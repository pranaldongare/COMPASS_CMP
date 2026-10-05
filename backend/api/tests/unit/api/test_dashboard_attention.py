"""'Needs attention' lists only what the role can act on.

An administrator was shown 'Accounts awaiting activation' for two data
principals who had not finished their own sign-up - nothing an administrator
can do, on a list whose whole promise is that everything on it is yours to
do. This pins the rule per role: every row names an action the role has, and
the rows that were information (lockouts that clear themselves, suspensions
made on purpose, drafts that are the author's, refusals in the log) are gone.
"""

from __future__ import annotations

import pytest

from cmp.api.routers.v1.dashboard import _ATTENTION, _attention

#: Keys and queues a role may only look at, never act on from the dashboard.
INFORMATION_ONLY: dict[str, set[str]] = {
    "admin": {"users_pending", "Lockouts (24h)", "Suspended sources and processors"},
    "dpo": {"draft_notices", "access_denials_7d", "grievances_about_dpo"},
}


@pytest.mark.parametrize("role", sorted(_ATTENTION))
def test_no_row_is_information_only(role: str) -> None:
    named = {spec.get("count") or spec.get("queue") for spec in _ATTENTION[role]}
    offenders = named & INFORMATION_ONLY.get(role, set())
    assert not offenders, f"{role} is shown things it cannot act on: {offenders}"


@pytest.mark.parametrize("role", sorted(_ATTENTION))
def test_every_row_opens_somewhere(role: str) -> None:
    """With everything counting one, every row carries a place to act."""
    specs = _ATTENTION[role]
    counts = {spec["count"]: 1 for spec in specs if "count" in spec}
    queues = [
        {"name": spec["queue"], "items": [{"overdue": True}]} for spec in specs if "queue" in spec
    ]
    queues.append({"name": "Tickets addressed to you", "items": [{"overdue": True}]})
    rows = _attention(role, counts, queues)
    assert len(rows) == len(specs)
    for row in rows:
        assert row["href"] and row["href"] != "/dashboard", row["label"]
        assert row["severity"] in {"critical", "warning", "info"}


def test_the_administrator_counts_staff_invitations_not_every_pending_account() -> None:
    rows = _attention("admin", {"users_pending": 2, "staff_invites_pending": 0}, [])
    assert rows == []
    rows = _attention("admin", {"staff_invites_pending": 1}, [])
    assert [r["key"] for r in rows] == ["staff_invites_pending"]
    assert rows[0]["href"].startswith("/users")


def test_the_dpo_is_asked_to_escalate_not_to_decide_grievances_about_the_dpo() -> None:
    rows = _attention("dpo", {"grievances_about_dpo": 3, "grievances_to_escalate": 0}, [])
    assert all(r["key"] != "grievances_about_dpo" for r in rows)
    rows = _attention("dpo", {"grievances_to_escalate": 1}, [])
    assert [r["key"] for r in rows] == ["grievances_to_escalate"]


def test_zero_counts_are_not_rows() -> None:
    assert _attention("dpo", {"requests_overdue": 0, "pending_approval": 0}, []) == []


def test_a_row_opens_the_list_its_label_describes() -> None:
    """A count is a claim about a subset, and its link has to open that subset
    (UX review 2026-10-05). "Sources with nobody accountable" opened every
    source; "due within 7 days" opened every request; "notice text awaiting
    approval" opened every notice."""
    expect = {
        ("dco_admin", "sources_without_owner"): "/sources?unowned=1",
        ("dpo", "requests_due_7d"): "/requests?due_soon=1",
        ("dpo", "unapproved_languages"): "/notices?languages=unapproved",
        ("admin", "grievances_about_dpo"): "/requests?type=grievance",
    }
    for (role, key), href in expect.items():
        [row] = _attention(role, {key: 1}, [])
        assert row["href"] == href, (role, key, row["href"])


def test_a_queue_row_opens_what_it_is_about() -> None:
    """A row about a collection or a site opens it, not its project; a queue at
    its row limit says it is not the whole list (UX review 2026-10-05)."""
    from cmp.api.routers.v1.dashboard import QUEUE_LIMIT, _finish_queues

    queues = [
        {
            "name": "Import exceptions",
            "items": [{"collection_uuid": "c-1", "project_uuid": "p-1"}],
        },
        {
            "name": "Sites awaiting a data source",
            "items": [{"site_uuid": "s-1", "project_uuid": "p-2"}] * QUEUE_LIMIT,
        },
        {"name": "Pending Approval", "items": [{"project_uuid": "p-3"}]},
    ]
    _finish_queues(queues)
    exceptions, sites, pending = queues
    assert exceptions["items"][0]["href"] == "/collections/c-1"
    assert sites["items"][0]["href"] == "/projects/p-2#sites"
    assert "href" not in pending["items"][0], "the card's own rule still serves the rest"
    assert sites["capped"] is True and exceptions["capped"] is False
