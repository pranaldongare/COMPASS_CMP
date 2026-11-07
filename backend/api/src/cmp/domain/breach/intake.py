"""Incidents reported through the public link (2026-11-06, ADR 0037).

Anybody may report an incident, with no account, once they have proved their
email by a code. What they say arrives with its `INC-` number and waits in the
shared intake, where both officers see it and both are told. Nothing runs on
it yet: no clock starts and no duty exists until an officer has read it.

* **Claiming logs the incident**, into the claiming officer's office, under
  the number the report arrived with - from then on it is an ordinary incident
  that nobody outside that office sees.
* **Dismissing keeps the report**, with the reason. Junk costs a sentence, and
  nothing about it reaches the register.
* **A stranger's word starts no duty.** Saying it is a cyber attack does not
  create the CERT-In duty, as the same answer does in the console: the officer
  marks that once they have read it. First noticed is when the report arrived,
  the first the office could have known; what the reporter says about when
  they noticed it is kept beside it, and anchors nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import OFFICER_OF, ROLE_TITLES, Role
from cmp.db.repositories import incident_reports as repo
from cmp.db.repositories.breaches import LOGGED_TEXT
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import service
from cmp.infrastructure.dkms import seal, unseal
from cmp.infrastructure.dkms.fields import PREFIX as SEALED_PREFIX

Row = dict[str, Any]

#: Where the reporter's report is kept when it says nothing of where it began.
NOT_SAID: Final = "Reported through the public link; where it occurred was not said"

#: A reporter's clock may run a little ahead of ours.
_SKEW: Final = timedelta(minutes=5)

#: The earliest a reporter may say they noticed anything. An aware time compares
#: in UTC, and year 1 with a positive offset falls before year 1 there: the
#: database keeps that as a BC date no reader can take back, and one such row
#: would stop the shared intake opening for both offices.
_EARLIEST: Final = datetime(1970, 1, 1, tzinfo=UTC)

#: How many dismissed reports the office reads at once: the latest.
DISMISSED_SHOWN: Final = 200

#: How many waiting reports the office reads at once, unless it asks for more
#: up to `WAITING_MOST`. A stranger can fill the intake, and it has to stay
#: readable while they do.
WAITING_SHOWN: Final = 50
WAITING_MOST: Final = 200

#: What a reporter is told when the code is on its way.
CODE_SENT: Final = "A code is on its way to this email address."


def _address(email: str) -> str:
    return email.strip().lower()


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _refuse_sealed(said: dict[str, str | None]) -> None:
    """A sealed value in what a reporter says refuses the report. `seal()` passes
    a value that is already sealed through as it is, and a message opens every
    sealed variable it carries: someone who typed another person's ciphertext
    as their name would be mailed it opened. The relay checks what a browser
    sends through it; this holds whichever way the report came."""
    for field, value in said.items():
        if value and SEALED_PREFIX in value:
            raise ValidationFailed(
                f"Take {SEALED_PREFIX} out of this and send it again", field=field
            )


async def send_code(*, email: str, ip_address: str | None) -> str:
    """A code to the address typed: it is theirs to prove. Nothing is stored
    until the code comes back with the report."""
    from cmp.tasks.dispatch import dispatch_required
    from cmp.tasks.notifications.incident_reports import send_incident_report_code

    address = _address(email)
    identity = ratelimit.contact_key(address)
    await ratelimit.enforce(
        "incident_report_contact",
        identity,
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many codes for this address. Try again later.",
    )
    if ip_address:
        await ratelimit.enforce(
            "incident_report_ip", ip_address, limit=20, window_s=3600, fail_open=True
        )
    # Keyed on the hash, as the counter above is: Redis holds nobody's address.
    issued = await otp.issue(otp.Scope.INCIDENT_REPORT, identity)
    # Sealed on the way to the broker, like every address.
    sealed = await seal("incident_report", {"reporter_email": address})
    # The code is the whole of this call: one that was never queued is a 503
    # and a try again, not a sentence saying it is on its way.
    dispatch_required(send_incident_report_code, sealed["reporter_email"], issued.code)
    return CODE_SENT


async def submit(
    conn: Conn,
    *,
    reporter_name: str,
    email: str,
    code: str,
    title: str,
    noticed_at: datetime | None,
    told: dict[str, str | None],
    cyber_attack: str | None,
    ip_address: str | None,
) -> Row:
    """Take the report, if the code is right. Both offices are told, and the
    reporter is given its number."""
    if ip_address:
        await ratelimit.enforce(
            "incident_report_submit_ip", ip_address, limit=30, window_s=3600, fail_open=True
        )
    name = (reporter_name or "").strip()
    if not name:
        raise ValidationFailed("Give your name", field="name")
    title = (title or "").strip()
    if not title:
        raise ValidationFailed("Say in a line what happened", field="title")
    details = {c: _text(told.get(c)) for c in LOGGED_TEXT}
    if not details["incident_details"]:
        raise ValidationFailed("Say what happened", field="incident_details")
    _refuse_sealed({"name": name, "title": title, **details})
    if noticed_at is not None and noticed_at > datetime.now(UTC) + _SKEW:
        raise ValidationFailed("This time is in the future", field="noticed_at")
    if noticed_at is not None and noticed_at < _EARLIEST:
        raise ValidationFailed("This time is too long ago to be right", field="noticed_at")
    address = _address(email)
    identity = ratelimit.contact_key(address)
    # Checked, not spent: the row needs the key service, and a report that could
    # not be sealed should not cost the reporter the code they typed correctly.
    await otp.require(otp.Scope.INCIDENT_REPORT, identity, code, consume=False)
    made = await repo.create(
        conn,
        reporter_name=name,
        reporter_email=address,
        title=title,
        noticed_at=noticed_at,
        told=details,
        cyber_attack=cyber_attack or None,
    )
    await audit.record(
        conn,
        event=Event.INCIDENT_REPORT_RECEIVED,
        entity_type="incident_report",
        entity_id=int(made["report_id"]),
        actor_user_id=None,
        detail={"reference": made["reference"]},
    )
    from cmp.domain import alerts

    await alerts.incident_reported(conn, report=made)
    # Spent now, by the atomic check rather than a plain delete: of two requests
    # racing with one code, the second is refused here and its row rolls back.
    await otp.require(otp.Scope.INCIDENT_REPORT, identity, code)
    return {
        "reference": made["reference"],
        "message": (
            f"Thank you. Your report is {made['reference']}, and it has reached the Privacy Office."
        ),
    }


# ---------------------------------------------------------------- the office


async def waiting(conn: Conn, *, limit: int = WAITING_SHOWN, offset: int = 0) -> Row:
    """The shared intake: a page of the reports no office has taken up, each by
    who sent it and its title. `read` opens one."""
    return {
        "items": await repo.waiting(conn, limit=limit, offset=offset),
        "total": await repo.count_waiting(conn),
        "limit": limit,
        "offset": offset,
    }


async def waiting_count(conn: Conn) -> int:
    """For both officers' dashboards: the same reports, counted."""
    return await repo.count_waiting(conn)


