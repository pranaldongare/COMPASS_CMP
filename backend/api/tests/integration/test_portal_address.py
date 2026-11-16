"""The portal's address, kept by the administrator (0072).

Every link to the data principal's portal starts with it: the configured
address until one is set, the one set from then on, in every process within
`TTL_S`. It is an origin and nothing more, and each change is on the trail.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from cmp.core import portal_address as held
from cmp.core.config import settings
from cmp.core.errors import ValidationFailed
from cmp.db.sql import fetch_all
from cmp.domain import portal_address
from cmp.domain.breach import settings as breach_settings

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def nothing_remembered() -> Iterator[None]:
    held.forget()
    yield
    held.forget()


@pytest.mark.parametrize(
    ("typed", "kept"),
    [
        ("http://10.20.30.40:3001", "http://10.20.30.40:3001"),
        ("  https://portal.example.org/ ", "https://portal.example.org"),
        ("http://[2001:db8::1]:3001", "http://[2001:db8::1]:3001"),
    ],
)
def test_an_origin_is_kept_as_one(typed: str, kept: str) -> None:
    assert held.as_origin(typed) == kept


@pytest.mark.parametrize(
    "typed",
    [
        "10.20.30.40:3001",
        "ftp://portal.example.org",
        "https://portal.example.org/c",
        "https://portal.example.org?x=1",
        "https://portal.example.org#x",
        "https://someone@portal.example.org",
        "https://portal.example.org:99999",
        "https://portal .example.org",
        "javascript://portal.example.org",
        "https://",
    ],
)
def test_anything_else_is_not_an_address(typed: str) -> None:
    assert held.as_origin(typed) is None


async def test_until_one_is_set_the_configured_address_is_used(
    conn: Any, seeded: dict[str, Any]
) -> None:
    shown = await portal_address.overview(conn)
    assert shown["portal_url"] is None
    assert shown["in_use"] == shown["configured_url"] == settings.public_base_url.rstrip("/")
    assert held.portal_base() == settings.public_base_url.rstrip("/")


async def test_setting_it_is_shown_recorded_and_can_be_undone(
    conn: Any, seeded: dict[str, Any]
) -> None:
    admin = seeded["users"]["admin"]["id"]
    saved = await portal_address.save(conn, portal_url="http://10.20.30.40:3001/", actor_id=admin)
    assert saved["portal_url"] == saved["in_use"] == "http://10.20.30.40:3001"
    assert saved["updated_by_name"] is not None and saved["updated_at"] is not None

    back = await portal_address.save(conn, portal_url="  ", actor_id=admin)
    assert back["portal_url"] is None and back["in_use"] == back["configured_url"]

    trail = await fetch_all(
        conn,
        """SELECT detail_json AS detail FROM audit_log
            WHERE event_type = 'portal_address.changed' ORDER BY log_id DESC LIMIT 2""",
    )
    assert [t["detail"]["address"] for t in trail] == [None, "http://10.20.30.40:3001"]
    assert all(t["detail"]["changed"] for t in trail)


async def test_what_is_not_an_address_is_refused_and_nothing_changes(
    conn: Any, seeded: dict[str, Any]
) -> None:
    with pytest.raises(ValidationFailed) as refused:
        await portal_address.save(
            conn,
            portal_url="https://portal.example.org/c/abc",
            actor_id=seeded["users"]["admin"]["id"],
        )
    assert refused.value.field == "portal_url"
    assert (await portal_address.overview(conn))["portal_url"] is None


def test_links_start_with_the_address_in_use_and_follow_it() -> None:
    """What the saving process is told (`remember`) is what the next link
    starts with; forgotten, the database is read again."""
    held.remember("http://10.20.30.40:3001")
    assert held.portal_base() == "http://10.20.30.40:3001"
    assert breach_settings.report_link() == "http://10.20.30.40:3001/report-incident"

    held.forget()
    assert (
        breach_settings.report_link() == f"{settings.public_base_url.rstrip('/')}/report-incident"
    )


def test_a_database_that_cannot_be_read_leaves_the_last_address_standing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    held.remember("http://10.20.30.40:3001")
    monkeypatch.setattr(held, "TTL_S", -1.0)

    def down() -> str | None:
        raise OSError("no database")

    monkeypatch.setattr(held, "_read", down)
    assert held.portal_base() == "http://10.20.30.40:3001"
    held.forget()
    assert held.portal_base() == settings.public_base_url.rstrip("/")
