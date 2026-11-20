"""Telling DataVault to erase, on an erasure request (0071, ADR 0039).

The office that answers an erasure request first asks DataVault what it holds
(`checks`). With that list on record, the DPO or the Legal PoC presses "Erase
in DataVault", confirms, and the assets go to DataVault under one
`erasure_id`. DataVault answers each asset `erased`, `pending`, `failed` (with
a reason) or `not_held`. Nothing here runs by itself (the product owner,
2026-11-13): an asset still pending is asked about again when somebody presses
"Check status", which repeats the same instruction - the same `erasure_id`
and the same assets - and so starts nothing new. That stays possible after the
request is closed: closing does not wait for DataVault, and what was pending
then can still be followed to its end.

**When it may be pressed.** On an erasure request that has been started and is
still open, which the state machine allows only once identity is verified,
the request is classified and she has said she means erasure; with a check
that listed something; and while no legal hold stands on the person - a hold
stops this erasure as it stops the platform's own. A hold stops "Check status"
too from sending an instruction DataVault has never answered: for all the
platform knows DataVault never received it, and sending it now would start it.

**Which assets go.** What the last answered check listed, and of it only what
this request reaches: an asset matched to this person's records in the
request's own office - its consent one of hers there, or its project one she
gave a consent on there. A request is one office's, and so is what it erases:
an asset of the other office's, or one whose consent and project match
nothing of hers, is left out and shown as left out (the review of 2026-11-13).
A request confined to one consent reaches only the assets DataVault tagged
with that consent or another of its chain. And an asset DataVault gave no
consent for is left out: the contract sends each asset back with its consent.
Of those in scope, a press sends what has not been sent yet and what DataVault
did not erase, each once however often the check listed it; what is erased,
not held, or still pending is not sent again.

**How it is sent.** The instruction and its assets are written first and
committed, then the call is made with no transaction open, then the answer is
written. Presses on one request are taken one at a time, so two at once do not
send the same assets twice. A call that is never answered leaves the
instruction on record with its assets unanswered, and "Check status" sends it
again. One DataVault refuses outright - malformed, a key it refuses, an
address it does not know - it has not taken: its assets are marked not erased,
with the reason in the platform's words, and a later press sends them again
under a new `erasure_id`. An instruction names at most a thousand assets, the
contract's limit; more go as several.

Each asset goes back with the consent DataVault gave for it at the check, as
it gave it - a number as a number, a text as a text. The person and the
request are named as the administrator's switch says (`ids`), and that is
settled for an instruction once DataVault has answered it: a repeat then says
the same, whatever the switch says by then. One DataVault has never answered
it has not taken, so the next ask names them as the switch says then - which
is how a refusal over the naming is mended by changing the switch.

**What it does not do.** It decides nothing about the request: the scope, the
holders, the tickets and the close are as they were. A request can close with
assets still pending in DataVault; the page says so before it does.

The trail records that an instruction went and what came back as counts and
a short code - never an asset, a path or a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cmp.core.enums import RightsRequestType as Kind
from cmp.core.errors import Conflict, Forbidden
from cmp.core.permissions import Role
from cmp.db.repositories import datavault as repo
from cmp.db.repositories import legal_holds as hold_repo
from cmp.db.repositories import rights as rights_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.datavault import connection, ids
from cmp.domain.rights import service as rights
from cmp.domain.rights import state_machine as sm
from cmp.domain.rights.tickets import WORKING
from cmp.infrastructure import datavault as client

Row = dict[str, Any]

#: An asset DataVault has not said the last word on.
OPEN = ("unanswered", "pending")
#: What a press of "Erase in DataVault" sends: never sent, or sent and failed.
SENDABLE = (None, "failed")
#: Every place an asset can stand once sent.
STATUSES = ("unanswered", "pending", "erased", "failed", "not_held")


def refused(code: str) -> bool:
    """A failure that means DataVault turned the instruction down without
    taking it: a 4xx, but for a request timing out or too many at once, which
    pass by themselves."""
    return code.startswith("status_4") and code not in ("status_408", "status_429")


#: Why an ask was not answered, in the office's words.
FAILURES: dict[str, str] = {
    "timeout": "DataVault did not answer in time.",
    "unreachable": "DataVault could not be reached.",
    "unreadable": "DataVault answered, but not in the agreed format.",
    "status_400": "DataVault refused the instruction as badly formed.",
    "status_401": "DataVault refused the key.",
    "status_403": "DataVault refused the key.",
    "status_404": "DataVault does not know this address.",
    "status_409": "DataVault has this instruction with a different list of assets.",
}


def failure_said(code: str) -> str:
    if code in FAILURES:
        return FAILURES[code]
    if code.startswith("status_"):
        return f"DataVault answered with an error ({code.removeprefix('status_')})."
    return "The instruction was not answered."


@dataclass(frozen=True)
class Send:
    """One instruction as it goes: read and written before the call."""

    erasure_id: int
    erasure_uuid: str
    request_id: int
    reference: str
    subject_user_id: int
    erasure_url: str
    api_key: str | None
    api_key_header: str
    #: The request and the person, as this ask names them, and by which
    #: naming (`ids`).
    id_format: str
    request_named: str
    person_named: int | str
    assets: list[dict[str, Any]]
    #: Sent before: this ask is for where it has got to.
    again: bool
    #: DataVault has answered this instruction before, so it has it: asking
    #: again starts nothing new.
    answered: bool = False
    #: The request's office when the instruction was made ready.
    office: str | None = None


def applies(row: Row) -> bool:
    """Only an erasure request has anything to erase."""
    return str(row["request_type"]) == Kind.ERASURE


async def _in_scope(conn: Conn, row: Row, assets: list[Row]) -> tuple[list[Row], list[Row]]:
    """The assets this request reaches, and those the check listed that it
    does not. One pass: a check may list thousands.

    Reached: an asset DataVault gave a consent for (it goes back with it) that
    is matched to this person's records in the request's own office - the
    check matched its consent or its project only among her consents there.
    A request confined to one consent reaches that consent's chain only."""
    chain: set[int] | None = None
    if row.get("consent_id"):
        chain = set(await rights_repo.consent_chain_ids(conn, int(row["consent_id"])))
    inside: list[Row] = []
    outside: list[Row] = []
    for a in assets:
        if a["consent_ref"] is None:
            reaches = False
        elif chain is not None:
            reaches = a["consent_id"] is not None and int(a["consent_id"]) in chain
        else:
            reaches = a["project_no"] is not None
        (inside if reaches else outside).append(a)
    return inside, outside


