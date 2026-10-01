"""An SMS gateway's passing trouble is retried; a refusal is not (review SCALE-2).

Every message task retries `ConnectionError`, `TimeoutError`, `OSError` and a
key service that blinked. The HTTP SMS adapter raised httpx's own exceptions
for a timeout or a dropped connection, and `RuntimeError` for any non-2xx -
none of them in that list, so a sign-in code to a mobile was lost the first
time the gateway hiccuped. The adapter now says which kind of failure it was:
a timeout, a lost connection, 429 or 5xx are worth another try; any other
refusal - a bad number, a bad token - is not, and retrying it would only send
the same wrong request five more times.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cmp.infrastructure.sms import transport
from cmp.tasks.authentication.otp import RETRY_KW as CODE_RETRY
from cmp.tasks.notifications.breach import RETRYABLE as BREACH_RETRY

GATEWAY = transport.HttpSmsTransport(
    url="https://sms.example.org/send", token="t", sender="CMP", timeout_s=1
)


def _answering(status: int) -> Any:
    def post(*_: Any, **__: Any) -> httpx.Response:
        return httpx.Response(status, request=httpx.Request("POST", "https://sms.example.org"))

    return post


def _raising(exc: Exception) -> Any:
    def post(*_: Any, **__: Any) -> httpx.Response:
        raise exc

    return post


def _retried(exc: BaseException) -> bool:
    return isinstance(exc, tuple(CODE_RETRY["autoretry_for"])) and isinstance(exc, BREACH_RETRY)


@pytest.mark.parametrize(
    "post",
    [
        _raising(httpx.ConnectTimeout("slow")),
        _raising(httpx.ReadTimeout("slow")),
        _raising(httpx.ConnectError("refused")),
        _answering(429),
        _answering(500),
        _answering(503),
    ],
    ids=["connect-timeout", "read-timeout", "connect-error", "429", "500", "503"],
)
def test_passing_trouble_is_retried(monkeypatch: pytest.MonkeyPatch, post: Any) -> None:
    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(Exception) as raised:
        GATEWAY.send(to="+919876500001", body="482913")
    assert _retried(raised.value), type(raised.value)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_a_refusal_is_not_retried(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    monkeypatch.setattr(httpx, "post", _answering(status))
    with pytest.raises(Exception) as raised:
        GATEWAY.send(to="+919876500001", body="482913")
    assert not _retried(raised.value), status


def test_a_success_is_still_a_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", _answering(202))
    assert GATEWAY.send(to="+919876500001", body="482913")["delivered"] is True
