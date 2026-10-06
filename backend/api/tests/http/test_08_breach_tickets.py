"""Breach tickets over HTTP (S3-08).

The DPO assigns a ticket to a member of staff on a recorded breach; they read
it, write, attach a file and return it; the DPO sends it back and, once it is
returned again, closes it. Another holder is told it is not there, and so is
every holder who asks for the register. Two closes at once close once.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from cmp.core.config import settings
from tests.conftest import plain
from tests.http.conftest import DOMAIN, SessionFactory, fresh_email, last_code
from tests.http.contract import call
from tests.http.world import World, build

B = "/breaches/{breach_uuid}"
T = f"{B}/tickets/{{ticket_uuid}}"
MINE = "/breach-tickets/{ticket_uuid}"


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


@pytest.fixture(autouse=True)
def internal(monkeypatch: pytest.MonkeyPatch) -> None:
    """This suite's accounts are on its own reserved domain."""
    monkeypatch.setattr(settings, "breach_ticket_email_domains", (DOMAIN,))


def _at(hours_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


async def _recorded(http: httpx.AsyncClient, world: World) -> str:
    made = await call(
        http,
        "POST",
        "/breaches",
        session=world.dpo,
        expect=201,
        json={
            "title": "A shared drive open to all staff",
            "detected_at": _at(3),
            "location_kind": "platform",
        },
    )
    uuid = str(made.json()["breach_uuid"])
    await call(
        http,
        "POST",
        f"/breaches/{uuid}/determinations",
        template=f"{B}/determinations",
        session=world.dpo,
        json={"outcome": "yes", "reasoning": "Names were on it", "became_aware_at": _at(2)},
    )
    return uuid


async def _assign(
    http: httpx.AsyncClient, world: World, uuid: str, who: Any, **extra: Any
) -> dict[str, Any]:
    made = await call(
        http,
        "POST",
        f"/breaches/{uuid}/tickets",
        template=f"{B}/tickets",
        session=world.dpo,
        expect=201,
        json={"user_uuid": who.uuid, "instruction": "Export the drive's access log", **extra},
    )
    body: dict[str, Any] = made.json()
    return body


class TestTheTicket:
    async def test_assign_answer_send_back_and_close(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        uuid = await _recorded(http, world)
        made = await _assign(http, world, uuid, world.dco, answer_by=str(datetime.now(UTC).date()))
        ticket = str(made["ticket"]["ticket_uuid"])
        assert str(made["instruction"]).startswith("SE::")
        assert any(q[0].endswith("send_breach_ticket_waiting") for q in queued)

        # The holder: their ticket, and the register still not there.
        mine = await call(http, "GET", "/breach-tickets", session=world.dco)
        [listed] = [t for t in mine.json() if t["ticket_uuid"] == ticket]
        assert listed["breach_reference"].startswith("BR-") and listed["state"] == "issued"
        await call(http, "GET", f"/breaches/{uuid}", template=B, session=world.dco, expect=404)
        await call(
            http,
            "GET",
            f"/breaches/{uuid}/tickets",
            template=f"{B}/tickets",
            session=world.dco,
            expect=404,
        )
        detail = await call(
            http, "GET", f"/breach-tickets/{ticket}", template=MINE, session=world.dco
        )
        assert plain(detail.json()["ticket"]["instruction"]) == "Export the drive's access log"
        assert "title" not in detail.text and "A shared drive" not in detail.text

        # Holder B is told it is not there, on every route.
        for method, path, template in (
            ("GET", f"/breach-tickets/{ticket}", MINE),
            ("POST", f"/breach-tickets/{ticket}/return", f"{MINE}/return"),
        ):
            await call(
                http,
                method,
                path,
                template=template,
                session=world.rco,
                expect=(404, 422),
                data={"summary": "x", "outcome": "done"} if method == "POST" else None,
            )
        await call(
            http, "GET", f"/breach-tickets/{ticket}", template=MINE, session=world.rco, expect=404
        )

        # The holder writes with a file, and returns it.
        wrote = await call(
            http,
            "POST",
            f"/breach-tickets/{ticket}/messages",
            template=f"{MINE}/messages",
            session=world.dco,
            data={"body": "Exporting now"},
            files={"evidence": ("access.csv", b"user,at\nx,1\n", "text/csv")},
        )
        with_file = next(m for m in wrote.json()["messages"] if m["evidence_hash"])
        assert str(with_file["evidence_name"]).startswith("SE::")
        await call(
            http,
            "GET",
            f"/breach-tickets/{ticket}/messages/{with_file['message_uuid']}/evidence",
            template=f"{MINE}/messages/{{message_uuid}}/evidence",
            session=world.dco,
            check_sealed=False,
        )
        await call(
            http,
            "POST",
            f"/breach-tickets/{ticket}/return",
            template=f"{MINE}/return",
            session=world.dco,
            data={"summary": "Exported and kept", "outcome": "done"},
            files={"evidence": ("log.txt", b"kept", "text/plain")},
        )

        # The office: list, read, write, download, send back.
        office = await call(
            http, "GET", f"/breaches/{uuid}/tickets", template=f"{B}/tickets", session=world.dpo
        )
        [row] = office.json()
        assert row["state"] == "returned" and row["unread"] >= 2
        assert [m["move"] for m in row["moves"]] == ["send_back", "close", "withdraw"]
        read = await call(
            http, "GET", f"/breaches/{uuid}/tickets/{ticket}", template=T, session=world.dpo
        )
        assert read.json()["ticket"]["unread"] == 0
        await call(
            http,
            "GET",
            f"/breaches/{uuid}/tickets/{ticket}/messages/{with_file['message_uuid']}/evidence",
            template=f"{T}/messages/{{message_uuid}}/evidence",
            session=world.dpo,
            check_sealed=False,
        )
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets/{ticket}/messages",
            template=f"{T}/messages",
            session=world.dpo,
            data={"body": "Which retention applies?"},
        )
        back = await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets/{ticket}/send-back",
            template=f"{T}/send-back",
            session=world.dpo,
            json={"reason": "Include the guest accounts"},
        )
        assert back.json()["ticket"]["state"] == "issued"
        # The holder has no route to close; the office's answers them 404.
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets/{ticket}/close",
            template=f"{T}/close",
            session=world.dco,
            expect=404,
        )

        await call(
            http,
            "POST",
            f"/breach-tickets/{ticket}/return",
            template=f"{MINE}/return",
            session=world.dco,
            data={"summary": "Guest accounts too", "outcome": "done"},
        )
        # Two closes at once: one closes, the other is told it is closed.
        first, second = await asyncio.gather(
            call(
                http,
                "POST",
                f"/breaches/{uuid}/tickets/{ticket}/close",
                template=f"{T}/close",
                session=world.dpo,
                expect=(200, 409),
            ),
            call(
                http,
                "POST",
                f"/breaches/{uuid}/tickets/{ticket}/close",
                template=f"{T}/close",
                session=world.dpo,
                expect=(200, 409),
            ),
        )
        assert sorted([first.status_code, second.status_code]) == [200, 409]
        final = await call(
            http, "GET", f"/breaches/{uuid}/tickets/{ticket}", template=T, session=world.dpo
        )
        assert [e["kind"] for e in final.json()["ticket"]["events"]].count("closed") == 1

        # Reopen, withdraw: both need a reason, and get one.
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets/{ticket}/reopen",
            template=f"{T}/reopen",
            session=world.dpo,
            json={"reason": "One more share found"},
        )
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets/{ticket}/withdraw",
            template=f"{T}/withdraw",
            session=world.dpo,
            json={"reason": "Handled by the share's owner"},
        )

    async def test_a_return_raced_against_a_close_lands_once(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        """Return and close arrive together on an issued ticket. The breach row
        is taken first, so they act one after the other: either the return
        lands and the close follows, or the close is refused and the return
        stands. Never both refused, never a close of an unreturned ticket."""
        uuid = await _recorded(http, world)
        ticket = str((await _assign(http, world, uuid, world.rco))["ticket"]["ticket_uuid"])
        returned, closed = await asyncio.gather(
            call(
                http,
                "POST",
                f"/breach-tickets/{ticket}/return",
                template=f"{MINE}/return",
                session=world.rco,
                data={"summary": "Done", "outcome": "done"},
            ),
            call(
                http,
                "POST",
                f"/breaches/{uuid}/tickets/{ticket}/close",
                template=f"{T}/close",
                session=world.dpo,
                expect=(200, 409),
            ),
        )
        assert returned.status_code == 200
        final = await call(
            http, "GET", f"/breaches/{uuid}/tickets/{ticket}", template=T, session=world.dpo
        )
        kinds = [e["kind"] for e in final.json()["ticket"]["events"]]
        assert kinds == (["returned", "closed"] if closed.status_code == 200 else ["returned"])

    async def test_assigning_waits_for_a_recorded_breach_and_internal_staff(
        self, http: httpx.AsyncClient, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        made = await call(
            http,
            "POST",
            "/breaches",
            session=world.dpo,
            expect=201,
            json={"title": "Not yet validated", "detected_at": _at(1), "location_kind": "platform"},
        )
        uuid = str(made.json()["breach_uuid"])
        refused = await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets",
            template=f"{B}/tickets",
            session=world.dpo,
            expect=409,
            json={"user_uuid": world.dco.uuid, "instruction": "x"},
        )
        assert refused.json()["error"]["code"] == "breach_not_recorded"

        recorded = await _recorded(http, world)
        monkeypatch.setattr(settings, "breach_ticket_email_domains", ("organisation.example",))
        outside = await call(
            http,
            "POST",
            f"/breaches/{recorded}/tickets",
            template=f"{B}/tickets",
            session=world.dpo,
            expect=422,
            json={"user_uuid": world.dco.uuid, "instruction": "x"},
        )
        assert DOMAIN not in outside.text


# ---------------------------------------------------- breach-only logins (S3-09)

ACCESS = "cmp.notifications.send_breach_ticket_access"
MFA = "cmp.notifications.send_mfa_code"


async def _sign_in(http: httpx.AsyncClient, queued: Any, email: str, password: str) -> Any:
    """Password, then the emailed second factor, as every member of staff."""
    first = await call(http, "POST", "/auth/login", json={"login": email, "password": password})
    assert first.json()["mfa_required"] is True, "a breach-only login steps up like staff"
    partial = dict(first.cookies)
    full = await call(
        http,
        "POST",
        "/auth/mfa/verify",
        cookies=partial,
        headers={"X-CSRF-Token": partial["cmp_csrf"]},
        json={"code": last_code(queued, MFA)},
    )
    cookies = {**partial, **dict(full.cookies)}

    class _S:
        pass

    s = _S()
    s.cookies = cookies  # type: ignore[attr-defined]
    s.headers = {"X-CSRF-Token": cookies["cmp_csrf"]}  # type: ignore[attr-defined]
    return s


async def _set_password(http: httpx.AsyncClient, queued: Any, email: str, password: str) -> None:
    """The access email's code, on the reset page, as an invitation's."""
    assert plain(last_code(queued, ACCESS, position=1)) == email
    await call(
        http,
        "POST",
        "/auth/password/reset/confirm",
        expect=(200, 204),
        json={
            "email": email,
            "code": last_code(queued, ACCESS, position=3),
            "new_password": password,
        },
    )


class TestBreachOnlyLogins:
    async def test_a_stranger_is_asked_adds_a_colleague_and_keeps_a_read_only_login(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        uuid = await _recorded(http, world)
        engineer, colleague = fresh_email("eng"), fresh_email("col")

        # 1. The DPO asks somebody with no account, by email.
        made = await call(
            http,
            "POST",
            f"/breaches/{uuid}/tickets",
            template=f"{B}/tickets",
            session=world.dpo,
            expect=201,
            json={
                "full_name": "Http Engineer",
                "email": engineer,
                "instruction": "Pull the firewall log",
            },
        )
        assert made.json()["ticket"]["temporary_access"] == "pending"

        # 2. They set a password from the access email, sign in, and read it.
        await _set_password(http, queued, engineer, "HttpSuite!Breach1")
        eng = await _sign_in(http, queued, engineer, "HttpSuite!Breach1")
        me = await call(http, "GET", "/auth/me", session=eng)
        assert me.json()["role"] == "breach_holder"
        assert me.json()["nav"] == ["tickets", "notifications", "profile"]
        [mine] = (await call(http, "GET", "/breach-tickets", session=eng)).json()
        ticket = str(mine["ticket_uuid"])
        await call(http, "GET", f"/breaches/{uuid}", template=B, session=eng, expect=404)
        await call(http, "GET", "/dashboard", session=eng)

        # 3. They add a colleague, who signs in the same way and returns theirs.
        added = await call(
            http,
            "POST",
            f"/breach-tickets/{ticket}/colleagues",
            template=f"{MINE}/colleagues",
            session=eng,
            json={"full_name": "Http Colleague", "email": colleague, "note": "Check the switch"},
        )
        assert added.json()["ticket"]["ticket_uuid"] == ticket, "the adder's own ticket back"
        await _set_password(http, queued, colleague, "HttpSuite!Breach2")
        col = await _sign_in(http, queued, colleague, "HttpSuite!Breach2")
        [theirs] = (await call(http, "GET", "/breach-tickets", session=col)).json()
        await call(
            http,
            "POST",
            f"/breach-tickets/{theirs['ticket_uuid']}/return",
            template=f"{MINE}/return",
            session=col,
            data={"summary": "Switch config exported", "outcome": "done"},
        )
        await call(
            http,
            "POST",
            f"/breach-tickets/{ticket}/return",
            template=f"{MINE}/return",
            session=eng,
            data={"summary": "Firewall log exported", "outcome": "done"},
        )

        # 4. The DPO closes every ticket, then the breach.
        office = (
            await call(
                http, "GET", f"/breaches/{uuid}/tickets", template=f"{B}/tickets", session=world.dpo
            )
        ).json()
        assert {t["temporary_access"] for t in office} == {"active"}
        assert any(t["parent_ticket_uuid"] == ticket for t in office), "who added whom"
        for t in office:
            await call(
                http,
                "POST",
                f"/breaches/{uuid}/tickets/{t['ticket_uuid']}/close",
                template=f"{T}/close",
                session=world.dpo,
            )
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={"outcome": "no", "reasoning": "Contained"},
        )
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/obligations/org_board/complete",
            template=f"{B}/obligations/{{duty}}/complete",
            session=world.dpo,
            json={"occurred_at": _at(0.5), "reported_to": "The chair"},
        )
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/transition",
            template=f"{B}/transition",
            session=world.dpo,
            json={"to": "closed"},
        )

        # 5. Both keep their login, to read their ticket and nothing more
        #    (decided 2026-10-06): the breach is closed, so every write is refused.
        for session in (eng, col):
            [read] = (await call(http, "GET", "/breach-tickets", session=session)).json()
            assert read["state"] == "closed" and read["may_add_colleague"] is False
            await call(
                http,
                "POST",
                f"/breach-tickets/{read['ticket_uuid']}/messages",
                template=f"{MINE}/messages",
                session=session,
                data={"body": "One more thing"},
                expect=409,
            )
            await call(http, "GET", f"/breaches/{uuid}", template=B, session=session, expect=404)

        # 6. The administrator's End temporary access is the off switch.
        await call(
            http,
            "POST",
            f"/users/{me.json()['uuid']}/deactivate",
            template="/users/{user_uuid}/deactivate",
            session=world.admin,
        )
        await call(http, "GET", "/breach-tickets", session=eng, expect=401)
        await call(
            http,
            "POST",
            "/auth/login",
            json={"login": engineer, "password": "HttpSuite!Breach1"},
            expect=(401, 403),
        )
        await call(http, "GET", "/breach-tickets", session=col)

    async def test_the_role_is_never_granted_by_hand(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        await call(
            http,
            "POST",
            "/users",
            session=world.admin,
            expect=422,
            json={"full_name": "X", "email": fresh_email("x"), "role": "breach_holder"},
        )