def _sendable(inside: list[Row], states: dict[str, Row]) -> list[Row]:
    """What a press sends: each asset in scope once, if it has not been sent
    or DataVault did not erase it."""
    seen: set[str] = set()
    out: list[Row] = []
    for a in inside:
        ref = str(a["asset_ref"])
        if ref in seen:
            continue
        seen.add(ref)
        if (states.get(ref) or {}).get("status") in SENDABLE:
            out.append(a)
    return out


def _left_out(inside: list[Row], outside: list[Row]) -> int:
    """How many assets the check listed that the request does not reach,
    each counted once."""
    inside_refs = {str(a["asset_ref"]) for a in inside}
    return len({str(a["asset_ref"]) for a in outside} - inside_refs)


async def _held(conn: Conn, row: Row) -> bool:
    """A legal hold stands on the person, whichever office placed it."""
    if row.get("subject_user_id") is None:
        return False
    found = await hold_repo.active_covering(
        conn, asset_id=None, subject_user_id=int(row["subject_user_id"])
    )
    return found is not None


async def _why_not(conn: Conn, row: Row, *, has_check: bool, held: bool) -> str | None:
    """Why nothing may be sent to DataVault for this request now, or None."""
    if row.get("subject_user_id") is None:
        return "This request is not linked to a person yet. Verify identity first."
    if row["status"] == "closed":
        return f"{row['reference']} is closed."
    if str(row["status"]) not in WORKING:
        return (
            "Start the request first: identity verified, classified as erasure, and "
            "erasure confirmed."
        )
    if await connection.for_erasure(conn) is None:
        return (
            "The erasure address is not set. An administrator sets it under DataVault connection."
        )
    if held:
        return (
            "A legal hold stands on this person. Nothing is erased in DataVault until it "
            "is released."
        )
    if not has_check:
        return "Check in DataVault first: what it lists is what is sent."
    return None


