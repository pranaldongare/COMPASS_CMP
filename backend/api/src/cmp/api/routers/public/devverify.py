"""A stand-in for the organisation's VerifyEmail, for a developer's machine.

Mounted only in `local` and `test` (`cmp.api.routers._development_routers`),
never in a deployment. Point the Employee check at it -
`http://localhost:8000/dev/verify-email` - and it answers as VerifyEmail does
(ADR 0046), by the address's local part, so every outcome can be tried:

* `left…` (left.priya@…, leftover@…): known, not employed now - IsActive false.
* `unknown…`: not known to the organisation - Status false.
* `down…`: no answer (a 503), as an outage.
* anything else: an active employee.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/dev/verify-email", tags=["development"], include_in_schema=False)


class Ask(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    my_single_id: str = Field(alias="MySingleID", min_length=3, max_length=320)


@router.post("/VerifyEmail")
async def verify_email(body: Ask) -> dict[str, Any]:
    local = body.my_single_id.split("@", 1)[0].lower()
    if local.startswith("down"):
        raise HTTPException(status_code=503)
    return {
        "MySingleID": body.my_single_id,
        "IsActive": not local.startswith(("left", "unknown")),
        "Status": not local.startswith("unknown"),
    }
