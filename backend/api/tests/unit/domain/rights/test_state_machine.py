"""The rights request transition table, tested as a specification.

The negatives carry the weight. Anyone can show that a verified, classified
request moves to in progress; what protects the flow is that nothing moves
*around* the gates - that an unverified request cannot start, that a request
with tickets out cannot reach collation until every gap has been chased, that
closure is not a transition anybody can call, and that only the DPO acts unless
the complaint is about the DPO.
"""

from __future__ import annotations

import itertools

import pytest

from cmp.core.enums import RightsRequestStatus as S
from cmp.core.errors import TransitionNotPermitted
from cmp.core.permissions import Role
from cmp.domain.rights.state_machine import (
    OPEN_BEFORE_COLLATION,
    RequestFacts,
    actors_for,
    available,
    may_act,
    validate,
)

READY = RequestFacts(verified=True, classified=True)

# The moves the generic transition route permits, per role. Closure is
# deliberately absent: it is made by responding, which records the outcome.
LEGAL: set[tuple[S, S, Role]] = {
    (S.RECEIVED, S.IN_PROGRESS, Role.DPO),
    (S.IN_PROGRESS, S.AWAITING_HOLDERS, Role.DPO),
    (S.IN_PROGRESS, S.COLLATING, Role.DPO),
    (S.AWAITING_HOLDERS, S.COLLATING, Role.DPO),
    (S.COLLATING, S.CLOSED, Role.DPO),
}


class TestTheTable:
    @pytest.mark.parametrize(("current", "target", "role"), list(itertools.product(S, S, Role)))
    def test_every_combination_matches_the_table(self, current: S, target: S, role: Role) -> None:
        """All 175 (from, to, role) triples, not just the five that are legal."""
        facts = RequestFacts(
            verified=True,
            classified=True,
            tickets_issued=1,
            tickets_outstanding=0,
            tickets_unescalated=0,
        )
        if (current, target, role) in LEGAL:
            validate(current=current, target=target, role=role, facts=facts)
        else:
            with pytest.raises(TransitionNotPermitted):
                validate(current=current, target=target, role=role, facts=facts)

    def test_closed_is_terminal(self) -> None:
        assert available(S.CLOSED, Role.DPO, READY) == []


class TestTheGatesBeforeWork:
    def test_an_unverified_request_cannot_start(self) -> None:
        with pytest.raises(TransitionNotPermitted) as raised:
            validate(current=S.RECEIVED, target=S.IN_PROGRESS, role=Role.DPO, facts=RequestFacts())
        assert raised.value.code == "transition_blocked"
        assert "not verified" in raised.value.message

    def test_a_failed_verification_blocks_before_anything_else(self) -> None:
        facts = RequestFacts(verification_failed=True, classified=True)
        with pytest.raises(TransitionNotPermitted) as raised:
            validate(current=S.RECEIVED, target=S.IN_PROGRESS, role=Role.DPO, facts=facts)
        assert "failed" in raised.value.message

    def test_free_text_must_be_classified_first(self) -> None:
        with pytest.raises(TransitionNotPermitted) as raised:
            validate(
                current=S.RECEIVED,
                target=S.IN_PROGRESS,
                role=Role.DPO,
                facts=RequestFacts(verified=True),
            )
        assert "classified" in raised.value.message

    def test_erasure_waits_for_withdrawal_or_erasure_to_be_settled(self) -> None:
        """Step 4 of the erasure flow: she clicks erase expecting deletion, or
        withdraw expecting deletion. The DPO confirms which before anything moves."""
        facts = RequestFacts(request_type="erasure", verified=True, classified=True)
        [option] = available(S.RECEIVED, Role.DPO, facts)
        assert option["allowed"] is False
        assert "withdrawal or erasure" in str(option["blocked_by"])

        settled = RequestFacts(
            request_type="erasure", verified=True, classified=True, intent_confirmed=True
        )
        assert available(S.RECEIVED, Role.DPO, settled)[0]["allowed"] is True

    def test_a_nominee_waits_for_the_event_to_be_evidenced(self) -> None:
        facts = RequestFacts(verified=True, classified=True, nominee=True)
        [option] = available(S.RECEIVED, Role.DPO, facts)
        assert option["allowed"] is False
        assert "evidenced" in str(option["blocked_by"])

    def test_a_grievance_about_the_dpo_waits_for_a_reviewer(self) -> None:
        facts = RequestFacts(
            request_type="grievance", verified=True, classified=True, about_dpo=True
        )
        [option] = available(S.RECEIVED, Role.ADMIN, facts)
        assert option["allowed"] is False
        assert "independent" in str(option["blocked_by"])


class TestHoldersAndTheClock:
    def test_awaiting_holders_needs_a_ticket(self) -> None:
        options = {o["to"]: o for o in available(S.IN_PROGRESS, Role.DPO, READY)}
        assert options["awaiting_holders"]["allowed"] is False
        assert options["collating"]["allowed"] is True, "no tickets means nothing to wait for"

    def test_collation_is_blocked_while_a_ticket_is_out_and_unchased(self) -> None:
        """Escalate once, then respond partial and on time. The clock does not pause."""
        out = RequestFacts(
            verified=True,
            classified=True,
            tickets_issued=2,
            tickets_outstanding=1,
            tickets_unescalated=1,
        )
        [option] = available(S.AWAITING_HOLDERS, Role.DPO, out)
        assert option["allowed"] is False
        assert "escalate" in str(option["blocked_by"]).lower()

        chased = RequestFacts(
            verified=True,
            classified=True,
            tickets_issued=2,
            tickets_outstanding=1,
            tickets_unescalated=0,
        )
        assert available(S.AWAITING_HOLDERS, Role.DPO, chased)[0]["allowed"] is True

    def test_closure_is_made_by_responding(self) -> None:
        [option] = available(S.COLLATING, Role.DPO, READY)
        assert option["to"] == "closed"
        assert option["via"] == "respond"

    def test_erasure_cannot_close_with_an_undecided_item(self) -> None:
        facts = RequestFacts(
            request_type="erasure", verified=True, classified=True, items_undecided=2
        )
        [option] = available(S.COLLATING, Role.DPO, facts)
        assert option["allowed"] is False
        assert "basis" in str(option["blocked_by"])


class TestWhoActs:
    def test_the_dpo_owns_every_request(self) -> None:
        assert actors_for(RequestFacts()) == frozenset({Role.DPO})

    def test_the_administrator_only_where_the_complaint_is_about_the_dpo(self) -> None:
        """Accountability cannot review itself and be credible."""
        assert Role.ADMIN in actors_for(RequestFacts(about_dpo=True))
        assert not may_act(Role.ADMIN, RequestFacts())
        assert may_act(Role.ADMIN, RequestFacts(about_dpo=True))

    @pytest.mark.parametrize(
        "role", [Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.RND_USER, Role.DATA_SUBJECT]
    )
    def test_nobody_else_acts(self, role: Role) -> None:
        assert not may_act(role, RequestFacts(about_dpo=True))
        assert available(S.RECEIVED, role, READY) == []

    def test_an_unknown_role_fails_closed(self) -> None:
        assert not may_act("auditor", RequestFacts())


def test_the_early_exits_are_open_until_collation() -> None:
    assert {S.RECEIVED, S.IN_PROGRESS, S.AWAITING_HOLDERS} == OPEN_BEFORE_COLLATION