async def state(
    conn: Conn, row: Row, *, role: Role | str, check: Row | None, assets: list[Row]
) -> tuple[dict[str, Row], Row | None]:
    """Where each listed asset stands, by DataVault's identifier, and what the
    office may do now. Nothing for a request that is not an erasure. A reader
    who may not act on the request is told where things stand, and offered
    nothing."""
    if not applies(row):
        return {}, None
    request_id = int(row["request_id"])
    states = await repo.erasure_states(conn, request_id)
    inside, outside = await _in_scope(conn, row, assets)
    inside_refs = {str(a["asset_ref"]) for a in inside}
    per_asset: dict[str, Row] = {}
    for a in assets:
        ref = str(a["asset_ref"])
        s = states.get(ref)
        per_asset[ref] = {
            "in_scope": ref in inside_refs,
            "erasure_status": s["status"] if s else None,
            "erasure_status_at": (s["status_at"] or s["sent_at"]) if s else None,
            "erasure_completed_at": s["completed_at"] if s else None,
            "erasure_reason": s["reason"] if s else None,
        }
    # Everything ever sent for the request, listed by the last check or not.
    counts = dict.fromkeys(STATUSES, 0)
    for s in states.values():
        counts[str(s["status"])] += 1
    to_send = _sendable(inside, states)
    sent = await repo.erasures_of(conn, request_id)
    held = await _held(conn, row)
    open_now = sum(int(e["open_assets"]) for e in sent)
    # Under a hold, an instruction DataVault has never answered is not sent.
    askable = sum(int(e["open_assets"]) for e in sent if not (held and e["answered_at"] is None))
    last = sent[0] if sent else None
    acts = sm.may_act(role, rights.facts_of(row))
    why_not: str | None = None
    if acts:
        why_not = await _why_not(conn, row, has_check=check is not None, held=held)
        if why_not is None and not to_send:
            why_not = (
                "Everything this request reaches has been sent to DataVault."
                if inside
                else "DataVault lists nothing this request reaches."
            )
    return per_asset, {
        "may_erase": acts and why_not is None,
        "why_not": why_not,
        "to_send": len(to_send),
        "left_out": _left_out(inside, outside),
        # After the request is closed too: what was pending then can still
        # be followed to its end.
        "may_check_status": acts and askable > 0 and await connection.for_erasure(conn) is not None,
        "open": open_now,
        "counts": counts,
        "last_asked_at": (last["last_asked_at"] or last["sent_at"]) if last else None,
        "last_failure": last["failure"] if last else None,
        "last_failure_said": failure_said(str(last["failure"]))
        if last and last["failure"]
        else None,
    }


def _named(row: Row, fmt: str) -> tuple[str, int | str]:
    """The request and the person as an instruction names them."""
    return (
        ids.request(fmt, reference=row["reference"], uuid=row["request_uuid"]),
        ids.of(fmt, no=row["subject_user_id"], uuid=row["subject_uuid"]),
    )


def _echo(asset: Row) -> int | str | None:
    """The consent DataVault gave for an asset, as it gave it: a number as a
    number, a text as a text. A check from before that was kept
    (`consent_ref_is_number` NULL) goes by what the text looks like."""
    ref = asset["consent_ref"]
    if ref is None:
        return None
    text = str(ref)
    numeric = asset.get("consent_ref_is_number")
    if numeric is None:
        numeric = text.isascii() and text.isdigit()
    # A number that would not read back the same ("007") is not sent as one.
    if numeric and text.isascii() and text.isdigit() and str(int(text)) == text:
        return int(text)
    return text


def _as_sent(asset_ref: str, consent: int | str | None) -> dict[str, Any]:
    """An asset as it goes back: with the consent DataVault gave for it. One
    it gave no consent for goes without."""
    out: dict[str, Any] = {"asset_id": asset_ref}
    if consent is not None:
        out["consent_id"] = consent
    return out


def _guard(row: Row, role: Role | str) -> None:
    if not applies(row):
        raise Conflict(
            "Only an erasure request erases anything in DataVault.",
            code="datavault_not_an_erasure",
        )
    if not sm.may_act(role, rights.facts_of(row)):
        raise Forbidden("This request is not yours to act on")


