"""The task that mails a report records an outcome whatever happens (ADR 0037).

Unlike a notice's, its job opens the words and draws the PDF, so an outage can
come before the mail as well as during it: both are retried, and what no retry
will mend is recorded at once. A report no one can be told about is a failed
line on the Reports tab, never a mail that was silently not sent, or sent to an
address that has been taken off the list.

Two tasks can hold one delivery, so each claims the address before it sends,
and a mail that has gone is never sent again to get it on the record.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from celery.exceptions import Retry
from redis.exceptions import ConnectionError as RedisDown

from cmp.domain.breach import notices
from cmp.domain.breach import reports as report_domain
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.tasks.app import celery_app
from cmp.tasks.notifications import breach
from cmp.tasks.notifications import breach_reports as task

JOB = {
    "removed": False,
    "email": "SE::sealed-address",
    "kind": "org_board",
    "reference": "BR-2026-0001",
    "report_title": "Report to the organisation's board",
    "report_text": "What happened\nA list went astray",
    "pdf": b"%PDF-1.7",
    "file_name": "BR-2026-0001-org_board-v1.pdf",
}


KEY = "mutex:breach_report:1:hash"


class Claims:
    """The four commands a claim uses, as Redis answers them."""

    def __init__(self) -> None:
        self.held: dict[str, int] = {}
        self.owners: dict[str, str] = {}

    def set(self, key: str, owner: str, *, nx: bool, ex: int) -> bool | None:
        assert nx, "a claim that overwrites another is no claim"
        assert owner, "a claim that names nobody can never be taken back"
        if key in self.held:
            return None
        self.held[key] = ex
        self.owners[key] = owner
        return True

    def get(self, key: str) -> str | None:
        return self.owners.get(key) if key in self.held else None

    def expire(self, key: str, ttl: int) -> None:
        self.held[key] = ttl

    def delete(self, key: str) -> None:
        self.held.pop(key, None)


@pytest.fixture(autouse=True)
def claims(monkeypatch: pytest.MonkeyPatch) -> Claims:
    """The real claiming, on a Redis of a dict; only the key's read is stood in for."""
    held = Claims()
    monkeypatch.setattr(breach, "_redis", lambda: held)
    monkeypatch.setattr(
        task, "_claim", lambda uuid, owner: KEY if task.take_claim(KEY, owner) else None
    )
    return held


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(task, "_job", lambda uuid: dict(JOB))
    monkeypatch.setattr(task, "_record", lambda uuid, status, detail: out.append((status, detail)))
    return out


def _run(retries: int = 0, task_id: str = "this-task") -> Any:
    task.send_breach_report.push_request(id=task_id, retries=retries)
    try:
        return task.send_breach_report.run("d-uuid")
    finally:
        task.send_breach_report.pop_request()


def _down(*_: Any, **__: Any) -> None:
    raise DkmsUnavailable("key service down")


def test_a_delivered_report_is_recorded_delivered(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(task, "deliver", lambda key, to, **v: sent.append({"to": to, **v}))
    assert _run() == {"delivered": True}
    assert recorded == [("delivered", {})]
    assert sent[0]["to"] == "SE::sealed-address", "the sealed address is opened by deliver()"


@pytest.mark.parametrize("stage", ["_job", "deliver"], ids=["reading it", "sending it"])
def test_an_outage_is_retried_and_recorded_only_when_the_retries_are_spent(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any], stage: str
) -> None:
    monkeypatch.setattr(task, stage, _down)
    monkeypatch.setattr(task.send_breach_report, "retry", lambda **kw: Retry(str(kw["exc"])))
    with pytest.raises(Retry):
        _run(retries=0)
    assert recorded == [], "not yet: it will be tried again"

    assert _run(retries=task.MAX_RETRIES) == {"failed": "DkmsUnavailable"}
    assert recorded == [("failed", {"error": "DkmsUnavailable", "attempts": task.MAX_RETRIES + 1})]


@pytest.mark.parametrize("stage", ["_job", "deliver"], ids=["reading it", "sending it"])
def test_what_no_retry_mends_is_recorded_at_once(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any], stage: str
) -> None:
    def broken(*_: Any, **__: Any) -> None:
        raise ValueError("a PDF that would not draw")

    monkeypatch.setattr(task, stage, broken)
    assert _run() == {"failed": "ValueError"}
    assert recorded == [("failed", {"error": "ValueError", "attempts": 1})]


