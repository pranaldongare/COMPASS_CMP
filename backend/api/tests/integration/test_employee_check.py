"""VerifyEmail at sign-in (2026-11-25, ADR 0046).

Console: a member of staff on the organisation's domains is asked about before
their code is sent - active signs in, inactive or no answer is refused, the
administrator is never asked, and staff on other domains sign in while the
administrator allows it. Portal: asked after the code, never refused; an
employee-only link refuses a person found not active. No address is ever on
the trail.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from cmp.auth.authentication import service as auth
from cmp.core.errors import Forbidden, ValidationFailed
from cmp.db.repositories import employee_check as repo
from cmp.domain.employees import check
from tests.conftest import hashed

PASSWORD = "TestPassw0rd!123"
BASE = "http://verify.test/api"


@pytest.fixture(autouse=True)
def no_queue(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Nothing reaches a broker: the code mail and the portal check are noted."""
    sent: list[Any] = []
    from cmp.tasks import dispatch

    monkeypatch.setattr(dispatch, "dispatch_required", lambda task, *a, **k: sent.append(task.name))
    monkeypatch.setattr(dispatch, "dispatch_optional", lambda task, *a, **k: sent.append(task.name))
    return sent


class Verify:
    """A stand-in for VerifyEmail: answers as told, and keeps what it was sent."""

    def __init__(self, *, active: bool = True, status: bool = True, fail: str | None = None):
        self.active, self.status, self.fail = active, status, fail
        self.asked: list[dict[str, Any]] = []
        self.headers: list[dict[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/VerifyEmail" and request.method == "POST"
        body = json.loads(request.content)
        self.asked.append(body)
        self.headers.append(dict(request.headers))
        if self.fail == "down":
            raise httpx.ConnectError("down", request=request)
        if self.fail == "500":
            return httpx.Response(500, json={"error": "internal detail never kept"})
        return httpx.Response(
            200,
            json={"MySingleID": body["MySingleID"], "IsActive": self.active, "Status": self.status},
        )


async def _set_up(
    conn: Any,
    seeded: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    verify: Verify,
    *,
    enabled: bool = True,
    allow_other: bool = True,
    domains: tuple[str, ...] = ("test.local",),
) -> None:
    admin = int(seeded["users"]["admin"]["id"])
    for d in await repo.domains(conn):
        await repo.remove_domain(conn, d)
    for d in domains:
        await check.add_domain(conn, d, actor_id=admin)
    await check.save(
        conn,
        base_url=BASE,
        api_key="s3cret-key",
        clear_api_key=False,
        api_key_header="X-API-Key",
        enabled=enabled,
        allow_other_domains=allow_other,
        actor_id=admin,
    )
    monkeypatch.setattr(check, "transport", httpx.MockTransport(verify))


async def _sign_in(conn: Any, login: str) -> dict[str, Any]:
    return await auth.authenticate(
        conn, login=login, password=PASSWORD, ip_address="127.0.0.1", user_agent="pytest"
    )


async def _trail(conn: Any, user_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """SELECT event_type, detail_json FROM audit_log
            WHERE entity_type = 'auth_user' AND entity_id = %s
              AND event_type IN ('employee.checked', 'employee.check_failed', 'auth.login_failed')
            ORDER BY log_id""",
        (user_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


def _own(detail: dict[str, Any]) -> dict[str, Any]:
    """A trail row's detail without what the trail adds to every row."""
    return {k: v for k, v in detail.items() if k not in ("_hash", "_prev", "ip", "request_id")}


async def _status(conn: Any, user_id: int) -> str | None:
    row = await repo.employment(conn, user_id)
    return row["employment_status"] if row else None


class TestConsole:
    async def test_an_active_employee_signs_in_and_the_answer_is_kept(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        verify = Verify()
        await _set_up(conn, seeded, monkeypatch, verify)
        await _sign_in(conn, "dpo@test.local")
        dpo = int(seeded["users"]["dpo"]["id"])
        assert verify.asked == [{"MySingleID": "dpo@test.local"}]
        assert verify.headers[0]["x-api-key"] == "s3cret-key"
        assert await _status(conn, dpo) == "active"
        trail = await _trail(conn, dpo)
        assert trail[-1]["event_type"] == "employee.checked"
        assert _own(trail[-1]["detail_json"]) == {"flow": "console_sign_in", "result": "active"}
        # The address asked about is nowhere on the trail.
        assert "test.local" not in json.dumps([t["detail_json"] for t in trail])

    async def test_a_leaver_is_refused_before_a_code_is_sent(
        self,
        conn: Any,
        seeded: dict[str, Any],
        monkeypatch: pytest.MonkeyPatch,
        no_queue: list[Any],
    ) -> None:
        await _set_up(conn, seeded, monkeypatch, Verify(active=False))
        with pytest.raises(Forbidden, match="not list you as an active employee"):
            await _sign_in(conn, "dpo@test.local")
        dpo = int(seeded["users"]["dpo"]["id"])
        assert await _status(conn, dpo) == "inactive"
        assert _own((await _trail(conn, dpo))[-1]["detail_json"]) == {
            "cause": "not_active_employee"
        }
        assert "cmp.authentication.send_mfa_code" not in no_queue

    async def test_not_known_to_the_organisation_is_not_active(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        await _set_up(conn, seeded, monkeypatch, Verify(active=True, status=False))
        with pytest.raises(Forbidden):
            await _sign_in(conn, "dco@test.local")

    @pytest.mark.parametrize("fail", ["down", "500"])
    async def test_no_answer_refuses_the_console(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fail: str
    ) -> None:
        await _set_up(conn, seeded, monkeypatch, Verify(fail=fail))
        with pytest.raises(Forbidden, match="could not confirm your employment"):
            await _sign_in(conn, "dpo@test.local")
        dpo = int(seeded["users"]["dpo"]["id"])
        assert await _status(conn, dpo) is None
        failed = [t for t in await _trail(conn, dpo) if t["event_type"] == "employee.check_failed"]
        assert failed[-1]["detail_json"]["failure"] in ("unreachable", "status_500")
        assert "internal detail" not in json.dumps(failed)

    async def test_the_administrator_is_never_asked_about(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        verify = Verify(fail="down")
        await _set_up(conn, seeded, monkeypatch, verify, allow_other=False)
        await _sign_in(conn, "admin@test.local")
        assert verify.asked == []

    async def test_other_domains_sign_in_unchecked_until_the_administrator_says_not(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        verify = Verify(fail="down")
        await _set_up(conn, seeded, monkeypatch, verify, domains=("company.example",))
        await _sign_in(conn, "dpo@test.local")
        assert verify.asked == []
        admin = int(seeded["users"]["admin"]["id"])
        await check.save(
            conn,
            base_url=BASE,
            api_key=None,
            clear_api_key=False,
            api_key_header=None,
            enabled=True,
            allow_other_domains=False,
            actor_id=admin,
        )
        with pytest.raises(Forbidden, match="not on one of the organisation's domains"):
            await _sign_in(conn, "dpo@test.local")

    async def test_switched_off_nothing_is_asked(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        verify = Verify(fail="down")
        await _set_up(conn, seeded, monkeypatch, verify, enabled=False)
        await _sign_in(conn, "dpo@test.local")
        assert verify.asked == []


class TestPortal:
    async def test_the_account_s_company_address_is_asked_about_and_kept(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        verify = Verify(active=False)
        await _set_up(conn, seeded, monkeypatch, verify, domains=("company.example",))
        subject = seeded["subject"]
        await conn.execute(
            """UPDATE auth_user SET secondary_email = 'person@company.example',
                                   secondary_email_hash = %s WHERE id = %s""",
            (hashed("email", "person@company.example"), subject["id"]),
        )
        found = await check.portal_subject(conn, str(subject["uuid"]))
        assert found is not None
        user_id, email, link = found
        assert email == "person@company.example"
        answer = await check.ask(link, email)
        await check.record(conn, user_id=user_id, flow=check.PORTAL, answer=answer)
        assert await check.refuses_employee_link(conn, user_id)

    async def test_no_answer_never_refuses_on_the_portal(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        await _set_up(conn, seeded, monkeypatch, Verify(fail="down"))
        user_id = int(seeded["subject"]["id"])
        answer = await check.ask((await check.settings_for_sign_in(conn)).link, "p@test.local")
        await check.record(conn, user_id=user_id, flow=check.PORTAL, answer=answer)
        assert answer.result == "failed"
        assert not await check.refuses_employee_link(conn, user_id)

    async def test_a_portal_sign_in_queues_the_check(
        self, conn: Any, seeded: dict[str, Any], no_queue: list[Any]
    ) -> None:
        """The dispatch is in the sign-in path; the check itself runs later."""
        import inspect

        source = inspect.getsource(auth.verify_subject_otp)
        assert "check_account" in source and "dispatch_optional" in source


class TestSettings:
    async def test_the_address_is_checked_and_the_key_never_served(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        admin = int(seeded["users"]["admin"]["id"])
        base: dict[str, Any] = {
            "api_key": None,
            "clear_api_key": False,
            "api_key_header": None,
            "actor_id": admin,
            "allow_other_domains": True,
        }
        with pytest.raises(ValidationFailed, match="without /VerifyEmail"):
            await check.save(conn, base_url=f"{BASE}/VerifyEmail", enabled=True, **base)
        with pytest.raises(ValidationFailed):
            await check.save(conn, base_url="ftp://x.example", enabled=True, **base)
        with pytest.raises(ValidationFailed, match="before switching it on"):
            await check.save(conn, base_url=None, enabled=True, **base)
        out = await check.save(
            conn, base_url=BASE, enabled=True, **{**base, "api_key": "zz-never-served-42"}
        )
        assert out["api_key_set"] is True
        assert "zz-never-served-42" not in json.dumps(
            {k: v for k, v in out.items() if k != "domains"}, default=str
        )

    async def test_other_domains_cannot_be_refused_with_no_domain_listed(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        admin = int(seeded["users"]["admin"]["id"])
        for d in await repo.domains(conn):
            await repo.remove_domain(conn, d)
        with pytest.raises(ValidationFailed, match="Add the organisation's domains"):
            await check.save(
                conn,
                base_url=None,
                api_key=None,
                clear_api_key=False,
                api_key_header=None,
                enabled=False,
                allow_other_domains=False,
                actor_id=admin,
            )

    async def test_a_domain_is_one_and_lower_case(self, conn: Any, seeded: dict[str, Any]) -> None:
        admin = int(seeded["users"]["admin"]["id"])
        rows = await check.add_domain(conn, "@Company.Example", actor_id=admin)
        assert "company.example" in [r["domain"] for r in rows]
        with pytest.raises(ValidationFailed):
            await check.add_domain(conn, "someone@company.example", actor_id=admin)
        assert await check.is_company_address(conn, "a@mail.company.example")
        assert not await check.is_company_address(conn, "a@notcompany.example")