async def gate(conn: Conn, what: Send) -> str | None:
    """Whether an instruction made ready may go now, or why not - the point
    after which it is DataVault's (review ARCH-8, 2026-11-20).

    Run in a short transaction of its own just before the call, never across
    it: it takes the lock a hold on the person takes, then reads the request
    and the hold afresh. A hold placed, the request closed or moved to the
    other office after the instruction was made ready withholds it; one placed
    after this commits finds the instruction gone, and the hold is recorded
    after it. An instruction DataVault has already answered may always be
    asked about again: it has it, and asking starts nothing new. One withheld
    stays as it was, unanswered, and goes - through this gate again - from
    "Check status" once nothing stands in its way."""
    if what.answered:
        return None
    await hold_repo.lock_person(conn, what.subject_user_id)
    request = await rights_repo.by_id(conn, what.request_id)
    if request is None:
        return "the request is gone"
    if request.get("office_code") != what.office:
        return "the request moved to the other office"
    if not what.again and (request["status"] == "closed" or str(request["status"]) not in WORKING):
        return "the request is no longer being worked on"
    if await _held(conn, request):
        return "a legal hold now stands on the person"
    return None


async def start(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> list[Send]:
    """A press of "Erase in DataVault": the instructions, written and ready to
    go. The caller commits before any of them is sent."""
    _guard(row, role)
    # One press at a time on a request: the second waits, then finds what the
    # first has sent.
    await repo.lock_erasures(conn, int(row["request_id"]))
    check = await repo.last_answer(conn, int(row["request_id"]))
    why_not = await _why_not(conn, row, has_check=check is not None, held=await _held(conn, row))
    if why_not:
        raise Conflict(why_not, code="datavault_erasure_not_now")
    link = await connection.for_erasure(conn)
    assert link is not None and link.erasure_url is not None and check is not None
    assets = await repo.assets_of(conn, int(check["check_id"]))
    inside, outside = await _in_scope(conn, row, assets)
    states = await repo.erasure_states(conn, int(row["request_id"]))
    going = _sendable(inside, states)
    if not going:
        raise Conflict(
            "There is nothing to send: everything this request reaches has been sent "
            "to DataVault, or it lists nothing the request reaches.",
            code="datavault_nothing_to_erase",
        )
    request_named, person_named = _named(row, link.id_format)
    sends: list[Send] = []
    for at in range(0, len(going), client.MAX_ERASURE_ASSETS):
        part: list[Row] = [
            {"asset_ref": str(a["asset_ref"]), "consent_sent": _echo(a)}
            for a in going[at : at + client.MAX_ERASURE_ASSETS]
        ]
        made = await repo.add_erasure(
            conn,
            request_id=int(row["request_id"]),
            check_id=int(check["check_id"]),
            id_format=link.id_format,
            sent_by=actor_id,
            assets=part,
        )
        sends.append(
            Send(
                erasure_id=int(made["erasure_id"]),
                erasure_uuid=str(made["erasure_uuid"]),
                request_id=int(row["request_id"]),
                reference=str(row["reference"]),
                subject_user_id=int(row["subject_user_id"]),
                erasure_url=link.erasure_url,
                api_key=link.api_key,
                api_key_header=link.api_key_header,
                id_format=link.id_format,
                request_named=request_named,
                person_named=person_named,
                assets=[_as_sent(p["asset_ref"], p["consent_sent"]) for p in part],
                again=False,
                office=row.get("office_code"),
            )
        )
    await audit.record(
        conn,
        event=Event.DATAVAULT_ERASURE_SENT,
        entity_type="rights_request",
        entity_id=int(row["request_id"]),
        subject_user_id=int(row["subject_user_id"]),
        actor_user_id=actor_id,
        detail={
            "reference": row["reference"],
            "assets": len(going),
            "instructions": len(sends),
            "left_out": _left_out(inside, outside),
            "confined_to_consent": bool(row.get("consent_id")),
        },
    )
    return sends


async def again(conn: Conn, row: Row, *, role: Role | str) -> list[Send]:
    """A press of "Check status": every instruction with an asset DataVault
    has not said the last word on, to be sent again as it was. On a closed
    request too."""
    _guard(row, role)
    link = await connection.for_erasure(conn)
    if link is None or link.erasure_url is None:
        raise Conflict(
            "The erasure address is not set. An administrator sets it under DataVault connection.",
            code="datavault_not_configured",
        )
    held = await _held(conn, row)
    sends: list[Send] = []
    withheld = 0
    for e in await repo.erasures_of(conn, int(row["request_id"])):
        if int(e["open_assets"]) == 0:
            continue
        if held and e["answered_at"] is None:
            # Never answered: for all we know never received, and sending it
            # now would start an erasure the hold stops.
            withheld += 1
            continue
        # Named as DataVault took it, whatever the switch says now: it is the
        # same instruction. One it has never answered it has not taken, and
        # is named as the switch says now.
        fmt = str(e["id_format"]) if e["answered_at"] is not None else link.id_format
        request_named, person_named = _named(row, fmt)
        named = await repo.erasure_assets(conn, int(e["erasure_id"]))
        sends.append(
            Send(
                erasure_id=int(e["erasure_id"]),
                erasure_uuid=str(e["erasure_uuid"]),
                request_id=int(row["request_id"]),
                reference=str(row["reference"]),
                subject_user_id=int(row["subject_user_id"]),
                erasure_url=link.erasure_url,
                api_key=link.api_key,
                api_key_header=link.api_key_header,
                id_format=fmt,
                request_named=request_named,
                person_named=person_named,
                assets=[_as_sent(str(a["asset_ref"]), a["consent_sent"]) for a in named],
                again=True,
                answered=e["answered_at"] is not None,
                office=row.get("office_code"),
            )
        )
    if not sends:
        if withheld:
            raise Conflict(
                "A legal hold stands on this person. An instruction DataVault has not "
                "answered is not sent until it is released.",
                code="datavault_erasure_not_now",
            )
        raise Conflict(
            "Nothing is waiting on DataVault for this request.", code="datavault_nothing_pending"
        )
    return sends


async def ask(what: Send, *, transport: Any = None) -> list[client.Outcome] | str:
    """DataVault's word on each asset, or the failure's code."""
    try:
        return await client.erase(
            erasure_url=what.erasure_url,
            api_key=what.api_key,
            api_key_header=what.api_key_header,
            erasure_id=what.erasure_uuid,
            request_id=what.request_named,
            person_id=what.person_named,
            assets=what.assets,
            transport=transport,
        )
    except client.DataVaultFailed as failed:
        return failed.code


async def store(
    conn: Conn, what: Send, answer: list[client.Outcome] | str, *, actor_id: int
) -> None:
    """One ask as it went."""
    failed = answer if isinstance(answer, str) else None
    await repo.record_ask(
        conn, what.erasure_id, asked_by=actor_id, failure=failed, id_format=what.id_format
    )
    detail: dict[str, Any] = {"reference": what.reference, "again": what.again}
    if failed:
        detail["outcome"] = "failed"
        detail["failure"] = failed
        if refused(failed):
            # Turned down, not taken: its assets may be sent again.
            detail["released"] = await repo.release_refused(
                conn, what.erasure_id, reason=f"Not taken: {failure_said(failed)}"
            )
    else:
        assert not isinstance(answer, str)
        named = {a["asset_id"] for a in what.assets}
        counts = dict.fromkeys(client.ERASURE_STATUSES, 0)
        for o in answer:
            if o.asset_ref not in named:
                continue  # not one this instruction named: nothing of ours
            counts[o.status] += 1
            await repo.set_outcome(
                conn,
                what.erasure_id,
                asset_ref=o.asset_ref,
                status=o.status,
                completed_at=o.completed_at,
                reason=o.reason,
            )
        detail["outcome"] = "answered"
        detail.update(counts)
    await audit.record(
        conn,
        event=Event.DATAVAULT_ERASURE_CHECKED,
        entity_type="rights_request",
        entity_id=what.request_id,
        subject_user_id=what.subject_user_id,
        actor_user_id=actor_id,
        detail=detail,
    )
    went_wrong = failed or (detail.get("failed") or 0)
    if went_wrong:
        # The instruction was refused, or DataVault could not erase some of it
        # (2026-11-20): the administrators and the request's office hear.
        from cmp.db.repositories import rights as rights_repo
        from cmp.domain import alerts

        request = await rights_repo.by_id(conn, what.request_id)
        await alerts.datavault_problem(
            conn,
            what=f"An erasure for request {what.reference}",
            failure=(
                failure_said(failed)
                if failed
                else f"{detail['failed']} asset(s) could not be erased"
            ),
            office=request.get("office_code") if request else None,
            marker=f"erasure:{what.erasure_uuid}:{failed or 'assets'}",
        )
