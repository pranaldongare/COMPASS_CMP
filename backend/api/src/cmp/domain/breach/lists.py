"""The people a breach affected, from a list somebody sends us (2026-10-07).

The records cannot always say who is affected: the people may not be on the
platform at all. The list then comes from outside, in one of two forms, each
from an Excel template we give out (a CSV is taken too):

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

People are also **typed in** (2026-11-11): mail IDs and mobile numbers, comma-
separated, and anybody on the platform found by name. They are checked and
taken as a people list is, and recorded as a list with no file (`typed`).
"""

from __future__ import annotations

import asyncio
import csv
import io
import re
import uuid as uuid_mod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final

from pydantic import TypeAdapter, ValidationError

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.security import file_hash
from cmp.db.repositories import breach_lists as repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit.service import Event
from cmp.domain.breach import notices, service
from cmp.infrastructure.dkms.blind import index_of
from cmp.infrastructure.spreadsheets import (
    Column,
    SheetSpec,
    build_workbook,
    match_headings,
    normalise_heading,
    read_rows,
)
from cmp.validation import normalise_mobile
from cmp.validation.contacts import Email

Row = dict[str, Any]

KINDS: Final = ("contacts", "assets")

#: Rows one file may carry. A breach of more is a file per part.
MAX_ROWS: Final = 50_000

#: Rows that cannot be read, named back to whoever sent the file. The rest are
#: counted.
SHOWN_ERRORS: Final = 50

#: The names people put at the top of a column instead of ours.
ALIASES: Final[dict[str, str]] = {
    "full_name": "name",
    "full name": "name",
    "mail": "email",
    "mails": "email",
    "mail id": "email",
    "mail ids": "email",
    "mail_id": "email",
    "mail address": "email",
    "emails": "email",
    "email id": "email",
    "email ids": "email",
    "email_id": "email",
    "email address": "email",
    "email addresses": "email",
    "e-mail": "email",
    "e-mails": "email",
    "e-mail id": "email",
    "e-mail ids": "email",
    "e-mail address": "email",
    "phone": "mobile",
    "phone no": "mobile",
    "phone no.": "mobile",
    "phone number": "mobile",
    "phone numbers": "mobile",
    "mobiles": "mobile",
    "mobile no": "mobile",
    "mobile no.": "mobile",
    "mobile_no": "mobile",
    "mobile nos": "mobile",
    "mobile nos.": "mobile",
    "mobile number": "mobile",
    "mobile numbers": "mobile",
    "asset id": "asset_id",
    "asset": "asset_id",
    "asset_ref": "asset_id",
    "source": "source_code",
    "source code": "source_code",
}

_EMAIL: Final = TypeAdapter(Email)

#: A heading that reads as a contact whatever else it says: 'Alternate mail',
#: 'Email 2', 'Telephone'. Not 'Mailing address'.
_CONTACT_HEADING: Final = re.compile(r"(?<![a-z])(e-?mail|mail|mobile|telephone|phone)s?(?![a-z])")

#: The sheet of each template. Its headers are what a person reads; the aliases
#: above are what people put there instead. No example row: one left in by
#: mistake would be somebody written to about a breach.
_SHEETS: Final[dict[str, SheetSpec]] = {
    "contacts": SheetSpec(
        title="People",
        columns=(
            Column(
                "name",
                "Name",
                help="As they would recognise it. Optional, but it helps the Privacy Office.",
                width=30,
            ),
            Column(
                "email",
                "Mail ID",
                help="Where the notice is emailed. Give this or the mobile number, or both.",
                width=36,
            ),
            Column(
                "mobile",
                "Mobile number",
                help="Where it is sent by SMS, with the country code: +91 98765 43210.",
                width=22,
                text=True,
            ),
        ),
    ),
    "assets": SheetSpec(
        title="Assets",
        columns=(
            Column(
                "asset_id",
                "Asset ID",
                required=True,
                help="The platform's asset ID, or the ID the capture tool gave it.",
                width=40,
            ),
            Column(
                "source_code",
                "Source code",
                help="The data source's code. Needed only when two sources use the same ID.",
                width=20,
            ),
        ),
    ),
}

