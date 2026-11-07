"""When a request looks for the reports she sent through the public link, when
it may erase her from them, and what a mail says of them, decided without a
database (0065)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from cmp.domain.rights import execution, public_reports


def _request(**over: Any) -> dict[str, Any]:
    return {
        "reference": "RR-2026-0001",
        "request_type": "erasure",
        "verification_status": "verified",
        "status": "in_progress",
        "consent_id": None,
        **over,
    }


@pytest.mark.parametrize(
    ("over", "said"),
    [
        ({"verification_status": "pending"}, public_reports.NOT_VERIFIED),
        ({"verification_status": "failed"}, public_reports.NOT_VERIFIED),
        ({"request_type": "grievance"}, public_reports.NOT_THIS_KIND),
        ({"request_type": "correction"}, public_reports.NOT_THIS_KIND),
        ({"consent_id": 7}, public_reports.CONFINED),
    ],
    ids=["pending", "failed", "grievance", "correction", "confined"],
)
def test_nothing_is_looked_for_until_it_may_be(over: dict[str, Any], said: str) -> None:
    assert public_reports.why_not_look(_request(**over)) == said


@pytest.mark.parametrize("kind", ["access", "erasure"])
def test_a_verified_access_or_erasure_request_looks(kind: str) -> None:
    assert public_reports.why_not_look(_request(request_type=kind)) is None


@pytest.mark.parametrize(
    ("over", "held", "code"),
    [
        ({"request_type": "access"}, False, "not_erasure"),
        ({"consent_id": 7}, False, "not_erasure"),
        ({"status": "received"}, False, "request_not_started"),
        ({"status": "received", "verification_status": "pending"}, False, "request_not_started"),
        ({"status": "closed"}, False, "request_closed"),
        ({}, True, "legal_hold"),
    ],
    ids=["access", "confined", "received", "unverified", "closed", "held"],
)
def test_an_erasure_waits_for_what_it_needs(over: dict[str, Any], held: bool, code: str) -> None:
    refused = public_reports.why_not_erase(_request(**over), held=held)
    assert refused is not None and refused[0] == code and refused[1]


def test_a_closed_request_is_refused_in_the_words_every_closed_request_is() -> None:
    refused = public_reports.why_not_erase(_request(status="closed"), held=False)
    assert refused is not None and refused[1].startswith("RR-2026-0001 is closed.")


@pytest.mark.parametrize("status", ["in_progress", "awaiting_holders", "collating"])
def test_a_started_erasure_may_erase(status: str) -> None:
    assert public_reports.why_not_erase(_request(status=status), held=False) is None


def _entry(reference: str, *, erased: bool = False) -> dict[str, Any]:
    when = datetime(2026, 11, 1, 9, 30, tzinfo=UTC)
    if erased:
        return {
            "reference": reference,
            "received_at": when,
            "dismissed_at": when,
            "reporter_erased_at": datetime(2026, 11, 7, tzinfo=UTC),
            "outcome": public_reports.ERASED,
        }
    return {
        "reference": reference,
        "received_at": when,
        "reported_by": {"full_name": "Asha Rao", "email": "asha@example.org"},
        "title": "A laptop left on a train",
        "noticed_at": None,
        "what_you_told_us": {"incident_details": "It had the participant list on it"},
        "cyber_attack": None,
        "dismissed_at": datetime(2026, 11, 2, tzinfo=UTC),
        "outcome": public_reports.NOT_TAKEN_UP,
    }


def test_a_mail_gives_the_number_the_dates_and_the_title_and_never_a_name_or_an_address() -> None:
    lines = public_reports.digest_lines(
        [_entry("INC-2026-0001"), _entry("INC-2026-0002", erased=True)], erasure=True
    )
    text = "\n".join(lines)
    assert lines[0] == "REPORTS YOU SENT THROUGH THE PUBLIC LINK"
    assert "@" not in text and "Asha" not in text
    assert "It had the participant list" not in text, "the words are in the file, not the mail"
    first, second = lines[1], lines[2]
    assert "INC-2026-0001" in first and "2026-11-01" in first and "2026-11-02" in first
    assert "A laptop left on a train" in first and "erased" not in first
    assert "INC-2026-0002" in second and "your name and email were erased" in second
    assert lines[-1] == execution.KEPT_OF_A_REPORT


def test_an_access_mail_says_nothing_of_what_was_kept() -> None:
    lines = public_reports.digest_lines([_entry("INC-2026-0001")], erasure=False)
    assert execution.KEPT_OF_A_REPORT not in lines


def test_no_report_is_no_section() -> None:
    assert public_reports.digest_lines([], erasure=True) == []


def _listed(n: int, *, erased: bool = False) -> dict[str, Any]:
    when = datetime(2026, 11, 1, tzinfo=UTC)
    return {
        "report_uuid": f"00000000-0000-4000-8000-{n:012d}",
        "reference": f"INC-2026-{n:04d}",
        "reporter_name": None if erased else "SE::name",
        "reporter_email": None if erased else "SE::email",
        "title": "SE::title",
        "received_at": when,
        "dismissed_at": when,
        "reporter_erased_at": when if erased else None,
    }


async def test_a_request_lists_fifty_and_counts_them_all() -> None:
    """A stranger can send many: the page lists the oldest fifty still naming
    her, then those already erased, and says how many there are."""
    found = {
        "looked": True,
        "not_looked_because": None,
        "unavailable": False,
        "open": [_listed(n) for n in range(60)],
        "erased": [_listed(99, erased=True)],
    }
    # A request with no account: no hold to look up, so no database is needed.
    shown = await public_reports.view(
        None,  # type: ignore[arg-type]
        _request(subject_user_id=None),
        role="dpo",
        result=found,
    )
    assert shown is not None
    assert [i["reference"] for i in shown["items"]] == [
        *(f"INC-2026-{n:04d}" for n in range(50)),
        "INC-2026-0099",
    ]
    assert (shown["total"], shown["erased"], shown["may_erase"]) == (60, 1, True)
