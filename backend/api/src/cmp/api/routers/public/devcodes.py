"""`GET /dev/codes` - the development popup's one-time codes - and
`GET /dev/seed-accounts`, the seed logins still on the seed password.

Mounted only when `DEV_SHOW_CODES` is on, which the settings refuse outside
`local` and `test`. No session: the popup is needed before anybody has one.
See `cmp.infrastructure.devcodes` for why that is acceptable here and
nowhere else.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response

from cmp.core.config import settings
from cmp.db.pool import connection
from cmp.db.redis import get_redis
from cmp.infrastructure import devcodes, devseed

router = APIRouter(tags=["development"], include_in_schema=False)


@router.get("/dev/codes", summary="Codes the console transports wrote, for the dev popup")
async def dev_codes(request: Request, response: Response) -> dict[str, Any]:
    """The asking tab's codes only - see `cmp.infrastructure.devcodes`."""
    response.headers["Cache-Control"] = "no-store"
    client = devcodes.client_id(request.headers.get(devcodes.CLIENT_HEADER))
    return {"items": await devcodes.recent(get_redis(), client=client)}


@router.get("/dev/seed-accounts", summary="Seed accounts still on the seed password")
async def dev_seed_accounts(response: Response) -> dict[str, Any]:
    """For the console's sign-in page - see `cmp.infrastructure.devseed`."""
    response.headers["Cache-Control"] = "no-store"
    async with connection() as conn:
        found = await devseed.accounts(conn)
    return {"password": settings.dev_seed_password if found else None, "accounts": found}
