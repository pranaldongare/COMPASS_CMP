"""The reports a person sent through the public link that an office dismissed,
and her rights over them (the product owner's fifth answer of 2026-11-07, 0065).

A claimed report became an incident, and the incident is the office's record of
what it did: it stays as it is. A dismissed report has nothing behind it, so no
record of accountability stands on it, and the person who sent it may ask what
is held about her and have her name and email taken off it.

* **Found by its blind index**, once identity is verified, on an access or an
  erasure request about everything held: her account's email once a code to
  it came back (or on a row from before such proofs were stamped), and its
  second email once that is proved; for a request with no account, the email
  it gave. An email nobody proved may be somebody else's, and it would hand
  that person's report over or erase it. Nothing is looked for on a request
  confined to one consent, because a report is under none.
* **Shown to the officers alone.** The register is theirs, and the
  administrator, who may read a request about the office, is shown nothing.
* **Erased by an officer's act on the request**, not an item: an item is her
  appearance in an asset, and a report is not one. It re-finds the reports by
  the index, so nothing a caller sends can name another person's, and blanks
  them in one statement. A legal hold on her stops it, and on a request with
  no account a hold on anybody whose account carries the contact it gave. The
  number, her words, the reason and who dismissed it stay, and the response
  says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from cmp.core.enums import RightsRequestStatus as Status
from cmp.core.enums import RightsRequestType as Kind
from cmp.core.errors import Conflict, NotFound
from cmp.core.permissions import Role
from cmp.db.repositories import incident_reports as incident_repo
from cmp.db.repositories import legal_holds as hold_repo
from cmp.db.repositories import users as user_repo
from cmp.db.repositories.breaches import LOGGED_TEXT
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.rights import execution
from cmp.infrastructure.dkms import DkmsUnavailable, unseal_many, unseal_value

Row = dict[str, Any]

#: The requests that look: an access request returns the reports, an erasure
#: takes her off them. A grievance asks for neither.
KINDS: Final = (Kind.ACCESS, Kind.ERASURE)

#: Who is shown them: the register is the officers'.
OFFICERS: Final = (Role.DPO, Role.LEGAL)

#: A request whose work has begun. Reaching it needs identity verified, the
#: request classified, erasure meant and the request in an office's queue
#: (`state_machine._start`), so this one test says all of that.
STARTED: Final = frozenset({Status.IN_PROGRESS, Status.AWAITING_HOLDERS, Status.COLLATING})

#: How many reports a request lists at once, with the total beside them: each
#: sealed value on the page is opened through the decrypt route, which has a
#: ceiling, and a stranger can send many.
SHOWN: Final = 50

NOT_VERIFIED: Final = "Identity is not verified yet; nothing is looked for until it is."
NOT_THIS_KIND: Final = "Only an access or an erasure request looks for them."
CONFINED: Final = (
    "This request is confined to one consent, and a report from the public link is under none."
)
UNAVAILABLE: Final = (
    "The key service did not answer, so the reports from the public link could not be "
    "looked for. Reload to try again."
)
NOT_ERASURE: Final = (
    "Only an erasure request takes the requester's name and email off a report; an access "
    "request sends them to the requester with the response."
)
NOT_STARTED: Final = (
    "Start the request first: identity verified, classified, erasure meant, and in your "
    "office's queue."
)
HELD: Final = "A legal hold on the requester stops this until it is released."
HOLD_UNKNOWN: Final = (
    "The key service did not answer, so whether a legal hold covers the requester could "
    "not be checked. Reload to try again."
)
NOTHING_LEFT: Final = "No report from the public link still carries the requester's name and email."

#: What the response says became of each report.
NOT_TAKEN_UP: Final = "Not taken up as an incident."
ERASED: Final = "Not taken up as an incident. Your name and email were erased from it."
#: What a mail says of a report an erasure has not yet reached.
NOT_YET_ERASED: Final = "not yet erased: it still carries your name and email"


def why_not_look(row: Row) -> str | None:
    """Why nothing is looked for on this request, or None when it looks."""
    if row.get("verification_status") != "verified":
        return NOT_VERIFIED
    if str(row.get("request_type")) not in KINDS:
        return NOT_THIS_KIND
    if row.get("consent_id"):
        return CONFINED
    return None


def why_not_erase(row: Row, *, held: bool) -> tuple[str, str] | None:
    """The code and the sentence that refuse an erasure now, or None.

    An erasure confined to one consent is not an erasure of everything held,
    which is what reaches a report, so it is refused as not one."""
    from cmp.domain.rights import service  # it imports this module

    if str(row.get("request_type")) != Kind.ERASURE:
        return "not_erasure", NOT_ERASURE
    if row.get("consent_id"):
        return "not_erasure", CONFINED
    try:
        service._open(row)
    except Conflict as closed:
        return str(closed.code), closed.message
    if Status(row["status"]) not in STARTED:
        return "request_not_started", NOT_STARTED
    if held:
        return "legal_hold", HELD
    return None


def is_officer(role: Role | str) -> bool:
    """Whether this role reads the register: what the request page shows of
    the reports, and of a request's way to them, is served to these alone."""
    try:
        return Role(role) in OFFICERS
    except ValueError:
        return False


