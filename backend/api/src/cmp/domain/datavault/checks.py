"""A rights request's check of what DataVault holds of the person (0070).

The DPO or Legal presses "Check in DataVault" on a request, or the platform
asks by itself when the holders it has just found include a project's DCO
Admin - the person who would otherwise be asked to go and look. Either way
it is one call, in three steps so that no database transaction is held open
while another system is waited on:

1. `prepare` - on a connection: is this request one to ask about, is
   DataVault set up, and which consents are this person's;
2. `ask` - the call, with no connection held;
3. `store` - in a transaction: the check, what it listed, and the trail.

What is sent: the request's reference and the person's Person ID (the
product owner, 2026-11-13). What comes back is kept as sent, and each
asset's consent and project are matched to ours only among this person's own
consents in the request's office - by uuid or by number, whichever DataVault
used - so an identifier that belongs to somebody else, or to the other
office's project, resolves to nothing.

Who sees it: the office that answers the request, in full; and a DCO Admin
holder, on their own ticket, the assets of the project they answer for. A
later check that fails does not unsay an earlier answer: the page shows the
last answer and, beside it, that the last attempt failed.

The check changes nothing else. It adds no holder, moves no ticket and
decides nothing about erasure; a request with no check behaves as it did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cmp.core.errors import Conflict, Forbidden
from cmp.core.permissions import Role
from cmp.db.repositories import datavault as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.datavault import connection
from cmp.domain.rights import service as rights
from cmp.domain.rights import state_machine as sm
from cmp.infrastructure import datavault as client

Row = dict[str, Any]

#: Why a call was not answered, in the office's words. A code not listed
#: (a status the list does not name) reads as the last line.
FAILURES: dict[str, str] = {
    "timeout": "DataVault did not answer in time.",
    "unreachable": "DataVault could not be reached.",
    "unreadable": "DataVault answered, but not in the agreed format.",
    "too_many": f"DataVault listed more than {client.MAX_ASSETS} assets; a part is not read.",
    "status_401": "DataVault refused the key.",
    "status_403": "DataVault refused the key.",
    "status_404": "DataVault does not know this address, or this person.",
}


def failure_said(code: str) -> str:
    if code in FAILURES:
        return FAILURES[code]
    if code.startswith("status_"):
        return f"DataVault answered with an error ({code.removeprefix('status_')})."
    return "The check did not complete."


@dataclass(frozen=True)
class Ask:
    """Everything the call and its recording need, read before the call."""

    request_id: int
    reference: str
    subject_user_id: int
    base_url: str
    api_key: str | None
    api_key_header: str
    consents: list[Row]


def _askable(row: Row) -> str | None:
    """Why this request cannot be checked, or None."""
    if row.get("subject_user_id") is None:
        return (
            "This request is not linked to a person yet, and DataVault is asked by "
            "Person ID. Verify identity first."
        )
    if row["status"] == "closed":
        return f"{row['reference']} is closed."
    return None


async def prepare(conn: Conn, row: Row, *, role: Role | str | None) -> Ask:
    """`role` None: the platform's own call, already decided by its caller."""
    if role is not None and not sm.may_act(role, rights.facts_of(row)):
        raise Forbidden("This request is not yours to act on")
    why_not = _askable(row)
    if why_not:
        raise Conflict(why_not, code="datavault_not_askable")
    ready = await connection.ready(conn)
    if ready is None:
        raise Conflict(
            "DataVault is not set up. An administrator sets its address under "
            "DataVault connection.",
            code="datavault_not_configured",
        )
    return Ask(
        request_id=int(row["request_id"]),
        reference=str(row["reference"]),
        subject_user_id=int(row["subject_user_id"]),
        base_url=ready["base_url"],
        api_key=ready["api_key"],
        api_key_header=ready["api_key_header"],
        consents=await repo.consents_of_person(
            conn, int(row["subject_user_id"]), office_id=row.get("office_id")
        ),
    )


async def ask(what: Ask, *, transport: Any = None) -> list[client.Held] | str:
    """The assets, or the failure's code."""
    try:
        return await client.lookup(
            base_url=what.base_url,
            api_key=what.api_key,
            api_key_header=what.api_key_header,
            request_ref=what.reference,
            person_no=what.subject_user_id,
            transport=transport,
        )
    except client.DataVaultFailed as failed:
        return failed.code


def _matched(what: Ask, held: list[client.Held]) -> list[Row]:
    """Each asset with our consent and project, where DataVault named one of
    this person's. A consent names its project, so a matched consent settles
    the project too when DataVault's own does not match."""
    by_consent: dict[str, Row] = {}
    by_project: dict[str, int] = {}
    for c in what.consents:
        by_consent[str(c["consent_uuid"]).lower()] = c
        by_consent[str(c["consent_id"])] = c
        by_project[str(c["project_uuid"]).lower()] = int(c["project_id"])
        by_project[str(c["project_id"])] = int(c["project_id"])
    out: list[Row] = []
    for h in held:
        consent = by_consent.get((h.consent_ref or "").lower())
        project_id = by_project.get((h.project_ref or "").lower())
        if project_id is None and consent is not None:
            project_id = int(consent["project_id"])
        out.append(
            {
                "asset_ref": h.asset_ref,
                "consent_ref": h.consent_ref,
                "project_ref": h.project_ref,
                "consent_id": int(consent["consent_id"]) if consent else None,
                "project_id": project_id,
                "mid": h.mid,
                "datapath": h.datapath,
            }
        )
    return out