def test_an_address_taken_off_the_list_is_recorded_and_not_mailed(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    monkeypatch.setattr(task, "_job", lambda uuid: {"removed": True})
    monkeypatch.setattr(task, "deliver", lambda *a, **k: pytest.fail("mailed a removed address"))
    assert _run() == {"failed": "RecipientRemoved"}
    assert recorded == [("failed", {"error": "RecipientRemoved", "attempts": 1})]


def test_nothing_to_do_is_nothing_done(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(task, "_job", lambda uuid: None)
    monkeypatch.setattr(task, "_record", lambda *a: pytest.fail("recorded a skipped job"))
    assert _run() == {"skipped": True}


def test_the_reports_words_go_marked_as_quoted(
    monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
) -> None:
    from cmp.infrastructure.email.layout import quoted

    sent: list[dict[str, Any]] = []
    monkeypatch.setattr(task, "deliver", lambda key, to, **v: sent.append(v))
    _run()
    assert sent[0]["report_text"] == quoted(str(JOB["report_text"]))


class TestOneSendAtATime:
    def test_a_task_that_loses_sends_nothing_and_writes_no_failure(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any], claims: Claims
    ) -> None:
        assert task.take_claim(KEY, "another-task")
        monkeypatch.setattr(task, "deliver", lambda *a, **k: pytest.fail("mailed twice"))
        assert _run() == {"skipped": True}
        assert recorded == []
        assert KEY in claims.held, "it is the winner's to give up"

    def test_a_task_whose_worker_was_killed_comes_back_and_sends(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
    ) -> None:
        """Its message returns under the same id, to the claim it died holding.
        Standing down there would leave nothing alive to send the mail."""
        assert task.take_claim(KEY, "this-task")
        sent: list[str] = []
        monkeypatch.setattr(task, "deliver", lambda key, to, **_: sent.append(to))
        assert _run(task_id="this-task") == {"delivered": True}
        assert len(sent) == 1

    def test_of_two_tasks_at_once_one_sends(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any]
    ) -> None:
        sent: list[str] = []

        def slow(key: Any, to: str, **_: Any) -> None:
            sent.append(to)
            # The second task, arriving while the first is at the mail server.
            assert _run(task_id="another-task") == {"skipped": True}

        monkeypatch.setattr(task, "deliver", slow)
        assert _run() == {"delivered": True}
        assert len(sent) == 1
        assert recorded == [("delivered", {})]

    @pytest.mark.parametrize("retries", [0, task.MAX_RETRIES], ids=["to retry", "retries spent"])
    def test_a_failure_leaves_the_claim_free_for_the_next_try(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any], claims: Claims, retries: int
    ) -> None:
        monkeypatch.setattr(task, "deliver", _down)
        monkeypatch.setattr(task.send_breach_report, "retry", lambda **kw: Retry(str(kw["exc"])))
        with contextlib.suppress(Retry):
            _run(retries=retries)
        assert claims.held == {}

    def test_what_no_retry_mends_leaves_the_claim_free_too(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any], claims: Claims
    ) -> None:
        def broken(*_: Any, **__: Any) -> None:
            raise ValueError("a mail the server would not take")

        monkeypatch.setattr(task, "deliver", broken)
        assert _run() == {"failed": "ValueError"}
        assert claims.held == {}, "the next attempt must be able to send"

    def test_the_retry_sends(self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any]) -> None:
        tries: list[str] = []

        def once(key: Any, to: str, **_: Any) -> None:
            tries.append(to)
            if len(tries) == 1:
                raise DkmsUnavailable("key service down")

        monkeypatch.setattr(task, "deliver", once)
        monkeypatch.setattr(task.send_breach_report, "retry", lambda **kw: Retry(str(kw["exc"])))
        with pytest.raises(Retry):
            _run()
        assert _run(retries=1) == {"delivered": True}
        assert len(tries) == 2

    def test_a_claim_it_could_not_ask_for_is_a_retry_and_no_send(
        self, monkeypatch: pytest.MonkeyPatch, recorded: list[Any], claims: Claims
    ) -> None:
        def down(*_: Any, **__: Any) -> None:
            raise RedisDown("no redis")

        monkeypatch.setattr(claims, "set", down)
        monkeypatch.setattr(task, "deliver", lambda *a, **k: pytest.fail("sent with no claim"))
        monkeypatch.setattr(task.send_breach_report, "retry", lambda **kw: Retry(str(kw["exc"])))
        with pytest.raises(Retry):
            _run()
        assert recorded == []
        assert _run(retries=task.MAX_RETRIES) == {"failed": "ConnectionError"}

    def test_a_claim_outlasts_the_longest_task_and_not_the_wait_for_one(self) -> None:
        limit = celery_app.conf.task_time_limit
        assert limit < breach.CLAIM_TTL_S
        for wait in (report_domain.STALE_AFTER, notices.STALE_AFTER):
            assert wait.total_seconds() > breach.CLAIM_TTL_S, (
                "held up reads after this, when a task that started on time has let go"
            )