def email_proved(person: Row) -> bool:
    """Whether an account's own email counts as the account holder's.

    A code came back from it, or the row is from before each medium's proof
    was stamped: neither the email nor the mobile carries a stamp, the legacy
    rule `consent.service.receipt_contact` keeps. An account that proved its
    mobile and never its email is the case this refuses. A nominee's account
    is made that way, carrying the email the principal typed, and so may carry
    somebody else's address."""
    return bool(person.get("email_verified_at")) or not person.get("mobile_verified_at")


async def address_hashes(conn: Conn, row: Row) -> list[str]:
    """The blind indexes of the addresses this request may find her by.

    Only addresses the account holder has proved: the account's email by
    `email_proved`, and its second email once a code to it came back. A
    request with no account has only the contact it gave, opened to be hashed
    as an email; a mobile finds nothing, because a report carries none. Raises
    `DkmsUnavailable` when that contact cannot be opened."""
    if why_not_look(row):
        return []
    if row.get("subject_user_id") is not None:
        person = await user_repo.by_id(conn, int(row["subject_user_id"]))
        if not person:
            return []
        hashes = (
            [str(person["email_hash"])] if person.get("email_hash") and email_proved(person) else []
        )
        if person.get("secondary_email_hash") and person.get("secondary_email_verified_at"):
            hashes.append(str(person["secondary_email_hash"]))
        return hashes
    contact = await unseal_value("rights_request", "submitted_contact", row["submitted_contact"])
    email_hash, _ = user_repo.contact_indexes(str(contact or ""))
    return [email_hash] if email_hash else []


async def found(conn: Conn, row: Row, *, strict: bool = False) -> Row:
    """What this request finds: the dismissed reports still naming her, all of
    them, and those erased under it.

    Not strict, a key service that does not answer is said rather than raised,
    so the request's page still opens; `unavailable` tells a caller that the
    answer is unknown rather than empty. Strict, it is raised, for a write that
    must not act on an unknown."""
    erased = await incident_repo.erased_under(conn, int(row["request_id"]))
    reason = why_not_look(row)
    if reason:
        return _result(reason, erased=erased)
    try:
        hashes = await address_hashes(conn, row)
    except DkmsUnavailable:
        if strict:
            raise
        return _result(UNAVAILABLE, erased=erased, unavailable=True)
    reports = await incident_repo.found_for(conn, hashes, limit=None) if hashes else []
    return {
        "looked": True,
        "not_looked_because": None,
        "unavailable": False,
        "open": reports,
        "erased": erased,
    }


