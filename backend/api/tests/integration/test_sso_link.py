"""An employee consent link signs in through the organisation (ADR 0034).

Against the stub provider: the first sign-in of an employee the register has
not met waits for a mobile confirmed by code and then creates an active
`employee` account carrying the employee ID; a second link matches that
account without a new row; an asserted address on another account is a
conflict, refused and audited; a tampered assertion and a provider that does
not answer leave no account; a code is never sent on an `sso` link; the
session is a data principal's whatever the account's role; and an R&D site's
link may be `sso` too.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from cmp.auth.authentication import sso
from cmp.core.errors import Conflict, NotFound
from cmp.core.permissions import Role
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities
from tests.integration.hr_world import approved_version, legal_office
from tests.support.oidc_stub import StubProvider, install

pytestmark = pytest.mark.integration

MOBILE = "+919811112222"


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[StubProvider]:
    with install(monkeypatch) as provider:
        yield provider


@pytest.fixture
def codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Codes the SSO mobile gate queued, instead of queueing them."""
    from cmp.tasks import dispatch as dispatch_mod

    out: list[tuple[Any, ...]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        out.append(args)
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    return out


@pytest.fixture
async def link(conn: Any, seeded: dict[str, Any], request_context: Any) -> str:
    """An HR activity's `sso` link, as a raw token."""
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


def _employee(tag: str) -> str:
    return f"EMP-{tag}"


async def _through_provider(
    conn: Any, stub: StubProvider, token: str, **claims: Any
) -> sso.Outcome:
    url = await sso.start(conn, token=token)
    query = parse_qs(urlparse(url).query)
    code = stub.code_for(stub.id_token(nonce=query["nonce"][0], **claims))
    return await sso.callback(
        conn,
        state=query["state"][0],
        code=code,
        error=None,
        ip_address="203.0.113.9",
        user_agent="test",
    )


class TestAFirstSignIn:
    async def test_it_waits_for_a_mobile_then_creates_the_employee(
        self, conn: Any, stub: StubProvider, link: str, codes: list[Any]
    ) -> None:
        employee = _employee("A1001")
        outcome = await _through_provider(
            conn, stub, link, employee_id=employee, email="new.hire@corp.example"
        )
        assert outcome.kind == "mobile_needed" and outcome.pending_id
        assert await user_repo.by_employee_id(conn, employee) is None, "nothing yet"

        await sso.send_mobile_code(conn, token=link, pending_id=outcome.pending_id, mobile=MOBILE)
        [(number, code, _project)] = codes
        raw, session = await sso.confirm_mobile(
            conn,
            token=link,
            pending_id=outcome.pending_id,
            mobile=number,
            code=code,
            ip_address=None,
            user_agent=None,
        )
        assert raw and session.role == Role.DATA_SUBJECT.value
        account = await user_repo.by_employee_id(conn, employee)
        assert account is not None
        assert account["person_type"] == "employee"
        assert account["status"] == "active"
        assert account["is_minor"] is None, "her age is asked next, by the portal"
        events = await fetch_all(
            conn,
            "SELECT event_type FROM audit_log WHERE entity_type = 'auth_user' AND entity_id = %s",
            (account["id"],),
        )
        assert {"auth.sso_account_created", "auth.sso_signed_in"} <= {
            e["event_type"] for e in events
        }

        # The date of birth, then the notice and her consent - unchanged paths.
        await conn.execute(
            "UPDATE auth_user SET minor_until = DATE '1990-01-01' WHERE id = %s", (account["id"],)
        )
        served = await consent_service.serve_notice(
            conn, token=link, language_code="english", user_id=account["id"]
        )
        grants = {str(p["purpose_uuid"]): True for p in served["purposes"]}
        made = await consent_service.capture(
            conn,
            token=link,
            user_id=account["id"],
            language_code="english",
            grants=grants,
            action_type="checkbox_click",
            ip_address=None,
        )
        assert made["consent_uuid"]

    async def test_a_second_link_matches_the_same_employee(
        self, conn: Any, stub: StubProvider, link: str, codes: list[Any], seeded: dict[str, Any]
    ) -> None:
        employee = _employee("A1002")
        first = await _through_provider(conn, stub, link, employee_id=employee, email=None)
        await sso.send_mobile_code(conn, token=link, pending_id=first.pending_id, mobile=MOBILE)
        [(number, code, _)] = codes
        await sso.confirm_mobile(
            conn,
            token=link,
            pending_id=first.pending_id,
            mobile=number,
            code=code,
            ip_address=None,
            user_agent=None,
        )
        again = await _through_provider(conn, stub, link, employee_id=employee, email=None)
        assert again.kind == "signed_in"
        rows = await fetch_one(
            conn,
            "SELECT count(*) AS n FROM auth_user WHERE organization_id_hash = "
            "(SELECT organization_id_hash FROM auth_user WHERE id = %s)",
            ((await user_repo.by_employee_id(conn, employee))["id"],),
        )
        assert rows["n"] == 1


class TestRefusals:
    async def test_an_address_on_another_account_is_a_conflict(
        self, conn: Any, stub: StubProvider, link: str, seeded: dict[str, Any]
    ) -> None:
        outcome = await _through_provider(
            conn, stub, link, employee_id=_employee("A1003"), email="dco@test.local"
        )
        assert outcome.kind == "conflict"
        row = await fetch_one(
            conn,
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'auth.sso_identity_conflict' AND entity_id = %s""",
            (seeded["users"]["dco"]["id"],),
        )
        assert row is not None
        assert "dco@test.local" not in str(row["detail_json"]), "never the claims"

    async def test_a_tampered_assertion_writes_no_account(
        self, conn: Any, stub: StubProvider, link: str
    ) -> None:
        outcome = await _through_provider(
            conn, stub, link, employee_id=_employee("A1004"), audience="someone-else"
        )
        assert outcome.kind == "invalid"
        assert await user_repo.by_employee_id(conn, _employee("A1004")) is None

    async def test_a_provider_that_does_not_answer_is_reported_as_such(
        self, conn: Any, stub: StubProvider, link: str
    ) -> None:
        url = await sso.start(conn, token=link)
        query = parse_qs(urlparse(url).query)
        stub.down = True
        outcome = await sso.callback(
            conn,
            state=query["state"][0],
            code="whatever",
            error=None,
            ip_address=None,
            user_agent=None,
        )
        assert outcome.kind == "unavailable"

    async def test_a_state_is_used_once(self, conn: Any, stub: StubProvider, link: str) -> None:
        url = await sso.start(conn, token=link)
        state = parse_qs(urlparse(url).query)["state"][0]
        await sso.callback(
            conn, state=state, code=None, error="access_denied", ip_address=None, user_agent=None
        )
        with pytest.raises(NotFound):
            await sso.callback(
                conn, state=state, code="x", error=None, ip_address=None, user_agent=None
            )
        with pytest.raises(NotFound):
            await sso.callback(
                conn,
                state="never-issued-state",
                code="x",
                error=None,
                ip_address=None,
                user_agent=None,
            )

    async def test_a_mobile_on_another_account_is_refused(
        self, conn: Any, stub: StubProvider, link: str, seeded: dict[str, Any]
    ) -> None:
        outcome = await _through_provider(
            conn, stub, link, employee_id=_employee("A1005"), email=None
        )
        with pytest.raises(Conflict):
            await sso.send_mobile_code(
                conn, token=link, pending_id=outcome.pending_id, mobile="+915550000001"
            )


class TestTheLinkItself:
    async def test_a_code_is_never_sent_on_an_sso_link(
        self, conn: Any, link: str, codes: list[Any], seeded: dict[str, Any]
    ) -> None:
        await consent_service.send_contact_code(conn, token=link, contact="+915550000001")
        assert codes == []

    async def test_nobody_registers_by_form_on_an_sso_link(self, conn: Any, link: str) -> None:
        with pytest.raises(Conflict) as refused:
            await consent_service.register_subject(
                conn,
                token=link,
                full_name="Someone",
                mobile="+919833334444",
                email=None,
                dob="1990-01-01",
            )
        assert refused.value.code == "sso_link"

    async def test_a_staff_account_signs_in_as_a_data_principal(
        self, conn: Any, stub: StubProvider, link: str, seeded: dict[str, Any]
    ) -> None:
        await conn.execute(
            "UPDATE auth_user SET organization_id_hash = %s WHERE id = %s",
            (
                __import__("cmp.infrastructure.dkms.blind", fromlist=["index_of"]).index_of(
                    "text", _employee("A1006")
                ),
                seeded["users"]["dco"]["id"],
            ),
        )
        outcome = await _through_provider(
            conn, stub, link, employee_id=_employee("A1006"), email="dco@test.local"
        )
        assert outcome.kind == "signed_in"
        assert outcome.session is not None
        assert outcome.session.role == Role.DATA_SUBJECT.value
        assert outcome.session.account_role == Role.DCO.value

    async def test_an_r_and_d_site_link_may_sign_in_by_sso(
        self, conn: Any, stub: StubProvider, seeded: dict[str, Any], request_context: Any
    ) -> None:
        minted = await consent_service.create_link(
            conn,
            site_uuid=str(seeded["site"]["site_uuid"]),
            expires_at=datetime.now(UTC) + timedelta(days=1),
            max_uses=None,
            actor_id=int(seeded["users"]["dpo"]["id"]),
            role=Role.DPO.value,
            audience_mode="sso",
        )
        url = await sso.start(conn, token=minted["token"])
        assert "code_challenge" in url