async def dismissed(conn: Conn) -> list[Row]:
    """What became of the reports an office did not take up, newest first: who
    sent each, who dismissed it and why. For both officers, so a report that
    was the other office's can be raised. Sealed; the console opens it. A
    reporter erased under a rights request shows with no name or address, and
    when it was done (0065)."""
    return await repo.dismissed(conn, limit=DISMISSED_SHOWN)


def _view(row: Row) -> Row:
    return {
        "report_uuid": row["report_uuid"],
        "reference": row["reference"],
        "reporter_name": row["reporter_name"],
        "reporter_email": row["reporter_email"],
        "title": row["title"],
        "noticed_at": row["noticed_at"],
        "received_at": row["received_at"],
        "cyber_attack": row["cyber_attack"],
        "logged": {c: row.get(c) for c in LOGGED_TEXT},
    }


def _waiting(report: Row | None) -> Row:
    if report is None:
        raise NotFound("Report")
    if report["claimed_at"] is not None:
        raise Conflict("It has already been claimed", code="already_claimed")
    if report["dismissed_at"] is not None:
        raise Conflict("It has already been dismissed", code="already_dismissed")
    return report


async def read(conn: Conn, *, report_uuid: str) -> Row:
    """One waiting report in full, for an officer to read. Sealed, as the list
    is; the console opens it."""
    return _view(_waiting(await repo.by_uuid(conn, report_uuid)))


