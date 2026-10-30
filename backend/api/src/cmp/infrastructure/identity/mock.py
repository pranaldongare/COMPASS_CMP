"""A stand-in for the organisation's identity provider, for local development.

With `SSO_MOCK` on (2026-10-30), an `sso` link signs in here instead of at a
real provider, so the employee path can be followed on a machine that has
none. It answers the four calls `oidc` answers, the way `oidc` answers them,
and `cmp.auth.authentication.sso` takes it in `oidc`'s place - the start,
the callback, the matching on the employee ID and the mobile gate run
unchanged (ADR 0034: a second implementation behind the same interface).

Its sign-in page is the portal's `/sso-mock`: any email address, then a code
sent to it (`cmp.auth.authentication.sso_mock`). What it asserts is made from
that address alone - the address, a name from its local part, and an
employee ID derived from it, `MOCK-` and eight hex digits - so the same
address is the same employee every time.

The settings refuse `SSO_MOCK` outside local and test: it signs anybody in
as anybody who can read a code sent to an address they typed.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from typing import Final
from urllib.parse import urlencode

from cmp.core.config import settings
from cmp.core.security import seal_token, unseal_token
from cmp.db.redis import get_redis, key
from cmp.infrastructure.identity.oidc import AssertionInvalid, Claims
from cmp.infrastructure.identity.state import K_SSO

#: How long the code the page hands the callback stays good.
ASSERTION_TTL_S: Final = 300

_WORD = re.compile(r"[._+\-]+")


def configured() -> bool:
    return settings.sso_mock


def claims_for(email: str) -> Claims:
    """What the stand-in asserts for an address."""
    address = email.strip().lower()
    employee_id = "MOCK-" + hashlib.sha256(address.encode()).hexdigest()[:8].upper()
    words = [w for w in _WORD.split(address.partition("@")[0]) if w]
    name = " ".join(w.capitalize() for w in words) or "Employee"
    return Claims(subject=employee_id, employee_id=employee_id, email=address, name=name)


async def authorize_url(*, state: str, nonce: str, challenge: str) -> str:
    """The portal's stand-in sign-in page, carrying the state as a provider would."""
    return f"{settings.public_base_url.rstrip('/')}/sso-mock?{urlencode({'state': state})}"


async def signed_in(*, state: str, nonce: str, email: str) -> str:
    """The person proved the address: where to send the browser - the
    callback, with a code it exchanges for this assertion, once."""
    code = secrets.token_urlsafe(32)
    payload = json.dumps({"nonce": nonce, "email": email})
    await get_redis().set(key(K_SSO, "mock", code), seal_token(payload).hex(), ex=ASSERTION_TTL_S)
    return _callback({"state": state, "code": code})


def cancelled(*, state: str) -> str:
    """The person turned back: the callback, told so as a provider tells it."""
    return _callback({"state": state, "error": "access_denied"})


def _callback(query: dict[str, str]) -> str:
    target = settings.sso_redirect_url
    return f"{target}{'&' if '?' in target else '?'}{urlencode(query)}"


async def exchange(*, code: str, verifier: str) -> str:
    raw = await get_redis().getdel(key(K_SSO, "mock", code))
    if not raw:
        raise AssertionInvalid("unknown or used code")
    text = raw.decode() if isinstance(raw, bytes) else str(raw)
    try:
        opened = unseal_token(bytes.fromhex(text))
    except ValueError as exc:
        raise AssertionInvalid("unreadable code") from exc
    if not opened:
        raise AssertionInvalid("unreadable code")
    return opened


async def validate(token: str, *, nonce: str) -> Claims:
    try:
        held = json.loads(token)
    except ValueError as exc:
        raise AssertionInvalid("unreadable assertion") from exc
    if not secrets.compare_digest(str(held.get("nonce") or ""), nonce):
        raise AssertionInvalid("nonce does not match")
    return claims_for(str(held["email"]))
