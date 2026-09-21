"""The office replaces the words of a message, and the worker sends them."""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.messages import Message
from cmp.db.repositories import audit as audit_repo
from cmp.domain.messaging import service
from cmp.infrastructure import messaging

pytestmark = pytest.mark.integration


class TestEditing:
    async def test_the_catalogue_lists_every_junction_as_default(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        rows = await service.catalogue(conn)
        assert {r["key"] for r in rows} == {m.value for m in Message}
        for row in rows:
            for ch in row["channels"]:
                assert ch["customised"] is False
                assert ch["body"] == ch["default_body"]

    async def test_saving_replaces_the_words_and_is_audited(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        view = await service.save(
            conn,
            key="login_code",
            channel="sms",
            subject=None,
            body="Hi from {organisation}: {code} signs you in, {minutes} min.",
            actor_id=dpo,
        )
        sms = next(c for c in view["channels"] if c["channel"] == "sms")
        assert sms["customised"] is True
        assert sms["body"].startswith("Hi from")
        assert sms["default_body"] != sms["body"]
        assert sms["updated_by_name"]

        events = await audit_repo.by_actor(conn, dpo, limit=5)
        assert any(e["event_type"] == "message_template.updated" for e in events)

    async def test_reset_returns_to_the_default(self, conn: Any, seeded: dict[str, Any]) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        await service.save(
            conn,
            key="mfa_code",
            channel="email",
            subject="Code {code}",
            body="{code}",
            actor_id=dpo,
        )
        view = await service.reset(conn, key="mfa_code", channel="email", actor_id=dpo)
        email = view["channels"][0]
        assert email["customised"] is False and email["body"] == email["default_body"]

    async def test_an_unknown_variable_is_refused_with_the_allowed_ones_named(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationFailed) as exc:
            await service.save(
                conn,
                key="mfa_code",
                channel="email",
                subject="Hi {full_name}",
                body="{code}",
                actor_id=seeded["users"]["dpo"]["id"],
            )
        assert "{full_name}" in str(exc.value.message) and "{code}" in str(exc.value.message)

    async def test_an_unknown_message_or_channel_is_not_found(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        with pytest.raises(NotFound):
            await service.one(conn, "no_such_message")
        with pytest.raises(NotFound):
            await service.save(
                conn, key="mfa_code", channel="sms", subject=None, body="x", actor_id=1
            )

    def test_preview_renders_with_samples(self) -> None:
        out = service.preview("mfa_code", "email", "{code} for {organisation}", "Use {code}")
        assert out["subject"] and "482913" in out["subject"]
        assert out["body"] == "Use 482913"


class TestWorkerSide:
    def test_the_stored_words_are_what_the_worker_renders(self) -> None:
        overrides = {"login_code:sms": {"subject": None, "body": "Custom {code} ({minutes}m)"}}
        subject, body = messaging.render(
            Message.LOGIN_CODE, "sms", {"code": "111222", "minutes": 10}, overrides=overrides
        )
        assert subject is None and body == "Custom 111222 (10m)"

    def test_without_stored_words_the_default_renders(self) -> None:
        subject, body = messaging.render(
            Message.MFA_CODE, "email", {"code": "111222", "minutes": 5}, overrides={}
        )
        assert subject and "111222" in subject
        assert "111222" in body and "5 minutes" in body

    def test_loading_overrides_survives_an_empty_table_and_fills_the_mirror(
        self, redis_conn: Any
    ) -> None:
        overrides = messaging.load_overrides()
        assert isinstance(overrides, dict)
        # A second read comes from the mirror and agrees.
        assert messaging.load_overrides() == overrides

    def test_deliver_refuses_a_channel_the_message_does_not_use(self) -> None:
        with pytest.raises(ValueError):
            messaging.deliver(Message.MFA_CODE, to="+919000000001", code="1", minutes=5)