async def _open(conn: Conn, report_uuid: str) -> Row:
    return _waiting(await repo.locked(conn, report_uuid))


async def claim(conn: Conn, *, report_uuid: str, office: str, actor_id: int) -> Row:
    """Out of the intake and into this office's register, as an incident
    logged by the officer who took it. Its clocks start with the validation,
    as every incident's do."""
    report = await _open(conn, report_uuid)
    plain = await unseal("incident_report", dict(report))
    logged = {c: plain.get(c) for c in LOGGED_TEXT}
    detail = await service.record(
        conn,
        title=str(plain["title"]),
        detected_at=report["received_at"],
        began_at=None,
        location_kind="other",
        processor_uuid=None,
        source_uuid=None,
        location_detail=_text(plain.get("origin")) or NOT_SAID,
        actor_id=actor_id,
        logged=logged,
        # Never "yes": that would create the CERT-In duty on a stranger's word.
        cyber_attack="no" if report["cyber_attack"] == "no" else "unknown",
        office=office,
        reference=str(report["reference"]),
    )
    breach = await service.require(conn, str(detail["breach_uuid"]))
    await repo.set_claimed(
        conn,
        int(report["report_id"]),
        breach_id=int(breach["breach_id"]),
        claimed_by=actor_id,
    )
    await audit.record(
        conn,
        event=Event.INCIDENT_REPORT_CLAIMED,
        entity_type="incident_report",
        entity_id=int(report["report_id"]),
        actor_user_id=actor_id,
        detail={"reference": report["reference"], "office": office},
    )
    return await service.detail(conn, str(detail["breach_uuid"]))


async def dismiss(conn: Conn, *, report_uuid: str, reason: str, actor_id: int) -> None:
    """Not taken up, and why. It stays, for whoever asks what became of it."""
    text = _text(reason)
    if not text:
        raise ValidationFailed("Say why it is being dismissed", field="reason")
    report = await _open(conn, report_uuid)
    await repo.set_dismissed(conn, int(report["report_id"]), reason=text, dismissed_by=actor_id)
    await audit.record(
        conn,
        event=Event.INCIDENT_REPORT_DISMISSED,
        entity_type="incident_report",
        entity_id=int(report["report_id"]),
        actor_user_id=actor_id,
        detail={"reference": report["reference"], "reason_given": True},
    )


async def reported(conn: Conn, breach_id: int) -> Row | None:
    """Who reported an incident and what they said of it, if a report became
    it. Sealed; the console opens it."""
    report = await repo.for_breach(conn, breach_id)
    if report is None:
        return None
    return {
        "reporter_name": report["reporter_name"],
        "reporter_email": report["reporter_email"],
        "received_at": report["received_at"],
        "noticed_at": report["noticed_at"],
        "cyber_attack": report["cyber_attack"],
    }


#: Who the office may have told of a report: every role that signs in to the
#: console, but for a breach-only login, which holds a ticket and nothing else.
INTAKE_ROLES: Final[tuple[Role, ...]] = tuple(
    r for r in Role if r not in (Role.DATA_SUBJECT, Role.BREACH_HOLDER)
)


def role_titles() -> list[Row]:
    return [{"role": r.value, "title": ROLE_TITLES[r.value]} for r in INTAKE_ROLES]


#: The officers, always among those told: a report nobody who may claim it
#: hears of is a report that waits for ever.
OFFICERS: Final[tuple[str, ...]] = tuple(OFFICER_OF.values())
