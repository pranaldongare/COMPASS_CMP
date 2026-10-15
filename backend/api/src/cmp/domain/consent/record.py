"""A consent record as a PDF, for audit (2026-10-15).

What a person decided, against which notice, shown in which words, and when,
in one document an auditor can file. The PDFs are kept by a downstream system,
so each one has to stand on its own: the notice text as it was shown, in the
language it was shown, with the hash that proves it; the decision per purpose;
the history of the decision; and a machine-readable copy embedded in the PDF.

**What it says about the person, and no more.** Her name and one contact,
masked - the mobile if she has one, else the email - and her principal ID.
Not her date of birth, not her other contacts, not the network address the
consent came from. A PDF in somebody else's store is out of reach of an
erasure, so it carries only what identifies the record to a reader
(decided 2026-10-15; ADR 0031).

**Every artefact, as it stands.** A withdrawal is its own artefact. The PDF
of an earlier decision says it was superseded, by what, and when, so a copy
filed before the withdrawal and one filed after cannot be read as the same.

Who may have one: staff who may read the consent (the DPO for all; a DCO,
DCO Admin or RCO in their own scope), and the person, for her own. Each copy
is a disclosure of her name and is audited as `consent.record_downloaded`.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from cmp.core.errors import NotFound, ServiceUnavailable, ValidationFailed
from cmp.db.repositories import consent as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.dkms import unseal_strings
from cmp.infrastructure.dkms.fields import PREFIX
from cmp.infrastructure.pdf import (
    Attachment,
    Banner,
    Document,
    Fields,
    Heading,
    Paragraph,
    Table,
    Verbatim,
    render,
)

#: One archive is at most this many records. Each takes about a tenth of a
#: second to lay out; a larger pull is a narrower date range, asked again.
ARCHIVE_LIMIT = 200

_IST = ZoneInfo("Asia/Kolkata")

_STATUS = {
    "consented": ("Consented", "success"),
    "partial": ("Partly consented", "warning"),
    "declined": ("Declined", "neutral"),
    "withdrawn": ("Withdrawn", "danger"),
}

_ACTION = {
    "checkbox_click": "Ticked a checkbox for each purpose",
    "button_press": "Pressed a button to submit the decision",
    "signature": "Signed",
}

_BASIS = {
    "consent_s6": "Consent (s.6)",
    "legitimate_use_s7": "Legitimate use (s.7)",
}

_ROLE = {
    "dpo": "Data Protection Officer",
    "dco": "Data Collection Officer",
    "dco_admin": "DCO Admin",
    "rco": "Research Collection Officer",
}

_LANGUAGE = {
    "english": "English",
    "hindi": "Hindi",
    "marathi": "Marathi",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "kannada": "Kannada",
    "bengali": "Bengali",
    "gujarati": "Gujarati",
}


# ---------------------------------------------------------------- helpers
def mask_mobile(mobile: str) -> str:
    """'+919876543210' -> '+91******3210': the country code and the last four."""
    digits = re.sub(r"\D", "", mobile)
    if len(digits) <= 4:
        return "*" * len(digits)
    plus = mobile.strip().startswith("+")
    keep_front = 2 if plus and len(digits) > 10 else 0
    hidden = len(digits) - 4 - keep_front
    return f"{'+' if plus else ''}{digits[:keep_front]}{'*' * hidden}{digits[-4:]}"


def mask_email(email: str) -> str:
    """'asha.rao@example.org' -> 'a***@example.org'."""
    local, _, domain = email.strip().partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def masked_contact(mobile: str | None, email: str | None) -> tuple[str, str] | None:
    """The one contact a record shows: the mobile first, as sign-in does."""
    if mobile:
        return "Mobile (masked)", mask_mobile(mobile)
    if email:
        return "Email (masked)", mask_email(email)
    return None


def status_of(granted: int, total: int, *, is_withdrawal: bool) -> str:
    """The same rule as every consent read: derived from the grants."""
    if is_withdrawal and granted == 0:
        return "withdrawn"
    if granted == 0:
        return "declined"
    if granted < total:
        return "partial"
    return "consented"


def _when(value: datetime | None) -> str:
    if value is None:
        return "-"
    utc = value.astimezone(UTC)
    return f"{utc:%d %b %Y, %H:%M:%S} UTC ({value.astimezone(_IST):%H:%M} IST)"


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat() if value else None


def _period(value: Any) -> str:
    if not isinstance(value, timedelta):
        return str(value or "-")
    days = value.days
    if days and days % 365 == 0:
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''}"
    if days and days % 30 == 0:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''}"
    return f"{days} days"


def _sealed(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


async def _open_people(artefacts: list[dict[str, Any]]) -> None:
    """Open every name and contact in one call to the key service.

    A value that comes back still sealed means the service did not answer.
    Refused rather than printed: ciphertext on an audit record is worse than
    no record, because it looks like one.
    """
    columns = ("subject_name", "subject_email", "subject_mobile")
    opened = await unseal_strings([a.get(c) for a in artefacts for c in columns])
    for artefact in artefacts:
        for column in columns:
            value = artefact.get(column)
            if isinstance(value, str):
                value = opened.get(value, value)
            if _sealed(value):
                raise ServiceUnavailable(
                    "The encryption service did not answer, so the consent record could not "
                    "be made. Try again in a minute."
                )
            artefact[column] = value


# ---------------------------------------------------------------- the record
async def gather(conn: Conn, artefact: dict[str, Any]) -> dict[str, Any]:
    """Everything one record says, as plain data: the PDF's source and its
    embedded JSON. `artefact` is a row of `repo.artefact_by_uuid`, its people
    already opened."""
    consent_id = artefact["consent_id"]
    grants = await repo.grants_of(conn, consent_id)
    served = await repo.served_notice_text(conn, consent_id) or {}
    chain = await repo.history_chain(
        conn, user_id=artefact["auth_user_id"], notice_id=artefact["notice_id"]
    )

    granted = sum(1 for g in grants if g["granted"])
    status = status_of(granted, len(grants), is_withdrawal=artefact["is_withdrawal"])
    by_id = {c["consent_id"]: c for c in chain}
    later = next((c for c in chain if c["supersedes_consent_id"] == consent_id), None)
    earlier = by_id.get(artefact.get("supersedes_consent_id"))
    # What each purpose was before, so a withdrawal can tell a purpose taken
    # back from one that was refused all along.
    before = (
        {g["purpose_uuid"]: g["granted"] for g in await repo.grants_of(conn, earlier["consent_id"])}
        if earlier
        else {}
    )
    contact = masked_contact(artefact.get("subject_mobile"), artefact.get("subject_email"))

    return {
        "consent_uuid": str(artefact["consent_uuid"]),
        "status": status,
        "granted_count": granted,
        "purpose_count": len(grants),
        "is_withdrawal": artefact["is_withdrawal"],
        "action_type": artefact["action_type"],
        "served_at": _iso(artefact["served_at"]),
        "affirmative_action_at": _iso(artefact["affirmative_action_at"]),
        "recorded_at": _iso(artefact["created_at"]),
        "supersedes": str(earlier["consent_uuid"]) if earlier else None,
        "superseded_by": str(later["consent_uuid"]) if later else None,
        "superseded_at": _iso(later["affirmative_action_at"]) if later else None,
        "in_force": later is None,
        "data_principal": {
            "principal_uuid": str(artefact["subject_uuid"]),
            "name": artefact.get("subject_name"),
            "contact": {"kind": contact[0], "value": contact[1]} if contact else None,
        },
        "project": {"uuid": str(artefact["project_uuid"]), "name": artefact["project_name"]},
        "site": {"uuid": str(artefact["site_uuid"]), "label": artefact["site_label"]},
        "notice": {
            "uuid": str(artefact["notice_uuid"]),
            "code": artefact["notice_code"],
            "version": artefact["version"],
            "language": artefact["language_code"],
            "content_sha256_at_capture": artefact["notice_content_hash"],
            "content_sha256_stored": served.get("content_hash"),
            "hash_matches": bool(served.get("hash_matches")),
            "text": served.get("rendered_text"),
            "withdraw_url": served.get("withdraw_url"),
            "exercise_rights_url": served.get("exercise_rights_url"),
            "board_complaint_url": served.get("board_complaint_url"),
            "dpo_contact": served.get("dpo_contact"),
            "recipients": served.get("recipients_text"),
        },
        "purposes": [
            {
                "uuid": str(g["purpose_uuid"]),
                "code": g["purpose_code"],
                "name": g["name"],
                "description": g["description"],
                "data_categories": list(g["data_categories"] or []),
                "retention": _period(g["retention_period"]),
                "lawful_basis": g["lawful_basis"],
                "granted": g["granted"],
                "decision": (
                    "granted"
                    if g["granted"]
                    else "withdrawn"
                    if before.get(g["purpose_uuid"])
                    else "refused"
                ),
            }
            for g in grants
        ],
        "history": [
            {
                "consent_uuid": str(c["consent_uuid"]),
                "affirmative_action_at": _iso(c["affirmative_action_at"]),
                "is_withdrawal": c["is_withdrawal"],
                "granted_count": c["granted_count"],
                "purpose_count": c["purpose_count"],
                "status": status_of(
                    c["granted_count"], c["purpose_count"], is_withdrawal=c["is_withdrawal"]
                ),
                "language": c["language_code"],
                "this_record": c["consent_id"] == consent_id,
            }
            for c in chain
        ],
    }


def document(record: dict[str, Any], *, generated_at: datetime, issued_to: str) -> Document:
    """The record laid out as pages."""
    label, tone = _STATUS[record["status"]]
    granted, total = record["granted_count"], record["purpose_count"]
    when = datetime.fromisoformat(record["affirmative_action_at"])
    note = f"{granted} of {total} purpose{'s' if total != 1 else ''} granted · {_when(when)}"
    if not record["in_force"]:
        tone = "neutral"
        note = (
            f"No longer in force: superseded on "
            f"{_when(datetime.fromisoformat(record['superseded_at']))}"
        )

    person = record["data_principal"]
    notice = record["notice"]
    language = _LANGUAGE.get(notice["language"], str(notice["language"]).title())
    person_rows = [("Name", person["name"] or "Not recorded")]
    if person["contact"]:
        person_rows.append((person["contact"]["kind"], person["contact"]["value"]))
    person_rows.append(("Principal ID", person["principal_uuid"]))

    record_rows = [
        ("Consent ID", record["consent_uuid"]),
        ("Kind", "Withdrawal" if record["is_withdrawal"] else "Consent decision"),
        ("Notice served", _when(datetime.fromisoformat(record["served_at"]))),
        ("Decision made", _when(when)),
        ("How it was given", _ACTION.get(record["action_type"], record["action_type"])),
        ("Supersedes", record["supersedes"] or "Nothing: the first decision on this notice"),
        (
            "In force",
            "Yes" if record["in_force"] else f"No. Superseded by {record['superseded_by']}",
        ),
    ]

    purposes = [
        [
            f"{p['name']}\n{p['code']}",
            ", ".join(p["data_categories"]) or "-",
            p["retention"],
            _BASIS.get(p["lawful_basis"], p["lawful_basis"]),
            p["decision"].title(),
        ]
        for p in record["purposes"]
    ]

    history = [
        [
            _short(h["affirmative_action_at"]),
            ("Withdrawal" if h["is_withdrawal"] else "Decision")
            + (" (this record)" if h["this_record"] else ""),
            f"{h['granted_count']} of {h['purpose_count']} granted",
            h["consent_uuid"],
        ]
        for h in record["history"]
    ]

    integrity = (
        "Matches: the text below is the text that was shown."
        if notice["hash_matches"]
        else "DOES NOT MATCH: the stored text has changed since it was shown. Report this to "
        "the Privacy Office; the hash recorded at capture is the evidence."
    )

    rights_rows = [
        (title, value)
        for title, value in (
            ("Withdraw consent", notice["withdraw_url"]),
            ("Exercise rights", notice["exercise_rights_url"]),
            ("Complain to the Board", notice["board_complaint_url"]),
            ("Data Protection Officer", notice["dpo_contact"]),
            ("Recipients", notice["recipients"]),
        )
        if value
    ]

    blocks: list[Any] = [
        Banner("Status", label, tone, note),
        Heading("Data principal"),
        Fields(person_rows),
        Paragraph(
            "Only the name and one masked contact identify the person here. Date of birth, "
            "other contacts and the network address the decision came from are held by "
            "COMPASS and deliberately left out.",
            muted=True,
            size=8,
        ),
        Heading("The record"),
        Fields(record_rows),
        Heading("Collected for"),
        Fields(
            [
                ("Project", record["project"]["name"]),
                ("Collection site", record["site"]["label"]),
                ("Notice", f"{notice['code']}, version {notice['version']}"),
                ("Language shown", language),
            ]
        ),
        Heading("Decision per purpose"),
        Table(
            ["Purpose", "Data categories", "Retention", "Lawful basis", "Decision"],
            purposes,
            (30, 26, 14, 16, 14),
        ),
        Heading("History of this consent"),
        Paragraph(
            "Every decision this person recorded against this notice, oldest first. A record is "
            "never edited: a change of mind is a new record that supersedes the last.",
            muted=True,
            size=8,
        ),
        Table(["When (UTC)", "What", "Purposes", "Consent ID"], history, (24, 24, 15, 37)),
    ]
    if rights_rows:
        blocks += [Heading("Withdrawal and rights, as the notice gave them"), Fields(rights_rows)]
    blocks += [
        Heading("The notice as shown"),
        Fields(
            [
                ("Language", language),
                ("SHA-256 recorded at capture", notice["content_sha256_at_capture"]),
                ("SHA-256 of the stored text", notice["content_sha256_stored"] or "-"),
                ("Integrity", integrity),
            ]
        ),
        Verbatim(notice["text"] or "(The notice text could not be found.)"),
        Heading("About this document"),
        Fields(
            [
                ("Generated", _when(generated_at)),
                ("Issued to", issued_to),
                ("Source", "The COMPASS consent register, which no one can edit."),
                (
                    "Machine-readable copy",
                    "consent-record.json, attached to this PDF (open the attachments pane).",
                ),
            ]
        ),
    ]

    return Document(
        title="Consent record",
        subtitle="A decision recorded under the Digital Personal Data Protection Act, 2023",
        header=f"COMPASS · Consent record · {record['project']['name']}",
        footer=f"Consent {record['consent_uuid']} · generated {generated_at:%Y-%m-%d %H:%M} UTC",
        subject=f"Consent record {record['consent_uuid']}",
        keywords=("consent", "DPDP", record["consent_uuid"], person["principal_uuid"]),
        created_at=generated_at,
        blocks=blocks,
        attachments=(
            Attachment(
                name="consent-record.json",
                data=json.dumps(
                    {"generated_at": _iso(generated_at), "issued_to": issued_to, **record},
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
                mime_type="application/json",
                description="The consent record as data",
            ),
        ),
    )


def _issued_to(role: Any) -> str:
    name = str(getattr(role, "value", role))
    return f"Staff: {_ROLE.get(name, name)}"


def _short(value: str) -> str:
    return f"{datetime.fromisoformat(value).astimezone(UTC):%d %b %Y, %H:%M} UTC"


def file_name(consent_uuid: str) -> str:
    """No name in a file name: it outlives the folder it was put in."""
    return f"consent-{consent_uuid}.pdf"


async def _audit(conn: Conn, artefact: dict[str, Any], *, copy: str, in_archive: bool) -> None:
    await audit.record(
        conn,
        event=Event.CONSENT_RECORD_DOWNLOADED,
        entity_type="consent_artefact",
        entity_id=artefact["consent_id"],
        subject_user_id=artefact["auth_user_id"],
        detail={"format": "pdf", "copy": copy, "in_archive": in_archive},
    )


async def _one(conn: Conn, consent_uuid: str, *, issued_to: str, copy: str) -> tuple[bytes, str]:
    artefact = dict(await repo.artefact_by_uuid(conn, consent_uuid) or {})
    if not artefact:
        raise NotFound("Consent record")
    await _open_people([artefact])
    record = await gather(conn, artefact)
    generated_at = datetime.now(UTC)
    payload = await asyncio.to_thread(
        render, document(record, generated_at=generated_at, issued_to=issued_to)
    )
    await _audit(conn, artefact, copy=copy, in_archive=False)
    return payload, file_name(record["consent_uuid"])


# ---------------------------------------------------------------- entry points
async def for_staff(conn: Conn, consent_uuid: str, *, role: Any, user_id: int) -> tuple[bytes, str]:
    """One record, for a member of staff who may read it."""
    if not await repo.artefact_scoped(conn, consent_uuid, role=role, user_id=user_id):
        raise NotFound("Consent record")
    return await _one(conn, consent_uuid, issued_to=_issued_to(role), copy="staff")


async def for_subject(conn: Conn, consent_uuid: str, *, user_id: int) -> tuple[bytes, str]:
    """Her own record. Somebody else's is not found, as on every /me route."""
    artefact = await repo.artefact_by_uuid(conn, consent_uuid)
    if not artefact or artefact["auth_user_id"] != user_id:
        raise NotFound("Consent record")
    return await _one(conn, consent_uuid, issued_to="The data principal", copy="subject")


