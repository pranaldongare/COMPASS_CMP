"""A failed request on a capability path does not log the capability.

The access log scrubbed `/c/{token}` from the start. The failure log did not:
the error handlers logged `request.url.path` as it came, so the request most
likely to fail - a stranger's, on a link - was the one that wrote the token
to disk. Every handler now goes through `safe_path`, and this pins it.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import Request

from cmp.api.errors import handlers
from cmp.api.middleware.request_context import safe_path
from cmp.core.errors import NotFound, RateLimited


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def _record(self, event: str, **fields: Any) -> None:
        self.events.append((event, fields))

    info = warning = error = _record


def _request(path: str, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
        }
    )


class TestSafePath:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/c/abcdef0123456789/notice", "/c/[token]/notice"),
            ("/c/abcdef0123456789", "/c/[token]"),
            ("/rights/nominations/abcdef0123456789", "/rights/nominations/[token]"),
            ("/rights/nominations/abcdef0123456789/accept", "/rights/nominations/[token]/accept"),
            (
                "/projects/1c1b7b8e-0000-4000-8000-000000000000",
                "/projects/1c1b7b8e-0000-4000-8000-000000000000",
            ),
        ],
    )
    def test_tokens_are_replaced_and_everything_else_kept(self, path: str, expected: str) -> None:
        assert safe_path(path) == expected


class TestHandlersScrub:
    @pytest.fixture
    def recorder(self, monkeypatch: pytest.MonkeyPatch) -> _Recorder:
        rec = _Recorder()
        monkeypatch.setattr(handlers, "log", rec)
        return rec

    async def test_a_domain_error_on_a_consent_link_logs_no_token(
        self, recorder: _Recorder
    ) -> None:
        await handlers.cmp_error_handler(
            _request("/c/SECRETTOKEN123/consent", "POST"), NotFound("Link")
        )
        assert recorder.events, "the failure must be logged"
        event, fields = recorder.events[-1]
        assert event == "request.failed"
        assert fields["endpoint"] == "/c/[token]/consent"
        assert "SECRETTOKEN123" not in repr(recorder.events)

    async def test_a_rate_limit_on_a_nomination_link_logs_no_token(
        self, recorder: _Recorder
    ) -> None:
        await handlers.cmp_error_handler(
            _request("/rights/nominations/SECRETTOKEN123/code", "POST"),
            RateLimited("slow down", retry_after_s=5),
        )
        _, fields = recorder.events[-1]
        assert fields["endpoint"] == "/rights/nominations/[token]/code"

    async def test_an_unhandled_exception_logs_no_token(self, recorder: _Recorder) -> None:
        await handlers.unhandled_handler(_request("/c/SECRETTOKEN123"), RuntimeError("boom"))
        event, fields = recorder.events[-1]
        assert event == "request.unhandled"
        assert fields["endpoint"] == "/c/[token]"
        assert "SECRETTOKEN123" not in repr(recorder.events)
