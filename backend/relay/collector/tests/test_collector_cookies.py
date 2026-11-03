"""The collector keeps no cookie between requests.

One HTTP client serves every visitor. httpx's default cookie jar stores each
`Set-Cookie` and adds it to the next request that carries none, which signed
anonymous visitors in as whoever signed in last. `no_cookie_jar` refuses to
store or send anything; `httpx.Client` must be given the stdlib jar itself,
because it copies an `httpx.Cookies` into a fresh jar and loses the policy.
"""

from __future__ import annotations

import httpx
import pytest

from cmp_relay.collector import no_cookie_jar

SET_COOKIE = "cmp_session=visitor-a; Path=/; HttpOnly; SameSite=lax"


def _client(seen: list[str | None], jar: object) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("cookie"))
        return httpx.Response(200, headers=[("set-cookie", SET_COOKIE)], json={})

    return httpx.Client(transport=httpx.MockTransport(handler), cookies=jar)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "origin",
    ["http://127.0.0.1:8000", "http://api.internal.example.org", "https://api.example.org"],
)
def test_a_cookie_one_visitor_was_given_is_never_sent_for_another(origin: str) -> None:
    seen: list[str | None] = []
    client = _client(seen, no_cookie_jar())
    client.post(f"{origin}/auth/otp/verify")
    client.get(f"{origin}/auth/me")
    client.get(f"{origin}/auth/me", headers={"cookie": "cmp_session=visitor-b"})
    assert seen == [None, None, "cmp_session=visitor-b"]
    assert list(client.cookies.jar) == []


def test_the_default_jar_would_have_leaked() -> None:
    """The failure this guards against, shown on the default client."""
    seen: list[str | None] = []
    client = _client(seen, None)
    client.post("http://127.0.0.1:8000/auth/otp/verify")
    client.get("http://127.0.0.1:8000/auth/me")
    assert seen == [None, "cmp_session=visitor-a"]


def test_wrapping_the_jar_in_httpx_cookies_loses_the_policy() -> None:
    """Why `no_cookie_jar` returns the stdlib jar, not `httpx.Cookies`."""
    seen: list[str | None] = []
    client = _client(seen, httpx.Cookies(no_cookie_jar()))
    client.post("http://127.0.0.1:8000/auth/otp/verify")
    client.get("http://127.0.0.1:8000/auth/me")
    assert seen == [None, "cmp_session=visitor-a"]
