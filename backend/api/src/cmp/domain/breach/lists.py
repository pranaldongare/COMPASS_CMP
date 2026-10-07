"""Who a breach touched, from a list somebody sends us (2026-10-07).

The records cannot always say who a breach touched: the people may not be on
the platform at all. The list then comes from outside, in one of two forms,
each from a template we give out:

* **people** - a name, an email and a mobile per row. Somebody whose email or
  mobile is an account's goes on the breach's list as that account (and so
  also sees the notice in their account); anybody else is kept as a contact of
  this breach alone, sealed, and is sent the notice by email and SMS.
* **asset IDs** - the platform's asset ID or the capture tool's own reference,
  with the source's code where two sources share a reference. Each asset leads
  to the people who consented in it. Incidental and unidentified people in an
  asset name nobody and cannot be traced; they are counted, and said.

A file is checked first - nothing written, everything it would do counted,
every row that cannot be read named by its row number - and then taken. A
row already on the list, or repeated, is skipped rather than refused, so a
corrected file can be sent again. The file itself is not kept.
"""

from __future__ import annotations

import csv
import io
import uuid as uuid_mod
from dataclasses import dataclass, field
from typing import Any, Final

from pydantic import TypeAdapter, ValidationError

from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.security import file_hash
from cmp.db.repositories import breach_lists as repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.sql import Conn
from cmp.domain.audit.service import Event
from cmp.domain.breach import notices, service
from cmp.infrastructure.dkms.blind import index_of
from cmp.validation import normalise_mobile
from cmp.validation.contacts import Email

Row = dict[str, Any]

KINDS: Final = ("contacts", "assets")

#: Rows one file may carry. A breach of more is a file per part.
MAX_ROWS: Final = 50_000

#: Rows that cannot be read, named back to whoever sent the file. The rest are
#: counted.
SHOWN_ERRORS: Final = 50

COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "contacts": ("name", "email", "mobile"),
    "assets": ("asset_id", "source_code"),
}

#: The names people put at the top of a column instead of ours.
ALIASES: Final[dict[str, str]] = {
    "full_name": "name",
    "full name": "name",
    "mail": "email",
    "mail id": "email",
    "mail_id": "email",
    "email id": "email",
    "email_id": "email",
    "email address": "email",
    "phone": "mobile",
    "mobile no": "mobile",
    "mobile_no": "mobile",
    "mobile number": "mobile",
    "asset id": "asset_id",
    "asset": "asset_id",
    "asset_ref": "asset_id",
    "source": "source_code",
    "source code": "source_code",
}

HELP: Final[dict[str, list[str]]] = {
    "contacts": [
        "One row per person the breach touched.",
        "name: as they would recognise it. Optional, but it helps the Privacy Office.",
        "email: where the notice is emailed. mobile: where it is sent by SMS, with the "
        "country code (+91 98765 43210). Give either, or both - both are sent to.",
        "Somebody already on the platform is matched by email or mobile and also sees "
        "the notice in their account. Lines starting with # are ignored.",
    ],
    "assets": [
        "One row per asset the breach touched: a recording, an image, a file.",
        "asset_id: the platform's asset ID, or the ID the capture tool gave it.",
        "source_code: the data source's code. Needed only when two sources use the same "
        "asset ID. Lines starting with # are ignored.",
        "The people who consented in each asset are listed. People in an asset who "
        "consented to nothing cannot be traced, and are counted.",
    ],
}

EXAMPLE: Final[dict[str, list[str]]] = {
    "contacts": ["Asha Rao", "asha.rao@example.org", "+91 98765 43210"],
    "assets": ["GAIT-0417", "SRIB-LAB"],
}

_EMAIL: Final = TypeAdapter(Email)


def template(kind: str) -> str:
    """The CSV to fill in: the header, a line of guidance per column, an example."""
    _kind(kind)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS[kind])
    for line in HELP[kind]:
        out.write(f"# {line}\n")
    out.write("# Example - delete it before sending:\n")
    writer.writerow(EXAMPLE[kind])
    return out.getvalue()


