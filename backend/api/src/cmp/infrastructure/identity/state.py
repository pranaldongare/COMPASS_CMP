"""What an SSO sign-in carries between its legs, held by the server (ADR 0034).

Two records, both in Redis and both short-lived:

* **The sign-in** (`sso:state:<state>`, ten minutes): the nonce, the PKCE
  verifier and the link it was started on, written by `/c/{token}/sso/start`
  and taken - read and deleted in one step - by the callback. A callback
  whose state is unknown or already used has nothing to continue.
* **The pending employee** (`sso:pending:<id>`, fifteen minutes): an
  assertion that matched no account, held until the person confirms a
  mobile, because an account of a data principal cannot exist without one
  (`trg_subject_needs_mobile`, open point F-7). Sealed, because it carries
  a name, an email and an employee ID; its id travels in an httpOnly cookie,
  never in a URL.
"""

from __future__ import annotations

import json
import secrets
from typing import Any, Final

from cmp.core.security import seal_token, unseal_token
from cmp.db.redis import get_redis, key

K_SSO: Final = "sso"
STATE_TTL_S: Final = 600
PENDING_TTL_S: Final = 900
#: The cookie the pending employee's id travels in, on the portal's origin.
PENDING_COOKIE: Final = "cmp_sso_pending"


async def begin(*, link_token: str, nonce: str, verifier: str) -> str:
    """A new sign-in's state, which the browser carries to the provider and back."""
    state = secrets.token_urlsafe(32)
    payload = json.dumps({"link_token": link_token, "nonce": nonce, "verifier": verifier})
    await get_redis().set(
        key(K_SSO, "state", state),
        seal_token(payload).hex(),
        ex=STATE_TTL_S,
    )
    return state


async def take(state: str) -> dict[str, Any] | None:
    """The sign-in for `state`, once: a second callback with it finds nothing."""
    raw = await get_redis().getdel(key(K_SSO, "state", state))
    return _open(raw)


async def peek(state: str) -> dict[str, Any] | None:
    """The sign-in for `state`, left for the callback: the stand-in provider's
    page reads it while the person is still there (`mock`)."""
    raw = await get_redis().get(key(K_SSO, "state", state))
    return _open(raw)


async def hold(claims: dict[str, Any], *, link_token: str) -> str:
    """An assertion that matched nobody, kept until a mobile is confirmed."""
    pending = secrets.token_urlsafe(32)
    payload = json.dumps({"claims": claims, "link_token": link_token})
    await get_redis().set(
        key(K_SSO, "pending", pending), seal_token(payload).hex(), ex=PENDING_TTL_S
    )
    return pending


async def pending(pending_id: str) -> dict[str, Any] | None:
    raw = await get_redis().get(key(K_SSO, "pending", pending_id))
    return _open(raw)


async def release(pending_id: str) -> None:
    await get_redis().delete(key(K_SSO, "pending", pending_id))


def _open(raw: Any) -> dict[str, Any] | None:
    if not raw:
        return None
    text = raw.decode() if isinstance(raw, bytes) else str(raw)
    try:
        opened = unseal_token(bytes.fromhex(text))
    except ValueError:
        return None
    if not opened:
        return None
    value = json.loads(opened)
    return value if isinstance(value, dict) else None