class TestAMailThatHasGone:
    @pytest.fixture
    def sent(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        out: list[str] = []
        monkeypatch.setattr(task, "deliver", lambda key, to, **_: out.append(to))
        return out

    @pytest.fixture
    def left(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
        """What was left to the task that only records."""
        out: list[tuple[Any, ...]] = []
        monkeypatch.setattr(task, "dispatch_optional", lambda _task, *args: out.append(args))
        return out

    @staticmethod
    def _unrecordable(monkeypatch: pytest.MonkeyPatch) -> None:
        def stuck(*_: Any) -> None:
            raise OSError("the breach's row is held")

        monkeypatch.setattr(task, "_record", stuck)

    def test_a_recording_that_fails_is_retried_by_itself(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sent: list[str],
        left: list[tuple[Any, ...]],
        claims: Claims,
    ) -> None:
        monkeypatch.setattr(task, "_job", lambda uuid: dict(JOB))
        self._unrecordable(monkeypatch)
        monkeypatch.setattr(
            task.send_breach_report, "retry", lambda **_: pytest.fail("the mail went again")
        )
        assert _run() == {"delivered": True}
        assert len(sent) == 1
        assert left == [("d-uuid", "delivered", {})]
        assert claims.held == {KEY: task.CLAIM_KEPT_S}, "Try again must meet this claim"

    def test_a_delivered_mail_keeps_its_claim_until_it_runs_out(
        self, sent: list[str], recorded: list[Any], claims: Claims
    ) -> None:
        """A task that read before the outcome was recorded still stands down."""
        _run()
        assert KEY in claims.held

    @pytest.mark.parametrize("exception", [OSError, DkmsUnavailable, ValueError])
    def test_only_the_recording_is_tried_again(
        self, monkeypatch: pytest.MonkeyPatch, exception: type[Exception]
    ) -> None:
        def stuck(*_: Any) -> None:
            raise exception("not now")

        monkeypatch.setattr(task, "_record", stuck)
        monkeypatch.setattr(task, "deliver", lambda *a, **k: pytest.fail("the mail went again"))
        monkeypatch.setattr(
            task.record_breach_report_result, "retry", lambda **kw: Retry(str(kw["exc"]))
        )
        with pytest.raises(Retry):
            task.record_breach_report_result.run("d-uuid", "delivered", {})

    def test_it_is_recorded_when_it_can_be(self, recorded: list[Any]) -> None:
        assert task.record_breach_report_result.run("d-uuid", "delivered", {}) == {
            "recorded": "delivered"
        }
        assert recorded == [("delivered", {})]

    def test_the_recording_gives_up_before_the_claim_does(self) -> None:
        assert task.record_breach_report_result.max_retries == task.RECORD_RETRIES
        waited = sum(min(300, 5 * 2**n) for n in range(task.RECORD_RETRIES))
        assert waited < task.CLAIM_KEPT_S

    def test_a_failure_that_cannot_be_recorded_is_left_the_same_way(
        self, monkeypatch: pytest.MonkeyPatch, left: list[tuple[Any, ...]]
    ) -> None:
        def broken(*_: Any, **__: Any) -> None:
            raise ValueError("a mail the server would not take")

        monkeypatch.setattr(task, "_job", lambda uuid: dict(JOB))
        monkeypatch.setattr(task, "deliver", broken)
        self._unrecordable(monkeypatch)
        assert _run() == {"failed": "ValueError"}
        assert left == [("d-uuid", "failed", {"error": "ValueError", "attempts": 1})]
