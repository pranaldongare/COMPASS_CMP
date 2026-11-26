"""Retention reviews over HTTP (0076, ADR 0047).

The officer's register and settings, the one asked answering in the console,
and an outside processor answering by its link: the link alone opens nothing,
the code goes to the address the link was sent to, and the answer waits for
the officer. Every route is the officer's, the one asked's own, or the link's.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cmp.db.repositories import registry as registry_repo
from tests.http.conftest import SessionFactory, last_code
from tests.http.contract import call
from tests.http.world import World, build

REVIEW = "/retention/reviews/{review_uuid}"
ACTION = REVIEW + "/actions/{action_uuid}"
LINK = "/retention-links/{token}"


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


async def _user(committed: Any, user_id: int) -> dict[str, Any]:
    row = await (
        await committed.execute(
            """SELECT u.id, u.uuid, u.role::text AS role, u.email, o.office_code
                 FROM auth_user u LEFT JOIN office o ON o.office_id = u.office_id
                WHERE u.id = %s""",
            (user_id,),
        )
    ).fetchone()
    return dict(row)


async def test_the_register_the_settings_and_both_ways_of_answering(
    http: httpx.AsyncClient,
    world: World,
    session_for: SessionFactory,
    committed: Any,
    queued: Any,
) -> None:
    dpo = world.dpo
    for who in (world.dco, world.rnd, world.admin):
        await call(http, "GET", "/retention/reviews", session=who, expect=403)
        await call(http, "POST", "/retention/refresh", session=who, expect=403)
    await call(http, "GET", "/retention-actions", session=world.principal, expect=403)

    # The settings: checked, then saved.
    got = await call(http, "GET", "/retention/settings", session=dpo)
    assert got.json()["notice_hours"] >= 0
    body = {
        "reminder_days": [90, 30, 7],
        "notice_hours": 48,
        "action_days": 30,
        "escalate_after_days": 14,
    }
    await call(
        http,
        "PUT",
        "/retention/settings",
        session=dpo,
        expect=422,
        json={**body, "reminder_days": [0]},
    )
    await call(http, "PUT", "/retention/settings", session=dpo, json=body)
    await call(http, "GET", "/retention/settings", session=world.admin)

    # The world's consent runs out and its data must go; the processor it was
    # exported to has a respondent with no console login.
    await committed.execute("SELECT set_config('app.office', 'all', false)")
    await committed.execute(
        """UPDATE purpose SET consent_validity_period = interval '-2 days',
                              retention_period = interval '1 day'
            WHERE purpose_uuid = %s""",
        (world.purpose_uuid,),
    )
    processor = await (
        await committed.execute(
            "SELECT processor_id FROM processor WHERE processor_uuid = %s",
            (world.processor_uuid,),
        )
    ).fetchone()
    await registry_repo.add_respondent(
        committed,
        int(processor["processor_id"]),
        name="Retention respondent",
        contact="retention-respondent@processor.example",
        user_id=None,
    )

    ran = await call(http, "POST", "/retention/refresh", session=dpo)
    assert ran.json()["reviews_made"] >= 1

    reviews = await call(
        http, "GET", "/retention/reviews", session=dpo, params={"kind": "retention"}
    )
    ours = [r for r in reviews.json() if r["project_uuid"] == world.project_uuid]
    assert len(ours) == 1 and ours[0]["status"] == "in_progress"
    review = ours[0]
    detail = await call(
        http, "GET", f"/retention/reviews/{review['review_uuid']}", session=dpo, template=REVIEW
    )
    actions = {a["kind"]: a for a in detail.json()["actions_list"]}
    assert set(actions) == {"owner", "processor"}
    assert "person_no" in detail.json()["people_list"][0]

    # The owner answers in the console: only theirs, and an anonymisation needs a reason.
    owner_id = (
        await (
            await committed.execute(
                "SELECT user_id FROM retention_action WHERE action_uuid = %s",
                (actions["owner"]["action_uuid"],),
            )
        ).fetchone()
    )["user_id"]
    owner_row = await _user(committed, int(owner_id))
    owner = await session_for(owner_row["role"], user=owner_row)
    mine = await call(http, "GET", "/retention-actions", session=owner)
    assert actions["owner"]["action_uuid"] in [a["action_uuid"] for a in mine.json()]
    path = f"/retention-actions/{actions['owner']['action_uuid']}"
    await call(http, "GET", path, session=owner, template="/retention-actions/{action_uuid}")
    await call(
        http,
        "GET",
        path,
        session=world.rco,
        expect=404,
        template="/retention-actions/{action_uuid}",
    )
    await call(
        http,
        "POST",
        f"{path}/answer",
        session=owner,
        expect=422,
        template="/retention-actions/{action_uuid}/answer",
        json={"outcome": "anonymised"},
    )
    await call(
        http,
        "POST",
        f"{path}/answer",
        session=owner,
        template="/retention-actions/{action_uuid}/answer",
        json={"outcome": "erased"},
    )

    base = f"/retention/reviews/{review['review_uuid']}/actions"
    back = await call(
        http,
        "POST",
        f"{base}/{actions['owner']['action_uuid']}/send-back",
        session=dpo,
        template=ACTION + "/send-back",
        json={"reason": "Say where it was erased from."},
    )
    assert back.json()["status"] == "sent_back"
    await call(
        http,
        "POST",
        f"{path}/answer",
        session=owner,
        template="/retention-actions/{action_uuid}/answer",
        json={"outcome": "erased", "reason": "From the rig and the archive."},
    )
    await call(
        http,
        "POST",
        f"{base}/{actions['owner']['action_uuid']}/accept",
        session=dpo,
        template=ACTION + "/accept",
    )

    # The processor, by its link.
    url = next(
        args[-1]
        for name, args in reversed(queued)
        if name == "cmp.notifications.send_retention_action_link"
    )
    token = url.rsplit("/", 1)[1]
    opened = await call(http, "GET", f"/retention-links/{token}", template=LINK)
    assert opened.json()["signed_in"] is False
    assert "retention-respondent@processor.example" not in opened.text
    await call(
        http, "GET", f"/retention-links/{token}/action", template=LINK + "/action", expect=401
    )
    await call(http, "POST", f"/retention-links/{token}/code", template=LINK + "/code")
    code = last_code(queued, "cmp.notifications.send_retention_link_code", position=1)
    verified = await call(
        http,
        "POST",
        f"/retention-links/{token}/verify",
        template=LINK + "/verify",
        json={"code": code},
    )
    cookie = dict(verified.cookies)
    read = await call(
        http, "GET", f"/retention-links/{token}/action", template=LINK + "/action", cookies=cookie
    )
    assert read.json()["review"]["reference"] == review["reference"]
    answered = await call(
        http,
        "POST",
        f"/retention-links/{token}/answer",
        template=LINK + "/answer",
        cookies=cookie,
        json={"outcome": "not_held"},
    )
    assert answered.json()["action"]["status"] == "answered"
    await call(
        http,
        "POST",
        f"/retention-links/{token}/sign-out",
        template=LINK + "/sign-out",
        cookies=cookie,
        expect=204,
    )

    await call(
        http,
        "POST",
        f"{base}/{actions['processor']['action_uuid']}/accept",
        session=dpo,
        template=ACTION + "/accept",
    )
    closed = await call(
        http,
        "POST",
        f"/retention/reviews/{review['review_uuid']}/close",
        session=dpo,
        template=REVIEW + "/close",
        json={"note": "Done."},
    )
    assert closed.json()["status"] == "closed"
    cert = REVIEW + "/certificate"
    got = await call(
        http,
        "GET",
        f"/retention/reviews/{review['review_uuid']}/certificate",
        session=dpo,
        template=cert,
        params={"format": "pdf"},
    )
    assert got.content.startswith(b"%PDF")
    assert "certificate.pdf" in got.headers["content-disposition"]
    await call(
        http,
        "GET",
        f"/retention/reviews/{review['review_uuid']}/certificate",
        session=world.dco_admin,
        template=cert,
        expect=403,
    )

    # The validity review of the same people: its owner action set aside, then closed.
    validity = await call(
        http, "GET", "/retention/reviews", session=dpo, params={"kind": "validity"}
    )
    v = next(r for r in validity.json() if r["project_uuid"] == world.project_uuid)
    vd = await call(
        http, "GET", f"/retention/reviews/{v['review_uuid']}", session=dpo, template=REVIEW
    )
    for a in vd.json()["actions_list"]:
        await call(
            http,
            "POST",
            f"/retention/reviews/{v['review_uuid']}/actions/{a['action_uuid']}/not-needed",
            session=dpo,
            template=ACTION + "/not-needed",
        )
    await call(
        http,
        "POST",
        f"/retention/reviews/{v['review_uuid']}/close",
        session=dpo,
        template=REVIEW + "/close",
        json={},
    )
