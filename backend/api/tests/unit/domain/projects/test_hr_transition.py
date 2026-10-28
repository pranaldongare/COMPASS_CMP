"""The HR activity's transition (ADR 0033): in_draft -> approved, by the HR PoC.

Pure, as the rest of the state machine is. Every combination of the six
version facts is tried: the move is allowed only when all hold, and every
unmet one is named. An R&D project in draft is still offered the
submission to the DPO and nothing else, and an activity never is.
"""

from __future__ import annotations

from itertools import product

import pytest

from cmp.core.errors import TransitionNotPermitted
from cmp.core.permissions import Role
from cmp.domain.projects.state_machine import ProjectFacts, available, validate

FACTS = (
    "template_version_approved",
    "template_version_hash_matches",
    "has_notice",
    "purposes_within_version",
    "mandatory_purposes_included",
    "description_within_slot",
)


def _activity(**facts: bool) -> ProjectFacts:
    return ProjectFacts(office="hr", **facts)


@pytest.mark.parametrize("values", list(product([True, False], repeat=len(FACTS))))
def test_the_activity_goes_live_exactly_when_every_version_fact_holds(
    values: tuple[bool, ...],
) -> None:
    facts = _activity(**dict(zip(FACTS, values, strict=True)))
    [move] = available("in_draft", Role.HR_USER, facts)
    assert move["to"] == "approved"
    assert move["publishes_notice"] is True
    assert move["allowed"] is all(values)
    assert len(move.get("blockers", [])) == values.count(False)


def test_it_is_the_hr_poc_s_move_alone() -> None:
    ready = _activity(**dict.fromkeys(FACTS, True))
    for role in (Role.DPO, Role.LEGAL, Role.RND_USER, Role.ADMIN):
        assert available("in_draft", role, ready) == []
    with pytest.raises(TransitionNotPermitted):
        validate(current="in_draft", target="approved", role=Role.LEGAL, facts=ready)
    assert validate(
        current="in_draft", target="approved", role=Role.HR_USER, facts=ready
    ).publishes_notice


def test_an_activity_is_never_submitted_to_the_dpo() -> None:
    ready = _activity(**dict.fromkeys(FACTS, True))
    with pytest.raises(TransitionNotPermitted):
        validate(current="in_draft", target="pending_approval", role=Role.HR_USER, facts=ready)


def test_an_r_and_d_draft_is_still_submitted_and_never_goes_live_directly() -> None:
    study = ProjectFacts(**dict.fromkeys(FACTS, True))
    assert [m["to"] for m in available("in_draft", Role.RND_USER, study)] == ["pending_approval"]
    assert available("in_draft", Role.HR_USER, study) == []
    with pytest.raises(TransitionNotPermitted):
        validate(current="in_draft", target="approved", role=Role.RND_USER, facts=study)


@pytest.mark.parametrize(
    ("office", "closers"),
    [
        ("hr", {Role.HR_USER, Role.LEGAL}),
        ("rnd", {Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO}),
    ],
)
def test_each_office_closes_its_own(office: str, closers: set[Role]) -> None:
    facts = ProjectFacts(office=office)
    for role in Role:
        offered = [m["to"] for m in available("approved", role, facts)]
        assert offered == (["closed"] if role in closers else [])
