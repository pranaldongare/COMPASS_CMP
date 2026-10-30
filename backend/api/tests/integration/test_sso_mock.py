"""An `sso` link through the stand-in provider (`SSO_MOCK`, 2026-10-30).

The start sends the browser to the portal's stand-in page; a code goes to
whatever address is typed there; with it back, the callback runs exactly as
it does for the organisation's provider - an employee the register has not
met waits for a mobile, and the same address next time is the same
employee. A wrong code, an unknown sign-in and a cancelled one go nowhere.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from cmp.auth.authentication import sso, sso_mock
from cmp.core.config import settings
from cmp.core.errors import BadRequest, NotFound
from cmp.core.permissions import Role
from cmp.db.repositories import users as user_repo
from cmp.domain.hr import activities
from cmp.infrastructure.identity import mock
from tests.integration.hr_world import approved_version, legal_office

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def stand_in(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "sso_mock", True)
    yield


@pytest.fixture
def codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Codes queued for sending, instead of queueing them."""
    from cmp.tasks import dispatch as dispatch_mod

    out: list[tuple[Any, ...]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        out.append(args)
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    return out


@pytest.fixture
async def link(conn: Any, seeded: dict[str, Any], request_context: Any) -> str:
    world = await legal_office(conn, seeded)
    version = await approved_version(conn, world)
    made = await activities.create(
        conn,
        actor_id=int(world["poc"]["id"]),
        role=Role.HR_USER,
        category_uuid=str(world["category"]["category_uuid"]),
        template_version_uuid=str(version["version_uuid"]),
        purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
        name=f"Wellness {world['tag']}",
        description="Four lunchtime sessions.",
        audience_mode="sso",
        link_expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    return str(made["url_path"]).rsplit("/", 1)[-1]


def _address() -> str:
    return f"anyone.{uuid.uuid4().hex[:8]}@wherever.example"


async def _state(conn: Any, token: str) -> str:
    url = urlparse(await sso.start(conn, token=token))
    assert url.path == "/sso-mock"
    return parse_qs(url.query)["state"][0]


async def _signed_in_as(conn: Any, codes: list[Any], token: str, address: str) -> sso.Outcome:
    state = await _state(conn, token)
    await sso_mock.send_code(conn, state=state, email=address)
    to, code, _project = codes[-1]
    assert to == address.lower()
    back = parse_qs(urlparse(await sso_mock.confirm(state=state, email=address, code=code)).query)
    assert back["state"] == [state]
    return await sso.callback(
        conn,
        state=state,
        code=back["code"][0],
        error=None,
        ip_address="203.0.113.9",
        user_agent="test",
    )


async def test_any_address_signs_in_as_the_same_employee_every_time(
    conn: Any, link: str, codes: list[Any]
) -> None:
    address = _address()
    first = await _signed_in_as(conn, codes, link, address)
    assert first.kind == "mobile_needed" and first.pending_id

    mobile = f"+9198{uuid.uuid4().int % 10**8:08d}"
    await sso.send_mobile_code(conn, token=link, pending_id=first.pending_id, mobile=mobile)
    number, code, _project = codes[-1]
    await sso.confirm_mobile(
        conn,
        token=link,
        pending_id=first.pending_id,
        mobile=number,
        code=code,
        ip_address=None,
        user_agent=None,
    )
    account = await user_repo.by_employee_id(conn, mock.claims_for(address).employee_id)
    assert account is not None and account["person_type"] == "employee"

    again = await _signed_in_as(conn, codes, link, address.upper())
    assert again.kind == "signed_in" and again.session_token


async def test_a_wrong_code_goes_nowhere(conn: Any, link: str, codes: list[Any]) -> None:
    state = await _state(conn, link)
    address = _address()
    await sso_mock.send_code(conn, state=state, email=address)
    _to, code, _project = codes[-1]
    wrong = "000000" if code != "000000" else "111111"
    with pytest.raises(BadRequest):
        await sso_mock.confirm(state=state, email=address, code=wrong)


async def test_an_unknown_sign_in_is_not_there(conn: Any, codes: list[Any]) -> None:
    with pytest.raises(NotFound):
        await sso_mock.send_code(conn, state="x" * 43, email=_address())
    assert codes == []


async def test_cancelling_returns_to_the_link_as_cancelled(conn: Any, link: str) -> None:
    state = await _state(conn, link)
    back = parse_qs(urlparse(await sso_mock.cancel(state=state)).query)
    outcome = await sso.callback(
        conn,
        state=state,
        code=None,
        error=back["error"][0],
        ip_address=None,
        user_agent=None,
    )
    assert outcome.kind == "cancelled" and outcome.link_token == link
