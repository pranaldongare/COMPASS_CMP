"""The access response: what the platform says about her, in one file.

Section 11 gives a data principal a summary of the personal data being
processed, the processing activities, and the identities of everyone it has
been shared with. Step 5 of the access flow is the platform answering that
from its own records - consents, the notices as she read them, withdrawals and
the disclosure register - with no ticket needed. Steps 6 to 9 add what the
holders returned and what the DPO wrote.

The file is JSON rather than a rendered document. It is the data, and a
person or a program can read it; a PDF would be a picture of the data with the
structure thrown away. Every timestamp is ISO-8601 and every identifier is a
uuid - the same rules as the API, because it is the API's answer written down.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from cmp.core.config import settings
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import exchange as exchange_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn

#: What the file does not contain, said inside the file, so a reader who has
#: only the file still knows the shape of what they were given.
_SCOPE_NOTE = (
    "This file is the Data Fiduciary's own record: consent given and withdrawn, the "
    "notice text as served, every disclosure recorded, and the returns from every "
    "party ticketed. Data held by a processor is described by that processor's "
    "return, not reproduced here. Consent records are evidence and are never erased."
)


def _clean(row: dict[str, Any], drop: tuple[str, ...] = ()) -> dict[str, Any]:
    """Strip internal keys: surrogate ids never leave the system."""
    return {
        k: v for k, v in row.items() if not k.endswith("_id") and k != "_row_id" and k not in drop
    }


async def build_access_package(
    conn: Conn,
    request: dict[str, Any],
    *,
    holders: list[dict[str, Any]],
    response_text: str,
    generated_at: datetime,
) -> bytes:
    """The response as bytes. See `build_response`."""
    return encode(
        await build_response(
            conn, request, holders=holders, response_text=response_text, generated_at=generated_at
        )
    )


def encode(package: dict[str, Any]) -> bytes:
    return json.dumps(package, indent=2, default=str, ensure_ascii=False).encode("utf-8")


async def build_response(
    conn: Conn,
    request: dict[str, Any],
    *,
    holders: list[dict[str, Any]],
    response_text: str,
    generated_at: datetime,
) -> dict[str, Any]:
    """Assemble the response for one request. Read-only; the caller stores it.

    Built for every request that is linked to an account, whatever its kind
    and whatever the outcome. "No records held anywhere" is an answer about
    the holders; her consents, the notices she read and the disclosures made
    are the platform's own record, and they go back to her regardless - that
    record *is* the answer to "what do you hold", even when it is all of it.
    """
    subject_id = int(request["subject_user_id"])
    subject = await user_repo.by_id(conn, subject_id) or {}

    consents: list[dict[str, Any]] = []
    for row in await consent_repo.consents_of_user(conn, subject_id):
        consent_id = int(row["consent_id"])
        served = await consent_repo.served_notice_text(conn, consent_id)
        grants = await consent_repo.grants_of(conn, consent_id)
        assets = await consent_repo.assets_for_consent(conn, consent_id)
        consents.append(
            {
                **_clean(row),
                "purposes": [_clean(g) for g in grants],
                "notice_as_served": _clean(served) if served else None,
                "assets_held": [_clean(a) for a in assets],
            }
        )

    disclosures = [_clean(d) for d in await exchange_repo.disclosures_for_user(conn, subject_id)]
    trail = [
        _clean(e, drop=("detail_json",))
        for e in await audit_repo.for_subject(conn, subject_id, limit=500)
    ]

    package = {
        "request": {
            "reference": request["reference"],
            "request_type": request["request_type"],
            "received_at": request["received_at"],
            "responded_at": generated_at,
            "response_period_days": settings.rights_response_period_days,
        },
        "data_fiduciary": {"contact": settings.notification_email_from},
        "data_principal": {
            "uuid": subject.get("uuid"),
            "full_name": subject.get("full_name"),
            "email": subject.get("email"),
            "mobile": subject.get("mobile"),
            "date_of_birth": subject.get("dob"),
        },
        "response": response_text,
        "outcome": request.get("outcome"),
        "scope": _SCOPE_NOTE,
        "summary": {
            "consents": len(consents),
            "consents_withdrawn": sum(1 for c in consents if c.get("is_withdrawal")),
            "disclosures": len(disclosures),
            "holders": len(holders),
            "holders_returned": sum(1 for h in holders if h["ticket_status"] == "returned"),
        },
        "consents": consents,
        "disclosures": disclosures,
        "holders": [
            {
                "holder": h["label"],
                "derived_from": h["derived_from"],
                "ticket_status": h["ticket_status"],
                "issued_at": h["issued_at"],
                "returned_at": h["returned_at"],
                "return_summary": h["return_summary"],
                "return_evidence_sha256": h["return_evidence_hash"],
            }
            for h in holders
        ],
        "gaps": [
            h["label"]
            for h in holders
            if h["ticket_status"] in ("issued", "escalated", "unreturned")
        ],
        "activity": trail,
        "your_rights": {
            "grievance": "You may raise a grievance about how this request was handled.",
            "board": (
                "If you remain unsatisfied you may complain to the Data Protection Board "
                "of India. The route to the Board is independent of ours."
            ),
        },
    }
    return package


def digest_text(package: dict[str, Any]) -> str:
    """The response as prose, for the mail that carries it.

    Everything the file says, at the level a person reads in an inbox: what
    was decided, every consent and withdrawal with its purposes, every
    disclosure, what each holder returned, and what is still outstanding.
    The file itself stays on the platform, downloaded from her account.
    """

    def day(value: Any) -> str:
        text = str(value or "")
        return text[:10] if text else "-"

    def names(purposes: list[dict[str, Any]], *, granted: bool) -> list[str]:
        return [
            str(x.get("purpose_name") or x.get("name") or x.get("purpose_code") or "purpose")
            for x in purposes
            if bool(x.get("granted")) is granted
        ]

    lines: list[str] = ["YOUR CONSENTS ON RECORD"]
    consents = package.get("consents", [])
    if consents:
        for c in consents:
            kind = "Withdrawal" if c.get("is_withdrawal") else "Consent"
            where = " · ".join(str(x) for x in (c.get("project_name"), c.get("site_label")) if x)
            lines.append(
                f"- {kind} on {day(c.get('affirmative_action_at'))}"
                + (f" · {where}" if where else "")
            )
            agreed = names(c.get("purposes", []), granted=True)
            declined = names(c.get("purposes", []), granted=False)
            if agreed:
                lines.append(f"    agreed: {', '.join(agreed)}")
            if declined:
                lines.append(f"    declined: {', '.join(declined)}")
            held = c.get("assets_held") or []
            if held:
                lines.append(f"    collected material recorded against this consent: {len(held)}")
    else:
        lines.append("- None. No consent is recorded for you on the platform.")

    lines += ["", "DISCLOSURES OF YOUR DATA"]
    disclosures = package.get("disclosures", [])
    if disclosures:
        for d in disclosures:
            to = (
                d.get("processor_name")
                or d.get("recipient")
                or d.get("legal_name")
                or "a processor"
            )
            when = day(d.get("exported_at") or d.get("disclosed_at"))
            lines.append(
                f"- {when} to {to}"
                + (f" for {d.get('project_name')}" if d.get("project_name") else "")
            )
    else:
        lines.append("- None recorded.")

    lines += ["", "WHAT EACH PARTY HOLDING YOUR DATA RETURNED"]
    holders = package.get("holders", [])
    if holders:
        for h in holders:
            if h.get("ticket_status") == "returned":
                lines.append(
                    f"- {h['holder']}: {h.get('return_summary') or 'returned without a summary'}"
                )
            else:
                lines.append(f"- {h['holder']}: not returned ({h.get('ticket_status')})")
    else:
        lines.append(
            "- No party beyond the platform itself was asked; nothing names one as holding "
            "your data."
        )
    gaps = package.get("gaps", [])
    if gaps:
        lines += [
            "",
            "STILL OUTSTANDING: "
            + ", ".join(map(str, gaps))
            + ". This response is partial; the gap is named rather than hidden.",
        ]
    return "\n".join(lines)