async def store(
    conn: Conn, what: Ask, answer: list[client.Held] | str, *, actor_id: int | None
) -> None:
    """The check as it went. `actor_id` None: the platform asked."""
    failed = answer if isinstance(answer, str) else None
    assets = [] if failed else _matched(what, answer)  # type: ignore[arg-type]
    check = await repo.add_check(
        conn,
        request_id=what.request_id,
        asked_by=actor_id,
        outcome="failed" if failed else "answered",
        failure=failed,
        asset_count=len(assets),
    )
    await repo.add_assets(conn, int(check["check_id"]), assets)
    detail: dict[str, Any] = {
        "reference": what.reference,
        "automatic": actor_id is None,
        "outcome": "failed" if failed else "answered",
    }
    if failed:
        detail["failure"] = failed
    else:
        detail["assets"] = len(assets)
        detail["projects"] = len({a["project_id"] for a in assets if a["project_id"]})
        detail["unmatched"] = sum(1 for a in assets if a["project_id"] is None)
    await audit.record(
        conn,
        event=Event.DATAVAULT_CHECKED,
        entity_type="rights_request",
        entity_id=what.request_id,
        subject_user_id=what.subject_user_id,
        actor_user_id=actor_id,
        detail=detail,
    )


def _asset(a: Row) -> Row:
    return {
        "asset_ref": a["asset_ref"],
        "consent_ref": a["consent_ref"],
        "project_ref": a["project_ref"],
        "consent_uuid": a["consent_uuid"],
        "consent_no": a["consent_no"],
        "project_uuid": a["project_uuid"],
        "project_no": a["project_no"],
        "project_name": a["project_name"],
        "mid": a["mid"],
        "datapath": a["datapath"],
    }


def _check(k: Row) -> Row:
    return {
        "check_uuid": k["check_uuid"],
        "asked_at": k["asked_at"],
        "automatic": bool(k["automatic"]),
        "asked_by_name": k["asked_by_name"],
        "outcome": k["outcome"],
        "failure": k["failure"],
        "failure_said": failure_said(str(k["failure"])) if k["failure"] else None,
        "asset_count": int(k["asset_count"]),
    }


async def overview(conn: Conn, row: Row, *, role: Role | str) -> Row:
    """What the request page shows: whether DataVault can be asked, the last
    answer with its assets, and the last attempt if it failed after that."""
    configured = await connection.ready(conn) is not None
    why_not = _askable(row)
    answered = await repo.last_answer(conn, int(row["request_id"]))
    last = await repo.last_check(conn, int(row["request_id"]))
    return {
        "configured": configured,
        "may_check": configured and why_not is None and sm.may_act(role, rights.facts_of(row)),
        "why_not": why_not if configured else None,
        "answer": _check(answered) if answered else None,
        "assets": (
            [_asset(a) for a in await repo.assets_of(conn, int(answered["check_id"]))]
            if answered
            else []
        ),
        "last_failure": _check(last) if last and last["outcome"] == "failed" else None,
    }


async def for_ticket(conn: Conn, holder_uuid: str, user_id: int) -> Row | None:
    """What a DCO Admin sees on their own ticket: the assets DataVault listed
    for the project they answer for, as of the last answer. None for any other
    ticket, and before DataVault has answered for the request."""
    holder = await repo.dco_admin_holder(conn, holder_uuid, user_id)
    if holder is None:
        return None
    answered = await repo.last_answer(conn, int(holder["request_id"]))
    if answered is None:
        return None
    assets = await repo.assets_of(
        conn, int(answered["check_id"]), project_id=int(holder["project_id"])
    )
    return {"asked_at": answered["asked_at"], "assets": [_asset(a) for a in assets]}


def names_a_dco_admin(holders: list[Row]) -> bool:
    """Whether the holders found include a project's DCO Admin (0069): the
    case the platform asks DataVault for by itself."""
    return any(
        h.get("derived_from") == "project_owner" and h.get("is_activity") is False for h in holders
    )


async def wanted_automatically(conn: Conn, row: Row, holders: list[Row]) -> bool:
    """After holders were found: ask by itself only if a DCO Admin is among
    them, the request can be asked about, DataVault is set up, and it has not
    answered for this request already - Find holders may be pressed again, and
    the office has its button for a fresh look."""
    if not names_a_dco_admin(holders) or _askable(row) is not None:
        return False
    if await connection.ready(conn) is None:
        return False
    return await repo.last_answer(conn, int(row["request_id"])) is None


__all__ = [
    "Ask",
    "ask",
    "failure_said",
    "for_ticket",
    "names_a_dco_admin",
    "overview",
    "prepare",
    "store",
    "wanted_automatically",
]
