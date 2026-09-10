"""The consent a request is confined to, said the same way everywhere.

A request made about one consent carries that consent, and every step that
follows - deriving holders, deriving the erasure scope, briefing a holder,
instructing a ticket, attaching the response - has to say so in the same
words and act on the same records. The words are here; the records are the
consent's chain, resolved by the repository.
"""

from __future__ import annotations

from typing import Any

Row = dict[str, Any]


def consent_scope(row: Row) -> dict[str, Any] | None:
    """The consent a request is confined to, from the request row, or None
    when the request is about everything the platform holds about her."""
    if not row.get("consent_id"):
        return None
    at = row.get("consent_at")
    notice = row.get("consent_notice_code") or ""
    version = row.get("consent_notice_version")
    return {
        "consent_uuid": str(row["consent_uuid"]),
        "project": row.get("consent_project"),
        "notice": f"{notice} v{version}" if version is not None else notice,
        "at": at.isoformat() if at is not None else None,
        "withdrawn": bool(row.get("consent_withdrawn")),
        "purposes": list(row.get("consent_purposes") or []),
    }


def scope_text(scope: dict[str, Any] | None) -> str:
    """One sentence for a ticket, a brief or a mail. Empty when unconfined."""
    if not scope:
        return ""
    when = (scope.get("at") or "")[:10]
    what = ", ".join(scope.get("purposes") or []) or "no purpose granted"
    return (
        f"This request is confined to the consent given on {when} for {scope.get('project')} "
        f"({scope.get('notice')}): {what}. Act only on data held under that consent; "
        "anything held under another consent is outside this request."
    )
