"""`GET /dev/codes` - the development popup's one-time codes.

Mounted only when `DEV_SHOW_CODES` is on, which the settings refuse outside
`local` and `test`. No session: the popup is needed before anybody has one.
See `cmp.infrastructure.devcodes` for why that is acceptable here and
nowhere else.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response

from cmp.db.redis import get_redis
from cmp.infrastructure import devcodes

router = APIRouter(tags=["development"], include_in_schema=False)


@router.get("/dev/codes", summary="Codes the console transports wrote, for the dev popup")
async def dev_codes(response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    return {"items": await devcodes.recent(get_redis())}
