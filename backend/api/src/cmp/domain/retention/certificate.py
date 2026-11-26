"""The certificate of a closed retention review (ADR 0047).

What the organisation shows a regulator or an auditor: which consents the
review was about, why each ended and when its data fell due, who was asked,
what each answered - erased, anonymised and why, kept and why and until
when, or not held - who accepted it, and who closed the review. A PDF to
file, or a CSV to work with.

People appear by their consent and person numbers, never by name; the names
are those of the staff who answered and accepted. Reasons are opened for the
file, as a breach report's narrative is. Every download is on the trail.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.repositories import retention as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.dkms import unseal_value
from cmp.infrastructure.report_files import MIME, Content, Section, render

FORMATS = ("pdf", "csv")

_KIND = {
    "validity": "Consent validity",
    "retention": "Data retention",
}
_OUTCOME = {
    "erased": "Erased",
    "anonymised": "Anonymised",
    "kept": "Kept",
    "not_held": "Not held",
    "reviewed": "Reviewed",
}
_STATUS = {
    "open": "Not answered",
    "answered": "Answered, not accepted",
    "accepted": "Accepted",
    "sent_back": "Sent back",
    "not_needed": "Set aside: not needed",
}
_STATE = {"in": "In the review", "held": "Legal hold", "renewed": "Consented again"}


async def _name(value: Any) -> str:
    if value is None:
        return ""
    return str(await unseal_value("auth_user", "full_name", value) or "")


def _day(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%d")
    return value.isoformat()


async def build(conn: Conn, review_uuid: str) -> tuple[Content, Any]:
    from cmp.domain.retention.service import review as load
    from cmp.domain.retention.service import review_view

    row = await load(conn, review_uuid)
    if row["status"] != "closed":
        raise Conflict("A certificate is made once the review is closed.", code="review_not_closed")
    view = review_view(row)
    people = await repo.people_of(conn, int(row["review_id"]), state=None)
    acts = await repo.actions_of(conn, int(row["review_id"]))
    note = await unseal_value("retention_review", "close_note", row.get("close_note"))

    action_rows: list[list[Any]] = []
    for a in acts:
        reason = await unseal_value("retention_action", "reason", a.get("reason"))
        if row["kind"] == "validity" and a["reconsent"] is not None:
            answer = "Invite them again" if a["reconsent"] else "Do not invite them"
        else:
            answer = _OUTCOME.get(str(a["outcome"]), "") if a["outcome"] else ""
        action_rows.append(
            [
                a["label"],
                "Owner" if a["kind"] == "owner" else "Holder",
                _STATUS.get(str(a["status"]), str(a["status"])),
                answer,
                str(reason or ""),
                _day(a["keep_until"]),
                _day(a["answered_at"]),
                await _name(a.get("accepted_by_name")),
                _day(a["accepted_at"]),
            ]
        )
    people_rows = [
        [
            f"C-{p['consent_id']}",
            f"P-{p['auth_user_id']}",
            "Withdrawal" if p["ended_by"] == "withdrawal" else "Validity ran out",
            _day(p["due_at"]),
            _STATE.get(str(p["state"]), str(p["state"])),
            _day(p["notified_at"]),
            _day(p["invited_at"]),
        ]
        for p in people
    ]
    in_review = sum(1 for p in people if p["state"] == "in")
    content = Content(
        title=f"Retention certificate {row['reference']}",
        subtitle=f"{_KIND[str(row['kind'])]} - {row['project_name']}",
        about=[
            ("Reference", str(row["reference"])),
            ("Kind", _KIND[str(row["kind"])]),
            ("Office", str(row["office"]).upper()),
            ("Activity" if row["is_activity"] else "Project", str(row["project_name"])),
            ("Purpose", f"{row['purpose_code']} - {row['purpose_name']}"),
            ("Consent lasts", f"{view['validity_days']} days" if view["validity_days"] else "-"),
            (
                "Kept after the consent ends",
                f"{view['retention_days']} days" if view["retention_days"] else "-",
            ),
            ("People in the review", str(in_review)),
            ("Kept out by a legal hold", str(sum(1 for p in people if p["state"] == "held"))),
            ("Consented again", str(sum(1 for p in people if p["state"] == "renewed"))),
            ("First asked", _day(row["opened_at"])),
            ("Closed", _day(row["closed_at"])),
            ("Closed by", await _name(row.get("closed_by_name"))),
            ("Closing note", str(note or "-")),
        ],
        sections=[
            Section(
                heading="What each one asked answered",
                intro="Anonymising instead of erasing, and keeping, each carry their reason.",
                headers=[
                    "Asked",
                    "As",
                    "Status",
                    "Answer",
                    "Reason",
                    "Keep until",
                    "Answered",
                    "Accepted by",
                    "Accepted",
                ],
                rows=action_rows,
                widths=[3, 2, 2, 2, 5, 2, 2, 3, 2],
            ),
            Section(
                heading="The consents in the review",
                intro="By consent and person number; the consent register names them.",
                headers=[
                    "Consent",
                    "Person",
                    "Ended by",
                    "Fell due",
                    "State",
                    "Told before erasure",
                    "Invited again",
                ],
                rows=people_rows,
            ),
        ],
        notes=[
            "Made from the record of the review in the consent manager. Each answer, its "
            "acceptance and the closing are on the audit trail against the review."
        ],
        footer="Consents by number only: no person is named in this certificate.",
    )
    return content, row


async def download(
    conn: Conn, review_uuid: str, fmt: str, *, actor_id: int
) -> tuple[bytes, str, str]:
    if fmt not in FORMATS:
        raise ValidationFailed("Choose pdf or csv.", field="format")
    content, row = await build(conn, review_uuid)
    payload = render(content, fmt)
    await audit.record(
        conn,
        event=Event.RETENTION_CERTIFICATE_DOWNLOADED,
        entity_type="retention_review",
        entity_id=int(row["review_id"]),
        actor_user_id=actor_id,
        detail={"reference": row["reference"], "format": fmt},
    )
    return payload, f"{row['reference']}-certificate.{fmt}", MIME[fmt]
