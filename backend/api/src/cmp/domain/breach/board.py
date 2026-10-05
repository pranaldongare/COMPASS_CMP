"""The Board's two documents, drafted from the register (S3-04).

Rule 7(2) asks the fiduciary to intimate the Board twice: **without delay**,
with the nature, extent, timing, location and likely impact (7(2)(a)); and
within 72 hours of becoming aware, or the longer period the Board allows, with
six items of detail (7(2)(b)(i)-(vi)). Both are drafted here from what the
register holds, at any point, as many times as the DPO likes - a draft read on
the first morning and the same draft read on the third say what was known each
time.

**The platform never submits.** These are documents a person reads, checks and
files through the Board's own channel; the submission is then recorded on the
duty with the reference the Board returned (`service.complete_duty`). Nothing
in `cmp.domain.breach` opens a connection to anywhere but this database and the
key service, and a test reads the source to keep it so.

**Nothing is left out quietly.** A fact the register does not yet hold is
named in `missing`, and item (vi) says in words when no notice has been sent,
rather than the item being absent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cmp.db.sql import Conn
from cmp.domain.breach import notices, service
from cmp.domain.breach.clock import Duty

Row = dict[str, Any]

#: What 7(2)(a) asks for, and where each comes from.
INTIMATION: tuple[tuple[str, str], ...] = (
    ("nature_extent", "The nature and extent of the breach"),
    ("timing", "Its timing"),
    ("location", "Where it occurred"),
    ("likely_impact", "Its likely impact"),
)

#: 7(2)(b)(ii)-(v): one assessment fact each.
REPORT_FACTS: tuple[tuple[str, str, str], ...] = (
    ("ii", "circumstances", "The events, circumstances and reasons leading to the breach"),
    ("iii", "mitigation", "Measures implemented or proposed to mitigate the risk"),
    ("iv", "caused_by_findings", "Findings on the person who caused the breach"),
    ("v", "remedial_measures", "Remedial measures taken to prevent recurrence"),
)


def _duty(detail: Row, duty: Duty) -> Row | None:
    return next((d for d in detail["obligations"] if d["duty"] == duty), None)


#: Said in `missing` while the incident is still being validated: both
#: documents may be drafted then, and say what they are not yet.
NOT_RECORDED = "Not yet recorded as a personal data breach"


def _references(detail: Row) -> Row:
    """The breach reference is what the Board is given; before a *yes* there is
    none, and the document is quoted by the incident's."""
    return {
        "reference": detail["reference"],
        "incident_reference": detail["incident_reference"],
        "breach_reference": detail["breach_reference"],
    }


def _timing(detail: Row) -> Row:
    return {
        "detected_at": detail["detected_at"],
        "began_at": detail["began_at"],
        "became_aware_at": detail["became_aware_at"],
    }


async def intimation(conn: Conn, *, breach_uuid: str) -> Row:
    """Rule 7(2)(a): the initial intimation, as the register now stands."""
    detail = await service.detail(conn, breach_uuid)
    latest = detail["assessment"] or {}
    missing = [NOT_RECORDED] if detail["breach_reference"] is None else []
    missing += [
        label
        for key, label in INTIMATION
        if (key == "timing" and detail["became_aware_at"] is None)
        or (key in ("nature_extent", "likely_impact") and not latest.get(key))
    ]
    return {
        "document": "initial_intimation",
        "basis": "Rule 7(2)(a)",
        **_references(detail),
        "title": detail["title"],
        "generated_at": datetime.now(UTC),
        "determination": detail["determination"],
        **_timing(detail),
        "location": detail["location"],
        "nature_extent": latest.get("nature_extent"),
        "likely_impact": latest.get("likely_impact"),
        "assessment_revision": latest.get("revision"),
        "missing": missing,
        "duty": _duty(detail, Duty.BOARD_INTIMATION),
    }


async def report(conn: Conn, *, breach_uuid: str) -> Row:
    """Rule 7(2)(b): the detailed report, all six items, as the register now stands."""
    detail = await service.detail(conn, breach_uuid)
    latest = detail["assessment"] or {}
    account = await notices.account_for_report(conn, breach_uuid=breach_uuid)
    missing = [NOT_RECORDED] if detail["breach_reference"] is None else []
    if not latest:
        missing.append("(i) No assessment has been recorded")
    facts = []
    for item, key, label in REPORT_FACTS:
        value = latest.get(key)
        if not value:
            missing.append(f"({item}) {label}")
        facts.append({"item": item, "label": label, "text": value})
    return {
        "document": "detailed_report",
        "basis": "Rule 7(2)(b)",
        **_references(detail),
        "title": detail["title"],
        "generated_at": datetime.now(UTC),
        "determination": detail["determination"],
        # (i) Updated and detailed information: the latest assessment, with
        # every determination and how many revisions came before.
        **_timing(detail),
        "location": detail["location"],
        "determinations": detail["determinations"],
        "assessment": detail["assessment"],
        "assessment_revisions": detail["assessment_revisions"],
        # (ii) to (v)
        "facts": facts,
        # (vi) The account of notices to principals - said in words when none
        # has been sent, never left out.
        "notices": account,
        "missing": missing,
        "duty": _duty(detail, Duty.BOARD_REPORT),
        "duties": detail["obligations"],
    }
