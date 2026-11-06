"""Reporting an incident, with no account (0058, ADR 0037).

The public link's two calls: a code to the address typed, then the report with
that code. Nothing is stored until the code comes back, so a stranger who
never answers leaves no row. Unauthenticated and rate limited per address and
per contact, like every route of its kind; what arrives waits in the shared
intake, on no clock, for one of the two officers to read it.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Request, Response, status
from pydantic import AwareDatetime, Field

from cmp.api.middleware import client_ip
from cmp.db.pool import transaction
from cmp.db.repositories.breaches import LOGGED_TEXT
from cmp.domain.breach import intake
from cmp.schemas.common import Acknowledged, OtpCode, Out, Schema, ShortText
from cmp.validation.contacts import Email

router = APIRouter(prefix="/incident-reports", tags=["incident reports"])

_Text = Annotated[str, Field(max_length=8000)]


def _private(response: Response) -> None:
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"


class IncidentCodeIn(Schema):
    email: Email


class IncidentReportIn(Schema):
    name: ShortText
    email: Email
    code: OtpCode
    #: What happened, in a line.
    title: Annotated[str, Field(min_length=1, max_length=300)]
    #: As much as they know. The only detail asked for: the rest may be left.
    incident_details: Annotated[str, Field(min_length=1, max_length=8000)]
    #: When they noticed it, if they can say.
    noticed_at: AwareDatetime | None = None
    origin: _Text | None = None
    discovery: _Text | None = None
    affected_systems: _Text | None = None
    impact_scale: _Text | None = None
    countries_involved: _Text | None = None
    data_nature: _Text | None = None
    subject_types: _Text | None = None
    entities_involved: _Text | None = None
    third_parties: _Text | None = None
    #: yes, no or unknown. It starts nothing: the office reads it and decides.
    cyber_attack: Annotated[str | None, Field(default=None, pattern="^(yes|no|unknown)$")] = None


class IncidentReportReceivedOut(Out):
    #: INC-YYYY-NNNN. All a reporter is given, and what they may quote.
    reference: str
    message: str


@router.post("/code", response_model=Acknowledged, summary="A code to the address given")
async def report_code(body: IncidentCodeIn, request: Request, response: Response) -> dict[str, Any]:
    _private(response)
    return {"message": await intake.send_code(email=body.email, ip_address=client_ip(request))}


@router.post(
    "",
    response_model=IncidentReportReceivedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Report an incident, with the code",
)
async def report_incident(
    body: IncidentReportIn, request: Request, response: Response
) -> dict[str, Any]:
    _private(response)
    async with transaction() as conn:
        return await intake.submit(
            conn,
            reporter_name=body.name,
            email=body.email,
            code=body.code,
            title=body.title,
            noticed_at=body.noticed_at,
            told=body.model_dump(include=set(LOGGED_TEXT)),
            cyber_attack=body.cyber_attack,
            ip_address=client_ip(request),
        )
