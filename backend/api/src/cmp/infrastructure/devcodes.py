"""One-time codes kept for the development popup, and read back for it.

When `DEV_SHOW_CODES` is on, each message the console transports write is
also kept here, for five minutes, if it carries a code. The portals poll
`GET /dev/codes` and show it in a popup, so a local sign-in can be finished
on the screen that asked for it - including a phone or a second machine
opening the portal by IP, where `var/outbox.log` is out of reach.

Guarded three times over, because a code on the screen that asks for it
proves nothing about who holds the phone:

* the setting is refused at startup outside `local` and `test`;
* only the console transports record, and they already refuse to deliver
  outside `local` and `test`;
* the route is not mounted unless the setting is on.

Nothing here is ever used by a real delivery.

**Only the screen that asked sees a code.** Every open portal and console
polls, and a list shared by all of them showed each code in every open window
on every machine. So each browser tab sends a random id of its own
(`X-CMP-Dev-Client`) with its requests; the request that causes a code
carries it to the worker in the task headers, the code is kept with it, and
`GET /dev/codes` answers a tab with its own codes only. A tab that sends no id
sees none.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.devcodes")

KEY = "dev:codes"

#: The header a browser tab identifies itself with, and the context key that
#: carries it from the request to the worker that writes the message.
CLIENT_HEADER = "X-CMP-Dev-Client"
CONTEXT_KEY = "dev_client"
_CLIENT = re.compile(r"[A-Za-z0-9_-]{8,64}")
KEEP = 20
TTL_S = 300

#: The shapes the default templates put a code in: on its own line, after
#: "code is", or at the start of an SMS or subject line ("COMPASS: 123456 is
#: your…"). A reference such as RR-2026-000042 is not six digits on its own.
_CODE = re.compile(
    r"code is (\d{6})|^\s*(\d{6})\s*$|^(?:[^:\n]{1,60}: )?(\d{6}) (?:is your|confirms|signs)",
    re.M,
)


def enabled() -> bool:
    return settings.dev_show_codes and settings.environment in ("local", "test")


def client_id(value: str | None) -> str | None:
    """The tab id from a header, if it is one; anything else is no id."""
    if not value or not _CLIENT.fullmatch(value):
        return None
    return value


def _redis() -> Any:
    from cmp.infrastructure.messaging import _redis as messaging_redis

    return messaging_redis()


def record(*, channel: str, to: str, text: str) -> None:
    """Keep the code in `text`, if it has one. Never raises: a popup that
    could not be fed must not stop a message that could be sent."""
    if not enabled():
        return
    match = _CODE.search(text)
    if not match:
        return
    code = next(g for g in match.groups() if g)
    from cmp.core.context import current_context

    entry = {
        "to": to,
        "channel": channel,
        "code": code,
        "at": time.time(),
        # The tab whose request caused this message; see the module docstring.
        "client": current_context().extra.get(CONTEXT_KEY),
    }
    try:
        r = _redis()
        pipe = r.pipeline()
        pipe.lpush(KEY, json.dumps(entry))
        pipe.ltrim(KEY, 0, KEEP - 1)
        pipe.expire(KEY, TTL_S)
        pipe.execute()
    except Exception as exc:  # the popup is a convenience; the message is not
        log.warning("devcodes.not_recorded", error=str(exc))


async def recent(redis: Any, *, client: str | None, within_s: int = TTL_S) -> list[dict[str, Any]]:
    """This tab's codes from the last `within_s` seconds, newest first.

    Without a tab id there is nothing to match, so nothing is returned: a code
    is shown to the screen that asked for it or to none.
    """
    if not client:
        return []
    raw = await redis.lrange(KEY, 0, KEEP - 1)
    cutoff = time.time() - within_s
    out: list[dict[str, Any]] = []
    for item in raw:
        entry = json.loads(item)
        if entry.get("at", 0) >= cutoff and entry.get("client") == client:
            out.append({k: v for k, v in entry.items() if k != "client"})
    return out