async def archive(
    conn: Conn,
    *,
    role: Any,
    user_id: int,
    project_uuid: str | None = None,
    site_uuid: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[bytes, str, int]:
    """A ZIP of records, one PDF each, with a manifest; for a downstream store.

    Every artefact in scope that matches, oldest first, up to
    `ARCHIVE_LIMIT`. More than that is refused with the count, so a
    scheduled pull narrows its range rather than silently getting a part.
    """
    uuids, total = await repo.artefacts_for_records(
        conn,
        role=role,
        user_id=user_id,
        project_uuid=project_uuid,
        site_uuid=site_uuid,
        date_from=date_from,
        date_to=date_to,
        limit=ARCHIVE_LIMIT,
    )
    if total == 0:
        raise NotFound("Consent records matching these filters")
    if total > ARCHIVE_LIMIT:
        raise ValidationFailed(
            f"{total} consent records match; one archive holds at most {ARCHIVE_LIMIT}. "
            "Narrow the date range or choose a project.",
            code="archive_too_large",
            details={"matched": total, "limit": ARCHIVE_LIMIT},
        )

    artefacts = [dict(await repo.artefact_by_uuid(conn, u) or {}) for u in uuids]
    await _open_people(artefacts)
    records = [await gather(conn, a) for a in artefacts]
    generated_at = datetime.now(UTC)
    issued_to = _issued_to(role)
    documents = [document(r, generated_at=generated_at, issued_to=issued_to) for r in records]
    pdfs = await asyncio.to_thread(lambda: [render(d) for d in documents])

    manifest = io.StringIO()
    writer = csv.writer(manifest)
    writer.writerow(
        [
            "file",
            "sha256",
            "consent_uuid",
            "principal_uuid",
            "project_uuid",
            "project",
            "site",
            "status",
            "is_withdrawal",
            "decision_at",
            "in_force",
            "supersedes",
            "superseded_by",
        ]
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for record, pdf in zip(records, pdfs, strict=True):
            name = file_name(record["consent_uuid"])
            zf.writestr(name, pdf)
            # The manifest names no one: identifiers, so a store can index the
            # files without opening them.
            writer.writerow(
                [
                    name,
                    hashlib.sha256(pdf).hexdigest(),
                    record["consent_uuid"],
                    record["data_principal"]["principal_uuid"],
                    record["project"]["uuid"],
                    record["project"]["name"],
                    record["site"]["label"],
                    record["status"],
                    record["is_withdrawal"],
                    record["affirmative_action_at"],
                    record["in_force"],
                    record["supersedes"] or "",
                    record["superseded_by"] or "",
                ]
            )
        zf.writestr("manifest.csv", manifest.getvalue())

    for artefact in artefacts:
        await _audit(conn, artefact, copy="staff", in_archive=True)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    return buffer.getvalue(), f"consent-records-{stamp}.zip", len(records)
