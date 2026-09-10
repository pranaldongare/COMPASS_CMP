"""The consent flow - capture, withdrawal, and the link that carries them.

The rules that make an artefact evidence rather than a row:

* **The subject comes from the session, never from the request body.** There is
  no code path by which any role records consent for someone else.
* **`served_at <= affirmative_action_at`.** s.5(1): the notice must be given
  before or with the request for consent. A record where she acted before the
  text rendered is defective on its face, and the database refuses it.
* **The content hash is copied at capture.** Not referenced - copied. INV-4.
* **Withdrawal supersedes, never edits.** The old artefact stays exactly as it
  was; a new one points back at it. The chain is the record.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import (
    Conflict,
    ConsentDefective,
    LinkInvalid,
    NotFound,
    ValidationFailed,
)
from cmp.core.logging import get_logger
from cmp.core.security import new_token, seal_token, token_fingerprint
from cmp.db.redis import K_NOTICE_SERVED, get_redis, key
from cmp.db.repositories import consent as repo
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import projects as project_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.validation import is_mobile, normalise_contact, normalise_mobile

log = get_logger("cmp.consent")


def receipt_contact(user: dict[str, Any]) -> str | None:
    """Where a receipt goes: a verified contact, email first, else the mobile.

    A data principal may have registered with a mobile alone, so a receipt
    addressed to `user["email"]` would go to nobody. An unverified contact is
    skipped for the opposite reason - it may belong to somebody else.
    """
    email = user.get("email")
    if email and user.get("email_verified_at"):
        return str(email)
    mobile = user.get("mobile")
    if mobile and user.get("mobile_verified_at"):
        return str(mobile)
    # Legacy rows predate per-medium verification stamps; fall back to
    # whichever contact exists rather than sending nothing.
    if email and not user.get("mobile_verified_at"):
        return str(email)
    return str(mobile) if mobile else (str(email) if email else None)


# --------------------------------------------------------------------- links
def link_path(token: str) -> str:
    """The public path a token is served at.

    One definition, because it is now built in three places - minting,
    reminting, and re-displaying a sealed link - and three string literals
    would eventually disagree about the prefix.
    """
    return f"/c/{token}"


async def create_link(
    conn: Conn,
    *,
    site_uuid: str,
    expires_at: datetime,
    max_uses: int | None,
    actor_id: int,
    role: str,
) -> dict[str, Any]:
    """Mint a site's consent link.

    `expires_at` is required and has no default and no maximum. The absence of a
    pre-fill is the control: someone has to decide how long this link should
    live, and a default would be chosen once and never revisited.
    """
    site = await project_repo.site_by_uuid(conn, site_uuid, role=role, user_id=actor_id)
    if not site:
        raise NotFound("Site")
    if site["status"] != "active":
        raise Conflict("That site is not active", code="site_inactive")
    if site["project_status"] != "approved":
        raise Conflict(
            "A consent link may only exist for a project in approved",
            code="project_not_approved",
            details={"status": site["project_status"]},
        )
    if expires_at <= datetime.now(UTC):
        raise ValidationFailed("expires_at must be in the future", field="expires_at")

    project = await project_repo.require(
        conn, str(site["project_uuid"]), role=role, user_id=actor_id
    )
    notices = await notice_repo.list_for_project(conn, project["project_id"])
    published = [n for n in notices if n["status"] == "published"]
    if not published:
        raise Conflict("The project has no published notice to serve", code="no_published_notice")
    notice = max(published, key=lambda n: n["version"])

    # Two forms of the token go in. The keyed digest is what a request is
    # matched against, and is all that authenticates. The sealed copy exists so
    # the URL can be shown again to whoever has to share it - encrypted under a
    # key that lives in the secret manager, so a dump of this table on its own
    # still yields nothing usable.
    raw = new_token(32)
    link = await repo.create_link(
        conn,
        notice_id=notice["notice_id"],
        site_id=site["site_id"],
        token_stored=token_fingerprint(raw)[:64],
        token_sealed=seal_token(raw),
        expires_at=expires_at,
        max_uses=max_uses,
        created_by=actor_id,
    )
    await audit.record(
        conn,
        event=Event.LINK_CREATED,
        entity_type="consent_link",
        entity_id=link["link_id"],
        detail={
            "site": site_uuid,
            "notice": str(notice["notice_uuid"]),
            "expires_at": expires_at.isoformat(),
            "max_uses": max_uses,
        },
    )
    return {**link, "token": raw, "site_uuid": site_uuid, "notice_uuid": notice["notice_uuid"]}


async def resolve_link(conn: Conn, token: str) -> dict[str, Any]:
    """Validate a link token.

    Every failure returns the same error. Distinguishing expired from revoked
    from unknown tells a token-guesser which of their guesses was structurally
    valid.
    """
    link = await repo.link_by_token(conn, token_fingerprint(token)[:64])
    if not link:
        raise LinkInvalid()

    now = datetime.now(UTC)
    if (
        link["status"] != "active"
        or link["expires_at"] <= now
        or (link["max_uses"] is not None and link["use_count"] >= link["max_uses"])
        or link["notice_status"] not in ("published", "superseded")
        or link["project_status"] != "approved"
        or link["site_status"] != "active"
    ):
        raise LinkInvalid()

    return link


async def register_subject(
    conn: Conn,
    *,
    token: str,
    full_name: str,
    mobile: str,
    email: str | None,
    organization_id: str | None,
    person_type: str | None,
) -> dict[str, Any]:
    """Create or recognise the person behind a link.

    `registered_via_link_id` is the audit trail for an open link. If a link
    circulates beyond its intended population this identifies everyone who came
    through it - including anyone who registered and abandoned before consenting,
    who otherwise leaves no artefact to trace.
    """
    link = await resolve_link(conn, token)
    mobile = normalise_mobile(mobile)
    email = email.strip().lower() if email and email.strip() else None
    if not mobile:
        raise ValidationFailed("A mobile number is required", field="mobile")
    existing = await user_repo.by_contact(conn, mobile)
    if not existing and email:
        existing = await user_repo.by_contact(conn, email)
    if existing:
        if existing["role"] != "data_subject":
            # A staff account arriving through a consent link is either a mistake
            # or an attempt to bind staff identity to a subject record.
            raise Conflict(
                "Those details belong to a staff account. Sign in instead.",
                code="staff_account",
            )
        user = existing
        created = False
    else:
        consumed = await repo.increment_use(conn, link["link_id"])
        if not consumed:
            raise LinkInvalid()
        user = await user_repo.create(
            conn,
            full_name=full_name,
            email=email,
            mobile=mobile,
            organization_id=organization_id,
            role="data_subject",
            person_type=person_type,
            status="pending",
            registered_via_link_id=link["link_id"],
        )
        created = True

    await audit.record(
        conn,
        event=Event.SUBJECT_REGISTERED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
        detail={"link": str(link["link_uuid"]), "new_account": created},
    )
    return {"user": user, "link": link, "created": created}


async def send_contact_code(conn: Conn, *, token: str, contact: str) -> None:
    link = await resolve_link(conn, token)
    contact = normalise_contact(contact)

    await ratelimit.enforce(
        "consent_otp_contact",
        contact,
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many code requests for this contact.",
    )
    await ratelimit.enforce(
        "consent_otp_token",
        str(link["link_uuid"]),
        limit=settings.otp_requests_per_token_per_hour,
        window_s=3600,
        message="Too many code requests for this link.",
    )

    issued = await otp.issue(otp.Scope.CONSENT_LINK, f"{link['link_uuid']}:{contact}")
    from cmp.tasks.authentication import send_consent_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_consent_code, contact, issued.code, link["project_name"])


async def verify_contact_code(conn: Conn, *, token: str, contact: str, code: str) -> dict[str, Any]:
    """Verify the code and establish the subject session.

    This is what makes `POST /c/{token}/consent` safe: the subject is taken from
    the session established here, never from the request body.
    """
    link = await resolve_link(conn, token)
    contact = normalise_contact(contact)
    await otp.require(otp.Scope.CONSENT_LINK, f"{link['link_uuid']}:{contact}", code)

    user = await user_repo.by_contact(conn, contact)
    if not user:
        raise NotFound("Registration")

    # The medium answered. Every medium given at registration has to, and the
    # account - and the session - waits for the last of them.
    user = await user_repo.mark_contact_verified(
        conn, user["id"], "mobile" if is_mobile(contact) else "email"
    )
    remaining = user_repo.unverified_mediums(user)
    complete = not remaining
    if complete and user["status"] == "pending":
        user = await user_repo.set_status(conn, user["id"], "active")

    await audit.record(
        conn,
        event=Event.OTP_VERIFIED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
        detail={"flow": "consent_link", "link": str(link["link_uuid"]), "complete": complete},
    )
    return {"user": user, "link": link, "complete": complete, "remaining": remaining}


async def serve_notice(
    conn: Conn, *, token: str, language_code: str, user_id: int | None
) -> dict[str, Any]:
    """Render the notice and stamp `served_at`.

    The timestamp returned here is what the subsequent consent call must carry.
    It is not taken from the client: a client-supplied `served_at` could claim
    the notice was shown at any convenient moment.
    """
    link = await resolve_link(conn, token)
    language = await notice_repo.language_row(
        conn, notice_id=link["notice_id"], language_code=language_code
    )
    if not language:
        raise NotFound("Language rendition")
    if language["approved_at"] is None:
        raise Conflict(
            "That language rendition is not legally approved", code="language_unapproved"
        )

    purposes = await notice_repo.purposes_of(conn, link["notice_id"])
    served_at = datetime.now(UTC)

    if user_id:
        await audit.record(
            conn,
            event=Event.NOTICE_SERVED,
            entity_type="notice",
            entity_id=link["notice_id"],
            subject_user_id=user_id,
            actor_user_id=user_id,
            detail={
                "language": language_code,
                "sha256": language["content_hash"],
                "link": str(link["link_uuid"]),
            },
        )
        await _record_serving(
            user_id=user_id,
            link_id=link["link_id"],
            notice_language_id=language["notice_language_id"],
            served_at=served_at,
            content_hash=language["content_hash"],
        )

    return {
        "notice": {
            "uuid": link["notice_uuid"],
            "code": link["notice_code"],
            "version": link["version"],
            "withdraw_url": link["withdraw_url"],
            "exercise_rights_url": link["exercise_rights_url"],
            "board_complaint_url": link["board_complaint_url"],
            "dpo_contact": link["dpo_contact"],
            "recipients_text": link["recipients_text"],
        },
        "project_name": link["project_name"],
        "site_label": link["site_label"],
        "language_code": language_code,
        "rendered_text": language["rendered_text"],
        "content_hash": language["content_hash"],
        # Strip the integer id before this leaves the process: the public flow
        # has no response model to filter it for us.
        "purposes": [{k: v for k, v in p.items() if k != "purpose_id"} for p in purposes],
        "served_at": served_at,
    }


#: How long a rendering of the notice stays good for. Past this the page has
#: been open long enough that the text may have changed under her, and she is
#: asked to reload it. Also the lifetime of the server's serving record.
NOTICE_SERVING_TTL = timedelta(hours=6)


def _serving_key(*, user_id: int, link_id: int, notice_language_id: int) -> str:
    return key(K_NOTICE_SERVED, user_id, link_id, notice_language_id)


async def _record_serving(
    *, user_id: int, link_id: int, notice_language_id: int, served_at: datetime, content_hash: str
) -> None:
    """The server's own note that this person was shown this text, now.

    Written by `serve_notice`, read by `capture`. The moment is the server's,
    and it is bound to the person, the link and the rendition, so a consent
    cannot claim a serving that did not happen or happened to somebody else.
    """
    r = get_redis()
    await r.setex(
        _serving_key(user_id=user_id, link_id=link_id, notice_language_id=notice_language_id),
        int(NOTICE_SERVING_TTL.total_seconds()),
        f"{served_at.isoformat()}|{content_hash}",
    )


async def _served_at_for(
    *, user_id: int, link_id: int, notice_language_id: int, content_hash: str
) -> datetime:
    """When this person was last shown this rendition, or a refusal.

    No record means the notice was never rendered to her through the link
    (s.5(1) has nothing to stand on), or was rendered more than
    `NOTICE_SERVING_TTL` ago and the record has lapsed. Both answer the same
    way: reload the notice.
    """
    r = get_redis()
    stored = await r.get(
        _serving_key(user_id=user_id, link_id=link_id, notice_language_id=notice_language_id)
    )
    if not stored:
        raise ConsentDefective(
            "Read the notice before recording a decision, or reload it if this page "
            "has been open a while.",
            code="notice_not_served",
        )
    stamp, _, hashed = str(stored).partition("|")
    if hashed != content_hash:
        # Cannot happen while a published rendition is frozen; kept so that a
        # future un-freezing cannot quietly serve one text and record another.
        raise ConsentDefective(
            "The notice changed since it was shown. Reload it and try again.",
            code="notice_stale",
        )
    return datetime.fromisoformat(stamp)


async def capture(
    conn: Conn,
    *,
    token: str,
    user_id: int,
    language_code: str,
    grants: dict[str, bool],
    action_type: str,
    ip_address: str | None,
) -> dict[str, Any]:
    """Write the artefact and its grants.

    One transaction. A grant row without its artefact, or an artefact without its
    grants, is not a partial record - it is an unanswerable question about what
    somebody agreed to.

    `served_at` is the server's own record from `serve_notice`, never a value
    from the request: the notice must have been rendered to this person,
    through this link, in this language, within `NOTICE_SERVING_TTL`.
    """
    link = await resolve_link(conn, token)
    language = await notice_repo.language_row(
        conn, notice_id=link["notice_id"], language_code=language_code
    )
    if not language:
        raise NotFound("Language rendition")
    if language["approved_at"] is None:
        # `serve_notice` refuses this too; checked again here so the capture
        # path does not depend on the caller having gone through it.
        raise Conflict(
            "That language rendition is not legally approved", code="language_unapproved"
        )

    served_at = await _served_at_for(
        user_id=user_id,
        link_id=link["link_id"],
        notice_language_id=language["notice_language_id"],
        content_hash=language["content_hash"],
    )
    now = datetime.now(UTC)
    if served_at > now + timedelta(seconds=1):
        raise ConsentDefective("served_at is after the affirmative action (s.5(1))")
    if (now - served_at) > NOTICE_SERVING_TTL:
        raise ConsentDefective(
            "This page has been open too long. Reload the notice and try again.",
            code="notice_stale",
        )

    purposes = await notice_repo.purposes_of(conn, link["notice_id"])
    by_uuid = {str(p["purpose_uuid"]): p for p in purposes}

    unknown = sorted(set(grants) - set(by_uuid))
    if unknown:
        raise ValidationFailed(
            "A purpose in the request is not part of this notice",
            field="grants",
            details={"unknown": unknown},
        )

    missing = sorted(set(by_uuid) - set(grants))
    if missing:
        # Silence is not consent. Every purpose must carry an explicit answer.
        raise ValidationFailed(
            "Every purpose on the notice must be answered",
            field="grants",
            details={"unanswered": missing},
        )

    for uuid_, purpose in by_uuid.items():
        if purpose["is_mandatory"] and not grants[uuid_]:
            raise ValidationFailed(
                f"'{purpose['name']}' cannot be refused on this notice",
                field="grants",
            )

    # Section 9. A child's personal data may only be processed with verifiable
    # consent from a parent or lawful guardian, which this platform does not
    # collect - so a purpose the registry has not marked as permitted for
    # minors cannot be granted by a data principal it knows to be one. Unknown
    # age is neither: most accounts were registered through a link that never
    # asked, and treating "we did not ask" as "adult" is the mistake the
    # nullable column exists to avoid. The gap is recorded rather than decided.
    granted_uuids = [u for u, v in grants.items() if v]
    if granted_uuids:
        age = await (
            await conn.execute(
                "SELECT cmp_is_minor(dob) AS is_minor FROM auth_user WHERE id = %s", (user_id,)
            )
        ).fetchone()
        if age and age["is_minor"] is True:
            blocked = sorted(
                purpose["name"]
                for u, purpose in by_uuid.items()
                if u in granted_uuids and not purpose.get("permitted_for_minors")
            )
            if blocked:
                raise ConsentDefective(
                    "This notice includes purposes that cannot be processed for a person "
                    "under eighteen without a parent or guardian's verifiable consent "
                    f"(s.9): {', '.join(blocked)}. Please contact the Privacy Office.",
                    code="consent_minor_not_permitted",
                    details={"blocked": blocked},
                )

    # Serialise per (person, notice) before reading what is current. Two first
    # captures racing would each see nothing current and each write a root;
    # migration 0023 makes the second a constraint violation, and this lock
    # makes it a supersession instead, which is what she meant. The lock is
    # transaction-scoped and released at commit or rollback.
    await conn.execute("SELECT pg_advisory_xact_lock(%s, %s)", (user_id, link["notice_id"]))

    existing = await repo.current_for_user_notice(
        conn, user_id=user_id, notice_id=link["notice_id"]
    )

    artefact = await repo.create_artefact(
        conn,
        auth_user_id=user_id,
        notice_id=link["notice_id"],
        notice_language_id=language["notice_language_id"],
        notice_content_hash=language["content_hash"],  # copied, not referenced
        link_id=link["link_id"],
        served_at=served_at,
        affirmative_action_at=now,
        action_type=action_type,
        ip_address=ip_address,
        is_withdrawal=False,
        supersedes_consent_id=existing["consent_id"] if existing else None,
    )
    await repo.add_grants(
        conn,
        artefact["consent_id"],
        {by_uuid[u]["purpose_id"]: v for u, v in grants.items()},
    )

    any_granted = any(grants.values())
    await audit.record(
        conn,
        event=Event.CONSENT_GIVEN if any_granted else Event.CONSENT_DECLINED,
        entity_type="consent_artefact",
        entity_id=artefact["consent_id"],
        subject_user_id=user_id,
        actor_user_id=user_id,
        detail={
            "notice": str(link["notice_uuid"]),
            "language": language_code,
            "sha256": language["content_hash"],
            "granted": sorted(u for u, v in grants.items() if v),
            "refused": sorted(u for u, v in grants.items() if not v),
            # str(): a UUID object is not JSON, and this line is only reached on a
            # second decision on the same notice, which nothing exercised before.
            "supersedes": str(existing["consent_uuid"]) if existing else None,
        },
    )

    user = await user_repo.by_id(conn, user_id)
    contact = receipt_contact(user) if user else None
    if contact and any_granted:
        # Optional: the artefact is written. A receipt that could not be queued
        # must not tell her the consent failed.
        from cmp.tasks.dispatch import dispatch_optional
        from cmp.tasks.notifications import send_consent_receipt

        dispatch_optional(
            send_consent_receipt,
            contact,
            str(artefact["consent_uuid"]),
            link["project_name"],
            [by_uuid[u]["name"] for u, v in grants.items() if v],
        )

    log.info(
        "consent.captured",
        consent=str(artefact["consent_uuid"]),
        granted=sum(1 for v in grants.values() if v),
        total=len(grants),
    )
    return {**artefact, "project_name": link["project_name"], "notice_uuid": link["notice_uuid"]}


async def withdraw(
    conn: Conn,
    *,
    consent_uuid: str,
    user_id: int,
    purpose_uuids: list[str] | None,
    withdraw_all: bool,
    ip_address: str | None,
) -> dict[str, Any]:
    """Withdraw some or all purposes.

    A new artefact supersedes the old one, carrying the same notice and the same
    copied hash - because what she is withdrawing from is the text she saw, not
    whatever the notice says now.

    The response states what stops, what continues, and that data already
    collected is not reached by this release.
    """
    current = await repo.artefact_by_uuid(conn, consent_uuid)
    if not current or current["auth_user_id"] != user_id:
        # Scope in the query result, not a separate permission check.
        raise NotFound("Consent record")

    live = await repo.current_for_user_notice(conn, user_id=user_id, notice_id=current["notice_id"])
    if not live or live["consent_id"] != current["consent_id"]:
        raise Conflict(
            "This consent record has been superseded. Withdraw the current one.",
            code="consent_superseded",
        )

    grants = await repo.grants_of(conn, current["consent_id"])
    by_uuid = {str(g["purpose_uuid"]): g for g in grants}

    if withdraw_all:
        targets = set(by_uuid)
    else:
        targets = set(purpose_uuids or [])
        unknown = sorted(targets - set(by_uuid))
        if unknown:
            raise ValidationFailed(
                "A purpose in the request is not part of this consent",
                field="purposes",
                details={"unknown": unknown},
            )
    if not targets:
        raise ValidationFailed("Name at least one purpose, or set all", field="purposes")

    new_grants: dict[str, bool] = {}
    for uuid_, grant in by_uuid.items():
        new_grants[uuid_] = False if uuid_ in targets else bool(grant["granted"])

    now = datetime.now(UTC)
    artefact = await repo.create_artefact(
        conn,
        auth_user_id=user_id,
        notice_id=current["notice_id"],
        notice_language_id=current["notice_language_id"],
        notice_content_hash=current["notice_content_hash"],
        link_id=current["link_id"],
        served_at=now,
        affirmative_action_at=now,
        action_type="button_press",
        ip_address=ip_address,
        is_withdrawal=True,
        supersedes_consent_id=current["consent_id"],
    )

    from cmp.db.repositories import registry as registry_repo

    purpose_ids: dict[int, bool] = {}
    for uuid_, granted in new_grants.items():
        purpose = await registry_repo.purpose_by_uuid(conn, uuid_)
        if purpose:
            purpose_ids[purpose["purpose_id"]] = granted
    await repo.add_grants(conn, artefact["consent_id"], purpose_ids)

    stopped = [by_uuid[u]["name"] for u in targets]
    continuing = [g["name"] for u, g in by_uuid.items() if new_grants[u]]

    # A purpose on a s.7 basis does not stop because consent was withdrawn -
    # consent was never what authorised it. Saying otherwise is a promise the
    # platform cannot keep.
    other_basis = [
        by_uuid[u]["name"] for u in targets if by_uuid[u]["lawful_basis"] == "legitimate_use_s7"
    ]

    await audit.record(
        conn,
        event=Event.CONSENT_WITHDRAWN,
        entity_type="consent_artefact",
        entity_id=artefact["consent_id"],
        subject_user_id=user_id,
        actor_user_id=user_id,
        detail={"supersedes": consent_uuid, "withdrawn": sorted(targets), "all": withdraw_all},
    )

    user = await user_repo.by_id(conn, user_id)
    contact = receipt_contact(user) if user else None
    if contact:
        from cmp.tasks.dispatch import dispatch_optional
        from cmp.tasks.notifications import send_withdrawal_confirmation

        dispatch_optional(
            send_withdrawal_confirmation,
            contact,
            str(artefact["consent_uuid"]),
            stopped,
            continuing,
        )

    return {
        "consent_uuid": artefact["consent_uuid"],
        "supersedes": consent_uuid,
        "withdrawn_at": artefact["affirmative_action_at"],
        "stopped": stopped,
        "continuing": continuing,
        "continuing_under_other_basis": other_basis,
        "note": (
            "Processing for the purposes listed under 'stopped' ceases within a "
            "reasonable period. Data already collected is not deleted by this "
            "withdrawal - to ask for erasure, make a rights request."
        ),
    }
