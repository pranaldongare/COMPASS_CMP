"""The breach notice task records an outcome whatever happens (S3-03).

Rule 7(2)(b)(vi) asks for an account of the notices. A message dropped
silently would make that account wrong, so the task records `delivered`,
retries what a retry could mend, and records `failed` - once the retries are
spent, or at once for what no retry will mend.
"""

from __future__ import annotations

from typing import Any

import pytest
from celery.exceptions import Retry

from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.tasks.notifications import breach

JOB = {
    "channel": "sms",
    "email": None,
    "mobile": "SE::sealed-mobile",
    "reference": "BR-2026-0001",
    "what_happened": "a",
    "consequences": "b",
    "measures": "c",
    "protective_steps": "d",
    "contact": "e",
}


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(breach, "_job", lambda uuid: dict(JOB))
    monkeypatch.setattr(
        breach, "_record", lambda uuid, status, detail: out.append((status, detail))
    )
    return out


def _run(retries: int = 0) -> Any:
    breach.send_breach_notice.push_request(retries=retries)
    try:
        return breach.send_breach_notice.run("d-uuid")
    finally:
        breach.send_breach_notice.pop_request()


def test_a_delivered_notice_is_recorded_delivered(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(breach, "deliver", lambda key, to, **v: sent.append({"to": to, **v}))
    assert _run() == {"delivered": True}
    assert recorded == [("delivered", {})]
    assert sent[0]["to"] == "SE::sealed-mobile", "the sealed contact is opened by deliver()"
    assert sent[0]["breach_reference"] == "BR-2026-0001"


def test_an_outage_is_retried_and_recorded_only_when_the_retries_are_spent(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    def down(*_: Any, **__: Any) -> None:
        raise DkmsUnavailable("key service down")

    monkeypatch.setattr(breach, "deliver", down)
    # Celery's retry() re-queues the call; what matters here is that the task
    # asks for one, and records nothing while it does.
    monkeypatch.setattr(breach.send_breach_notice, "retry", lambda **kw: Retry(str(kw["exc"])))
    with pytest.raises(Retry):
        _run(retries=0)
    assert recorded == [], "not yet: it will be tried again"

    assert _run(retries=breach.MAX_RETRIES) == {"failed": "DkmsUnavailable"}
    assert recorded == [
        ("failed", {"error": "DkmsUnavailable", "attempts": breach.MAX_RETRIES + 1})
    ]


def test_what_no_retry_mends_is_recorded_at_once(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    def broken(*_: Any, **__: Any) -> None:
        raise ValueError("not a contact")

    monkeypatch.setattr(breach, "deliver", broken)
    assert _run() == {"failed": "ValueError"}
    assert recorded == [("failed", {"error": "ValueError", "attempts": 1})]


def test_a_contact_gone_since_the_send_is_a_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    monkeypatch.setattr(breach, "_job", lambda uuid: {**JOB, "mobile": None})
    assert _run() == {"failed": "NoContact"}
    assert recorded[0][0] == "failed"


def test_nothing_to_do_is_nothing_done(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(breach, "_job", lambda uuid: None)
    monkeypatch.setattr(breach, "_record", lambda *a: pytest.fail("recorded a skipped job"))
    assert _run() == {"skipped": True}