def _kind(kind: str) -> str:
    if kind not in KINDS:
        raise ValidationFailed("kind must be contacts or assets", field="kind")
    return kind


@dataclass
class Reading:
    """A file, read: the rows it gives, and the ones it does not."""

    rows: list[tuple[int, dict[str, str]]] = field(default_factory=list)
    errors: list[Row] = field(default_factory=list)

    def refuse(self, line: int, message: str) -> None:
        self.errors.append({"row": line, "message": message})


def read(kind: str, payload: bytes) -> Reading:
    """The rows of a CSV, by their line number in the file."""
    _kind(kind)
    if payload[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValidationFailed(
            "That is an old Excel workbook (.xls). Save it as CSV (File > Save As > CSV UTF-8) "
            "and send that",
            field="file",
        )
    if payload[:2] == b"PK":
        raise ValidationFailed(
            "That is an Excel workbook. Save it as CSV (File > Save As > CSV UTF-8) and send that",
            field="file",
        )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = payload.decode("cp1252")
        except UnicodeDecodeError:
            raise ValidationFailed(
                "The file could not be read as text. Save it as CSV UTF-8", field="file"
            ) from None
    lines = [
        (n, line)
        for n, line in enumerate(text.splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        raise ValidationFailed("The file has no rows", field="file")
    reader = csv.reader([line for _, line in lines])
    header = [ALIASES.get(h.strip().lower(), h.strip().lower()) for h in next(reader)]
    wanted = COLUMNS[kind]
    first = "email or mobile" if kind == "contacts" else "asset_id"
    if (kind == "contacts" and not {"email", "mobile"} & set(header)) or (
        kind == "assets" and "asset_id" not in header
    ):
        raise ValidationFailed(
            f"The first row must name the columns ({', '.join(wanted)}); "
            f"this one has no {first} column. Start from the template",
            field="file",
        )
    out = Reading()
    for (number, _), cells in zip(lines[1:], reader, strict=True):
        if len(out.rows) + len(out.errors) >= MAX_ROWS:
            raise ValidationFailed(
                f"A file takes at most {MAX_ROWS:,} rows. Send the rest in another",
                field="file",
            )
        values = {
            header[i]: cells[i].strip()
            for i in range(min(len(header), len(cells)))
            if header[i] in wanted
        }
        out.rows.append((number, values))
    return out


# ---------------------------------------------------------------- resolving


@dataclass
class Plan:
    """What a file would do to the list, before anything is written."""

    kind: str
    rows_read: int = 0
    errors: list[Row] = field(default_factory=list)
    people: dict[int, Row] = field(default_factory=dict)  # account id -> evidence
    contacts: list[Row] = field(default_factory=list)
    already_listed: int = 0
    untraceable: int = 0

    def counts(self) -> dict[str, int]:
        return {
            "rows_read": self.rows_read,
            "matched_people": len(self.people),
            "new_contacts": len(self.contacts),
            "already_listed": self.already_listed,
            "unreadable": len(self.errors),
            "untraceable": self.untraceable,
        }


async def _plan_contacts(conn: Conn, breach_id: int, reading: Reading) -> Plan:
    plan = Plan(kind="contacts", rows_read=len(reading.rows) + len(reading.errors))
    good: list[tuple[int, Row]] = []
    for number, values in reading.rows:
        email = values.get("email") or ""
        mobile = values.get("mobile") or ""
        name = (values.get("name") or "")[:200] or None
        if not email and not mobile:
            reading.refuse(number, "Neither an email nor a mobile")
            continue
        if email:
            try:
                email = str(_EMAIL.validate_python(email)).lower()
            except ValidationError:
                reading.refuse(number, f"Not an email address: {email[:60]}")
                continue
        if mobile:
            mobile = normalise_mobile(mobile)
            digits = mobile.lstrip("+")
            if not 8 <= len(digits) <= 15:
                reading.refuse(number, "Not a mobile number: give it with its country code")
                continue
        good.append(
            (
                number,
                {
                    "full_name": name,
                    "email": email or None,
                    "mobile": mobile or None,
                    "email_hash": index_of("email", email) if email else None,
                    "mobile_hash": index_of("mobile", mobile) if mobile else None,
                },
            )
        )
    plan.errors = reading.errors

    accounts = await repo.accounts_by_hashes(
        conn,
        email_hashes=[c["email_hash"] for _, c in good if c["email_hash"]],
        mobile_hashes=[c["mobile_hash"] for _, c in good if c["mobile_hash"]],
    )
    by_email = {str(a["email_hash"]): int(a["person_id"]) for a in accounts if a["email_hash"]}
    by_mobile = {str(a["mobile_hash"]): int(a["person_id"]) for a in accounts if a["mobile_hash"]}
    listed = await breach_repo.listed_person_ids(conn, breach_id)
    seen_email, seen_mobile = await repo.contact_hashes(conn, breach_id)
    for number, contact in good:
        person = by_email.get(contact["email_hash"] or "") or by_mobile.get(
            contact["mobile_hash"] or ""
        )
        if person is not None:
            if person in listed or person in plan.people:
                plan.already_listed += 1
            else:
                plan.people[person] = {"rows": [number]}
            continue
        if (contact["email_hash"] and contact["email_hash"] in seen_email) or (
            contact["mobile_hash"] and contact["mobile_hash"] in seen_mobile
        ):
            plan.already_listed += 1
            continue
        if contact["email_hash"]:
            seen_email.add(contact["email_hash"])
        if contact["mobile_hash"]:
            seen_mobile.add(contact["mobile_hash"])
        plan.contacts.append(contact)
    return plan


async def _plan_assets(conn: Conn, breach_id: int, reading: Reading) -> Plan:
    plan = Plan(kind="assets", rows_read=len(reading.rows) + len(reading.errors))
    wanted: list[tuple[int, str, str | None]] = []
    for number, values in reading.rows:
        asset = values.get("asset_id") or ""
        if not asset:
            reading.refuse(number, "No asset_id")
            continue
        wanted.append((number, asset, (values.get("source_code") or "").upper() or None))

    uuids = []
    for _, asset, _ in wanted:
        try:
            uuids.append(str(uuid_mod.UUID(asset)))
        except ValueError:
            continue
    by_uuid = {a["asset_uuid"]: a for a in await repo.assets_by_uuid(conn, uuids)}
    by_ref: dict[str, list[Row]] = {}
    for a in await repo.assets_by_ref(conn, [asset for _, asset, _ in wanted]):
        by_ref.setdefault(str(a["source_asset_ref"]), []).append(a)

    asset_ids: dict[int, list[int]] = {}
    for number, asset, source in wanted:
        found: Row | None = None
        try:
            found = by_uuid.get(str(uuid_mod.UUID(asset)))
        except ValueError:
            found = None
        if found is None:
            candidates = [
                a
                for a in by_ref.get(asset, [])
                if source is None or str(a["source_code"]).upper() == source
            ]
            if len(candidates) > 1:
                codes = ", ".join(sorted(str(a["source_code"]) for a in candidates))
                reading.refuse(
                    number,
                    f"{asset} is an asset in more than one source ({codes}): add source_code",
                )
                continue
            found = candidates[0] if candidates else None
        if found is None:
            reading.refuse(
                number,
                f"No asset {asset}" + (f" in source {source}" if source else ""),
            )
            continue
        asset_ids.setdefault(int(found["asset_id"]), []).append(number)
    plan.errors = reading.errors

    people, plan.untraceable = await repo.people_in_assets(conn, sorted(asset_ids))
    listed = await breach_repo.listed_person_ids(conn, breach_id)
    for p in people:
        pid = int(p["person_id"])
        if pid in listed:
            plan.already_listed += 1
        else:
            plan.people[pid] = {"assets": sorted(p["assets"])}
    return plan


async def _plan(conn: Conn, breach_id: int, kind: str, payload: bytes) -> Plan:
    reading = read(kind, payload)
    if kind == "contacts":
        return await _plan_contacts(conn, breach_id, reading)
    return await _plan_assets(conn, breach_id, reading)


def _report(plan: Plan) -> Row:
    return {
        "kind": plan.kind,
        **plan.counts(),
        "would_add": len(plan.people) + len(plan.contacts),
        "errors": plan.errors[:SHOWN_ERRORS],
        "more_errors": max(0, len(plan.errors) - SHOWN_ERRORS),
    }


async def check(conn: Conn, *, breach_uuid: str, kind: str, payload: bytes) -> Row:
    """What the file would add, and every row it cannot read. Writes nothing."""
    breach = await service.require(conn, breach_uuid)
    return _report(await _plan(conn, int(breach["breach_id"]), kind, payload))


async def take(
    conn: Conn,
    *,
    breach_uuid: str,
    kind: str,
    payload: bytes,
    file_name: str,
    actor_id: int,
) -> Row:
    """Add what the file names to the breach's list. Rows it cannot read are
    left out and reported; the rest are taken."""
    breach = await service.locked_open(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    plan = await _plan(conn, breach_id, kind, payload)
    if not plan.people and not plan.contacts:
        if plan.errors and not plan.already_listed:
            raise ValidationFailed(
                f"No row of this file could be used ({len(plan.errors)} could not be read). "
                "Check it again to see which, and why",
                field="file",
            )
        raise Conflict("Everybody in this file is already on the list", code="nothing_new")

    counts = plan.counts()
    upload = await repo.add_upload(
        conn,
        breach_id,
        kind=kind,
        file_name=file_name,
        sha256=file_hash(payload),
        counts=counts,
        added_by=actor_id,
    )
    upload_uuid = str(upload["upload_uuid"])
    if plan.people:
        await breach_repo.add_affected_revision(
            conn,
            breach_id,
            scopes=[
                {
                    "kind": "upload",
                    "upload_uuid": upload_uuid,
                    "file": kind,
                    "found": len(plan.people),
                }
            ],
            derived=len(plan.people),
            added_by_hand=0,
            excluded=0,
            people=[
                (
                    pid,
                    "upload",
                    {
                        "uploads": [upload_uuid],
                        **{k: [str(x) for x in v] for k, v in ev.items() if k == "assets"},
                    },
                )
                for pid, ev in plan.people.items()
            ],
            note=None,
            confirmed_by=actor_id,
        )
    added = await repo.add_contacts(conn, breach_id, int(upload["upload_id"]), plan.contacts)
    await service.record_event(
        conn,
        breach,
        Event.BREACH_AFFECTED_UPLOADED,
        actor_id=actor_id,
        detail={"upload": upload_uuid, "kind": kind, **counts, "new_contacts": added},
    )
    await notices.reopen_if_done(
        conn, breach, newly_listed=len(plan.people) + added, actor_id=actor_id
    )
    return {**_report(plan), "new_contacts": added, "upload_uuid": upload_uuid}


async def contacts(conn: Conn, *, breach_uuid: str, after: str | None, limit: int = 200) -> Row:
    """The breach's contacts with no account, a page at a time, and its uploads."""
    breach = await service.require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    after_id: int | None = None
    if after:
        after_id = await repo.contact_id_by_uuid(conn, breach_id, after)
        if after_id is None:
            raise ValidationFailed("Unknown cursor", field="cursor")
    page = await repo.contacts_page(conn, breach_id, after=after_id, limit=limit + 1)
    more = len(page) > limit
    page = page[:limit]
    return {
        "total": await repo.count_contacts(conn, breach_id),
        "contacts": page,
        "next_cursor": str(page[-1]["contact_uuid"]) if more else None,
        "uploads": await repo.uploads(conn, breach_id),
    }