def _result(reason: str, *, erased: list[Row], unavailable: bool = False) -> Row:
    return {
        "looked": False,
        "not_looked_because": reason,
        "unavailable": unavailable,
        "open": [],
        "erased": erased,
    }


async def _held(conn: Conn, row: Row) -> bool:
    """A hold on the requester, whichever office placed it.

    A request with no account may still be about somebody a hold covers: the
    public form opens one when the contact is a staff account's, or a data
    principal's second email nobody proved, and a hold is placed on a person
    whatever their role. So the contact it gave is looked up on every account,
    as any email, proved or not, or the mobile, and a hold on any of them
    stops the erasure. Raises `DkmsUnavailable` when that contact cannot be
    opened."""
    subject = row.get("subject_user_id")
    if subject is not None:
        people = [int(subject)]
    else:
        contact = await unseal_value(
            "rights_request", "submitted_contact", row["submitted_contact"]
        )
        people = await user_repo.ids_on_contact(conn, str(contact or ""))
    for person in people:
        if await hold_repo.active_covering(conn, asset_id=None, subject_user_id=person):
            return True
    return False


async def _why_not_erase_now(conn: Conn, row: Row) -> tuple[str, str] | None:
    """`why_not_erase` for this request as it stands. The hold is asked about
    only when nothing else refuses: with no account, asking opens the contact
    the request gave."""
    refused = why_not_erase(row, held=False)
    if refused is None and await _held(conn, row):
        return why_not_erase(row, held=True)
    return refused


def _item(report: Row) -> Row:
    """One report as a request shows it: who sent it and its title, sealed, and
    never the office's reason or who dismissed it."""
    return {
        "report_uuid": report["report_uuid"],
        "reference": report["reference"],
        "reporter_name": report["reporter_name"],
        "reporter_email": report["reporter_email"],
        "title": report["title"],
        "received_at": report["received_at"],
        "dismissed_at": report["dismissed_at"],
        "reporter_erased_at": report["reporter_erased_at"],
    }


async def view(conn: Conn, row: Row, *, role: Role | str, result: Row | None = None) -> Row | None:
    """The reports as a request shows them, or None for a role that does not
    read the register. Whether they may be erased now, and why not, is the
    server's answer, so the console holds no copy of the rule."""
    if not is_officer(role):
        return None
    if result is None:
        result = await found(conn, row)
    reports: list[Row] = result["open"]
    blocked: str | None
    if not result["looked"]:
        blocked = result["not_looked_because"]
    else:
        try:
            refused = await _why_not_erase_now(conn, row)
        except DkmsUnavailable:
            # Whether a hold covers the contact is unknown, so it may not be
            # erased now; the page still opens and says why.
            refused = ("unavailable", HOLD_UNKNOWN)
        blocked = refused[1] if refused else (None if reports else NOTHING_LEFT)
    return {
        "looked": result["looked"],
        "not_looked_because": result["not_looked_because"],
        "items": [_item(r) for r in reports[:SHOWN] + result["erased"]],
        "total": len(reports),
        "erased": len(result["erased"]),
        "may_erase": blocked is None,
        "erase_blocked_by": blocked,
    }


