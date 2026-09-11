"""A data principal is never pointed at a staff console.

Reported: opening Notifications as a data subject led to an admin screen.

The data was never wrong - her feed is her own events and nothing else. What was
wrong was the *link* on each of them. `entity_href` resolved one route per
entity type regardless of who was reading, so her own registration event, whose
entity is `auth_user`, resolved to `/users` - the administrator's account
register. Every row in her feed carried a link into a console she has no
business on.

The interesting assertion here is the sweeping one: not that the three entity
types she actually sees are correct today, but that *nothing* in the resolver
can hand her a staff route. A new entity type is unlinkable for her until
somebody decides otherwise, and this is what holds that.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.permissions import Role, nav_for
from cmp.db.repositories import entities as entity_repo
from cmp.db.repositories.entities import _SPECS
from cmp.db.sql import fetch_one

#: What a data principal's console actually consists of. Everything else in the
#: product is staff-facing, and a link to any of it is the bug.
HER_PAGES = ("/my-consents", "/my-requests", "/profile", "/rights", "/dashboard")


def test_no_entity_can_send_her_to_a_staff_console() -> None:
    """The sweep, and the reason this file exists.

    Asserting the three types in her feed are right today would pass while the
    fourth one added next month sends her to `/users` again.
    """
    offenders = [
        f"{name} -> {spec.subject_href}"
        for name, spec in _SPECS.items()
        if spec.subject_href is not None and not spec.subject_href.startswith(HER_PAGES)
    ]
    assert not offenders, f"a data principal would be sent to a staff page: {offenders}"


def test_her_own_account_does_not_resolve_to_the_account_register() -> None:
    """The exact route reported. `/users` is the administrator's screen."""
    assert _SPECS["auth_user"].href == "/users", "staff still go to the register"
    assert _SPECS["auth_user"].subject_href == "/profile"


def test_an_unmapped_entity_gives_her_no_link_at_all() -> None:
    """A link to nowhere is better than a link to a refusal.

    `subject_href` defaults to None, so a type nobody has thought about is
    unlinkable for her rather than defaulting to the staff route - the safe
    direction for a default to fail in.
    """
    assert _SPECS["project"].subject_href is None
    assert _SPECS["import_batch"].subject_href is None


@pytest.mark.asyncio
class TestTheResolverPicksByReader:
    async def _subject_event(self, conn: Any, seeded: dict[str, Any]) -> list[dict[str, Any]]:
        subject = seeded["subject"]
        row = await fetch_one(
            conn,
            """INSERT INTO audit_log (event_type, actor_user_id, subject_user_id,
                                      entity_type, entity_id, detail_json)
               VALUES ('subject.registered', %s, %s, 'auth_user', %s, '{}'::jsonb)
               RETURNING log_uuid, event_type, entity_type, entity_id""",
            (subject["id"], subject["id"], subject["id"]),
        )
        assert row is not None
        return [dict(row)]

    async def test_she_gets_her_own_page(self, conn: Any, seeded: dict[str, Any]) -> None:
        rows = await entity_repo.attach(
            conn, await self._subject_event(conn, seeded), for_subject=True
        )
        assert rows[0]["entity_href"] == "/profile"

    async def test_staff_get_the_register(self, conn: Any, seeded: dict[str, Any]) -> None:
        """The same row, the same label, a different link. Staff have business
        on `/users`; she does not."""
        rows = await entity_repo.attach(conn, await self._subject_event(conn, seeded))
        assert rows[0]["entity_href"] == "/users"

    async def test_the_label_is_the_same_either_way(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """What happened is what happened. Only the route differs - a feed that
        described events differently by reader would be two accounts of one
        fact."""
        event = await self._subject_event(conn, seeded)
        hers = await entity_repo.attach(conn, [dict(event[0])], for_subject=True)
        theirs = await entity_repo.attach(conn, [dict(event[0])])
        assert hers[0]["entity_label"] == theirs[0]["entity_label"]
        assert hers[0]["entity_noun"] == theirs[0]["entity_noun"]


def test_her_navigation_offers_only_her_own_sections() -> None:
    """The other half of the same problem.

    The sidebar is built from this, and it was already right - which is why the
    bug needed a link from outside the sidebar to happen at all. Pinned so a
    section added to her nav has to be a decision rather than a slip.
    """
    assert set(nav_for(Role.DATA_SUBJECT)) == {"consents", "requests", "notifications", "profile"}


def test_her_feed_names_only_what_concerns_her() -> None:
    """The office's working on a request - holders, tickets, classification,
    scope - is internal, and she has no page it could open. Her feed and her
    trail carry what she did, what was done with her data, and how the
    request moved; the response and the outcome are hers."""
    from cmp.db.repositories.audit import SUBJECT_VISIBLE, visible_to_subject
    from cmp.domain.audit.service import Event

    internal = {
        Event.RIGHTS_HOLDERS_DERIVED,
        Event.RIGHTS_HOLDER_CONFIRMED,
        Event.RIGHTS_TICKET_ISSUED,
        Event.RIGHTS_TICKET_MESSAGE,
        Event.RIGHTS_TICKET_RETURNED,
        Event.RIGHTS_TICKET_SENT_BACK,
        Event.RIGHTS_CLASSIFIED,
        Event.RIGHTS_SCOPE_DERIVED,
        Event.RIGHTS_HOLDER_CONTACTED,
    }
    hers = {
        Event.RIGHTS_REQUEST_RECEIVED,
        Event.RIGHTS_ACKNOWLEDGED,
        Event.RIGHTS_RESPONDED,
        Event.RIGHTS_CLOSED,
        Event.CONSENT_GIVEN,
        Event.CONSENT_WITHDRAWN,
        Event.NOMINATION_ACCEPTED,
    }

    def name(e: object) -> str:
        return str(getattr(e, "value", e))

    for e in internal:
        assert name(e) not in SUBJECT_VISIBLE, f"{name(e)} is internal"
    for e in hers:
        assert name(e) in SUBJECT_VISIBLE, f"{name(e)} concerns her"
    every = {name(v) for v in vars(Event).values() if isinstance(v, str) and "." in v}
    for n in SUBJECT_VISIBLE:
        assert n in every, f"{n} is not an event"
    rows = [{"event_type": name(e)} for e in [*internal, *hers]]
    assert {r["event_type"] for r in visible_to_subject(rows)} == {name(e) for e in hers}