HELP: Final[dict[str, list[str]]] = {
    "contacts": [
        "One row per person affected, on the People sheet.",
        "Somebody already on the platform is matched by their mail ID or mobile number, and "
        "also sees the notice in their account.",
    ],
    "assets": [
        "One row per asset affected, on the Assets sheet: a recording, an image, a file.",
        "The people who consented in each asset are listed. People in an asset who consented "
        "to nothing cannot be traced, and are counted.",
    ],
}


def template(kind: str) -> bytes:
    """The workbook to fill in: the columns, and how to fill them."""
    _kind(kind)
    return build_workbook([_SHEETS[kind]], instructions=HELP[kind])


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


def _text(value: object) -> str:
    """A cell as text. A number typed into Excel comes back a number, and a
    long one a float: a mobile without a plus sign is both."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return "" if value is None else str(value).strip()


def _mobile(value: object) -> str:
    """A mobile cell as text. Excel keeps a typed +919876522222 as the number
    919876522222 unless the cell is text, and accounts hold it with its plus, so
    a number long enough to carry a country code gets it back. A shorter one is
    left as it came: no country code is assumed."""
    text = _text(value)
    if isinstance(value, int | float) and text.isdigit() and 11 <= len(text) <= 15:
        return f"+{text}"
    return text


def _columns(kind: str) -> tuple[Column, ...]:
    return tuple(
        Column(
            c.key,
            c.header,
            required=c.required,
            aliases=tuple(a for a, key in ALIASES.items() if key == c.key),
        )
        for c in _SHEETS[kind].columns
    )


def _check_contact_headings(found: set[str], others: list[str]) -> None:
    """Refuse a list we would read short. A contact column left behind is
    somebody who is never told, and the file would still look fine, so a heading
    that reads like one and went unmatched stops it, by name, and so does a
    file with neither column."""
    unread = [h for h in others if _CONTACT_HEADING.search(normalise_heading(h))]
    if unread:
        raise ValidationFailed(
            f"The column '{unread[0][:60]}' looks like a mail ID or mobile number but could "
            "not be read. Name it Mail ID or Mobile number, or take it out, and send the file "
            "again",
            field="file",
        )
    if not {"email", "mobile"} & found:
        named = ", ".join(f"'{h[:60]}'" for h in others[:6])
        raise ValidationFailed(
            "This file has no Mail ID or Mobile number column"
            + (f"; it has {named} instead" if named else "")
            + ". Start from the template",
            field="file",
        )


def _read_workbook(kind: str, payload: bytes) -> Reading:
    out = Reading()
    rows = read_rows(
        payload,
        columns=_columns(kind),
        max_rows=MAX_ROWS,
        check_headings=_check_contact_headings if kind == "contacts" else None,
    )
    if not rows:
        raise ValidationFailed("The file has no rows", field="file")
    if kind == "contacts" and not any(r.get("email") or r.get("mobile") for _, r in rows):
        raise ValidationFailed(
            "This sheet has no mail ID or mobile number in it. Start from the template",
            field="file",
        )
    for number, record in rows:
        out.rows.append(
            (
                number,
                {k: _mobile(v) if k == "mobile" else _text(v) for k, v in record.items()},
            )
        )
    return out


def _csv_rows(text: str) -> Iterator[tuple[int, list[str]]]:
    """The rows of a CSV with the line each starts on, leaving out blank lines
    and comments. One reader over the whole text: a quoted field may hold a
    newline, which reading line by line would cut in two."""
    reader = csv.reader(io.StringIO(text, newline=""))
    number = 1
    for cells in reader:
        first = cells[0].lstrip() if cells else ""
        if (first or len(cells) > 1) and not first.startswith("#"):
            yield number, cells
        number = reader.line_num + 1


def _read_csv(kind: str, text: str) -> Reading:
    rows = _csv_rows(text)
    first = next(rows, None)
    if first is None:
        raise ValidationFailed("The file has no rows", field="file")
    position, others = match_headings(first[1], _columns(kind))
    found = {c.key for c in position.values()}
    if kind == "contacts":
        _check_contact_headings(found, others)
    elif "asset_id" not in found:
        raise ValidationFailed(
            "The first row must name the columns (asset_id, source_code); this one has no "
            "asset_id column. Start from the template",
            field="file",
        )
    out = Reading()
    for number, cells in rows:
        if len(out.rows) + len(out.errors) >= MAX_ROWS:
            raise ValidationFailed(
                f"A file takes at most {MAX_ROWS:,} rows. Send the rest in another",
                field="file",
            )
        out.rows.append(
            (number, {c.key: cells[i].strip() for i, c in position.items() if i < len(cells)})
        )
    return out


def read(kind: str, payload: bytes) -> Reading:
    """The rows of an Excel workbook or a CSV, by their row number in the file."""
    _kind(kind)
    if payload[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValidationFailed(
            "That is an old Excel workbook (.xls). Save it as .xlsx (File > Save As) and send that",
            field="file",
        )
    if payload[:2] == b"PK":
        return _read_workbook(kind, payload)
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = payload.decode("cp1252")
        except UnicodeDecodeError:
            raise ValidationFailed(
                "The file could not be read. Save it as .xlsx from Excel", field="file"
            ) from None
    try:
        return _read_csv(kind, text)
    except csv.Error as exc:
        raise ValidationFailed(
            "The file could not be read. Save it as .xlsx from Excel", field="file"
        ) from exc


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
    # Off the event loop, as a consent record's PDF is: reading a large list
    # takes a while, and the API has other requests to answer meanwhile.
    reading = await asyncio.to_thread(read, kind, payload)
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


# ------------------------------------------------------- typed in (2026-11-11)

#: Entries one form may carry, mail IDs and mobile numbers together. More is a
#: list to upload.
MAX_TYPED: Final = 1_000

#: How a typed list is named where the lists taken are shown. There is no file.
TYPED_NAME: Final = "Typed in"

#: 'Meera Nair <meera@example.com>', as Outlook copies an address with its name.
_NAMED: Final = re.compile(r'^"?(?P<name>[^"<>]*?)"?\s*<(?P<email>[^<>]*)>$')


def split_entries(text: str) -> list[str]:
    """Entries separated by commas, semicolons or new lines, as Outlook copies
    them. A separator inside quotes or angle brackets is left alone, so
    '"Nair, Meera" <meera@example.com>' stays one entry."""
    entries: list[str] = []
    current: list[str] = []
    quoted = angled = False
    for ch in text:
        if ch == '"':
            quoted = not quoted
        elif ch == "<" and not quoted:
            angled = True
        elif ch == ">" and not quoted:
            angled = False
        if ch in ",;\r\n" and not quoted and not angled:
            entries.append("".join(current))
            current = []
        else:
            current.append(ch)
    entries.append("".join(current))
    return [e.strip() for e in entries if e.strip()]


def read_typed(mail_ids: str, mobiles: str) -> Reading:
    """What was typed, as the rows of a people list: one person to each mail ID
    and each mobile number, numbered in the order typed. A mobile must carry
    its country code: a person typing it can add one, and without it the
    number would match no account."""
    mails, phones = split_entries(mail_ids), split_entries(mobiles)
    if not mails and not phones:
        raise ValidationFailed("Type a mail ID or a mobile number", field="mail_ids")
    if len(mails) + len(phones) > MAX_TYPED:
        raise ValidationFailed(
            f"At most {MAX_TYPED:,} at a time. Upload an Excel list for more", field="mail_ids"
        )
    out = Reading()
    for number, entry in enumerate(mails, start=1):
        named = _NAMED.match(entry)
        if named:
            out.rows.append(
                (number, {"name": named["name"].strip(), "email": named["email"].strip()})
            )
        else:
            out.rows.append((number, {"email": entry}))
    for number, entry in enumerate(phones, start=len(mails) + 1):
        if not entry.lstrip("(").startswith("+"):
            out.refuse(
                number,
                f"{entry[:30]}: give the mobile number with its country code, as +91 98765 43210",
            )
        else:
            out.rows.append((number, {"mobile": entry}))
    return out


async def _plan_typed(
    conn: Conn, breach_id: int, *, mail_ids: str, mobiles: str, people: list[str]
) -> Plan:
    """A people list from what was typed, with anybody picked by name on top."""
    plan = await _plan_contacts(conn, breach_id, read_typed(mail_ids, mobiles))
    plan.kind = "typed"
    # In the order typed: a mobile is refused on reading, a mail ID on planning.
    plan.errors.sort(key=lambda e: int(e["row"]))
    if people:
        listed = await breach_repo.listed_person_ids(conn, breach_id)
        for uuid in dict.fromkeys(people):
            person = await user_repo.by_uuid(conn, uuid)
            if not person:
                raise NotFound("Person")
            plan.rows_read += 1
            pid = int(person["id"])
            if pid in listed or pid in plan.people:
                plan.already_listed += 1
            else:
                plan.people[pid] = {}
    return plan


async def check_typed(
    conn: Conn, *, breach_uuid: str, mail_ids: str, mobiles: str, people: list[str]
) -> Row:
    """What the typed entries would add, and each one that cannot be used.
    Writes nothing."""
    breach = await service.require(conn, breach_uuid)
    return _report(
        await _plan_typed(
            conn, int(breach["breach_id"]), mail_ids=mail_ids, mobiles=mobiles, people=people
        )
    )


async def take_typed(
    conn: Conn,
    *,
    breach_uuid: str,
    mail_ids: str,
    mobiles: str,
    people: list[str],
    note: str | None,
    actor_id: int,
) -> Row:
    """Add the typed entries to the breach's list, as a people list is added:
    an account's mail ID or mobile number lists that account, added by hand;
    any other is kept as this breach's contact. Entries that cannot be used are
    left out and reported. The revision is written even when it lists nobody
    with an account, so the note and the entry stay in how the list was built."""
    breach = await service.locked_open(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    plan = await _plan_typed(conn, breach_id, mail_ids=mail_ids, mobiles=mobiles, people=people)
    if not plan.people and not plan.contacts:
        if plan.errors and not plan.already_listed:
            raise ValidationFailed(
                "None of these could be used. Check them to see why", field="mail_ids"
            )
        raise Conflict("Everybody here is already on the list", code="nothing_new")

    counts = plan.counts()
    upload = await repo.add_upload(
        conn,
        breach_id,
        kind="typed",
        file_name=TYPED_NAME,
        sha256=file_hash(f"{mail_ids}\n{mobiles}\n{','.join(people)}".encode()),
        counts=counts,
        added_by=actor_id,
    )
    upload_uuid = str(upload["upload_uuid"])
    await breach_repo.add_affected_revision(
        conn,
        breach_id,
        scopes=[
            {
                "kind": "upload",
                "upload_uuid": upload_uuid,
                "file": "typed",
                "found": len(plan.people),
            }
        ],
        derived=0,
        added_by_hand=len(plan.people),
        excluded=0,
        people=[(pid, "dpo", {"uploads": [upload_uuid]}) for pid in plan.people],
        note=(note or "").strip() or None,
        confirmed_by=actor_id,
    )
    added = await repo.add_contacts(conn, breach_id, int(upload["upload_id"]), plan.contacts)
    await service.record_event(
        conn,
        breach,
        Event.BREACH_AFFECTED_UPLOADED,
        actor_id=actor_id,
        detail={"upload": upload_uuid, "kind": "typed", **counts, "new_contacts": added},
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