async def erase(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> Row:
    """Take her name and email off every dismissed report still carrying them.

    Nothing to erase is an answer, not an error, and writes no trail row: an
    officer pressing twice, or two pressing at once, erase each report once."""
    from cmp.domain.rights import service  # it imports this module

    service._may_act(row, role)
    if not is_officer(role):
        # Hidden, as the register is from everybody else.
        raise NotFound("Reports from the public link")
    refused = await _why_not_erase_now(conn, row)
    if refused:
        code, message = refused
        raise Conflict(message, code=code)
    hashes = await address_hashes(conn, row)
    done = (
        await incident_repo.erase_reporters(
            conn, hashes, request_id=int(row["request_id"]), erased_by=actor_id
        )
        if hashes
        else []
    )
    for report in done:
        await audit.record(
            conn,
            event=Event.INCIDENT_REPORT_REPORTER_ERASED,
            entity_type="incident_report",
            entity_id=int(report["report_id"]),
            subject_user_id=row.get("subject_user_id"),
            actor_user_id=actor_id,
            # The request's reference, so its trail carries the erasure; never
            # the name or the address.
            detail={"reference": row["reference"], "incident_reference": report["reference"]},
            # The request's office, not the report's (a report is no office's):
            # the row says who asked and under which request, which the wall
            # between the offices keeps from the other one.
            office_of=("rights_request", int(row["request_id"])),
        )
    shown = await view(conn, row, role=role)
    assert shown is not None
    return shown


async def for_package(conn: Conn, request: Row, *, result: Row | None = None) -> list[Row]:
    """The reports as the response gives them to her, opened: her own name,
    email and words, and when the report arrived and was dismissed. Never the
    office's reason or who dismissed it, which are the office's notes, as a
    verification note is. A report erased under this request is named by its
    number and dates alone."""
    if result is None:
        result = await found(conn, request, strict=True)
    reports = await unseal_many("incident_report", [dict(r) for r in result["open"]])
    return [
        {
            "reference": r["reference"],
            "received_at": r["received_at"],
            "reported_by": {"full_name": r["reporter_name"], "email": r["reporter_email"]},
            "title": r["title"],
            "noticed_at": r["noticed_at"],
            "what_you_told_us": {c: r.get(c) for c in LOGGED_TEXT},
            "cyber_attack": r["cyber_attack"],
            "dismissed_at": r["dismissed_at"],
            "outcome": NOT_TAKEN_UP,
        }
        for r in reports
    ] + [
        {
            "reference": r["reference"],
            "received_at": r["received_at"],
            "dismissed_at": r["dismissed_at"],
            "reporter_erased_at": r["reporter_erased_at"],
            "outcome": ERASED,
        }
        for r in result["erased"]
    ]


def _day(value: Any) -> str:
    text = str(value or "")
    return text[:10] if text else "-"


def digest_lines(entries: Sequence[Row], *, erasure: bool) -> list[str]:
    """The reports as a mail lists them: the number, the dates and the title,
    and never a name or an address.

    On an erasure, each report says whether the name and email came off it,
    and what was kept is said only once one did: an erasure answered partial
    before anybody erased must not read as though they were gone."""
    if not entries:
        return []
    lines = ["REPORTS YOU SENT THROUGH THE PUBLIC LINK"]
    for e in entries:
        parts = [
            str(e["reference"]),
            f"received {_day(e.get('received_at'))}",
            f"not taken up {_day(e.get('dismissed_at'))}",
        ]
        if e.get("title"):
            parts.append(str(e["title"]))
        if e.get("reporter_erased_at"):
            parts.append("your name and email were erased from it")
        elif erasure:
            parts.append(NOT_YET_ERASED)
        lines.append("- " + " · ".join(parts))
    if erasure and any(e.get("reporter_erased_at") for e in entries):
        lines += ["", execution.KEPT_OF_A_REPORT]
    return lines


# ----------------------------------------------- a code to a report's address


async def reporter_address(conn: Conn, contact: str) -> str | None:
    """The sealed address a dismissed, unerased report came from, if this
    contact is it: where a code goes for a reporter with no account. The
    stored address, matched by its index, never the one typed."""
    email_hash, _ = user_repo.contact_indexes(contact)
    return await incident_repo.reporter_address(conn, email_hash) if email_hash else None


async def reporter_address_for(conn: Conn, row: Row) -> str | None:
    """`reporter_address` for a request with no account, by the contact it gave."""
    if row.get("subject_user_id") is not None:
        return None
    contact = await unseal_value("rights_request", "submitted_contact", row["submitted_contact"])
    return await reporter_address(conn, str(contact or ""))
