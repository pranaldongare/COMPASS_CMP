"""Analytics, audit and health reports, and generated reports (ADR 0045).

Distinct from `/dashboard`, which is what needs a person today. These are the
figures over a period, against targets; the ready-made reports over the audit
trail; the platform's health; the record of processing; and reports made as
files, kept, scheduled and mailed.

The matrix admits a role to each part (`analytics`, `audit_report`,
`health_report`, `analytics_setting`, `report`); the catalogue
(`cmp.core.metrics`) then decides which figures and which report kinds within
it, checked again by the service. Figures are counts: nothing here returns a
record about a person, except the audit reports, which are the trail as the
audit pages already show it to the same roles.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import Field

from cmp.api.dependencies import CurrentUser, Paging, RequireResource
from cmp.auth.identity import Principal
from cmp.core import metrics as cat
from cmp.core.errors import Forbidden
from cmp.core.pagination import PageRequest
from cmp.core.permissions import can_read
from cmp.db.pool import connection, transaction
from cmp.db.repositories import audit as audit_repo
from cmp.domain.analytics import periods, reports, service
from cmp.domain.analytics.service import Reader
from cmp.schemas.common import Acknowledged, Out, Schema

router = APIRouter(prefix="/analytics", tags=["analytics"])
reports_router = APIRouter(prefix="/reports", tags=["reports"])

AuditReportReader = Annotated[Principal, Depends(RequireResource("audit_report"))]
SettingReader = Annotated[Principal, Depends(RequireResource("analytics_setting"))]
SettingWriter = Annotated[Principal, Depends(RequireResource("analytics_setting", write=True))]
ReportReader = Annotated[Principal, Depends(RequireResource("report"))]
ReportWriter = Annotated[Principal, Depends(RequireResource("report", write=True))]
InventoryReader = Annotated[Principal, Depends(RequireResource("analytics"))]

audit_paging = Paging(audit_repo.LIST_SORTS, "-occurred_at")

PeriodQ = Annotated[str, Query(description="A preset: " + ", ".join(periods.PRESETS))]
DayQ = Annotated[date | None, Query(description="custom: the first or last day, India time")]
OfficeQ = Annotated[
    str | None, Query(pattern="^(rnd|hr)$", description="Management only: one office")
]


def _reader(principal: Principal) -> Reader:
    return Reader(
        role=str(getattr(principal.role, "value", principal.role)),
        user_id=int(principal.user_id),
        office=principal.office,
    )


def _period(period: str, start: date | None, end: date | None) -> periods.Period:
    return periods.resolve(period, start=start, end=end)


# ------------------------------------------------------------------ schemas


class Choice(Out):
    key: str
    label: str


class MetricInfo(Out):
    key: str
    title: str
    definition: str
    unit: str
    section: str
    group: str
    kind: str
    dims: list[str]
    people: bool


class ReportKindInfo(Out):
    key: str
    title: str
    description: str
    formats: list[str]
    schedulable: bool
    recipient_roles: list[str]


class AuditReportInfo(Out):
    key: str
    title: str
    description: str


class CatalogueOut(Out):
    role: str
    office: str | None
    may_choose_office: bool
    sections: list[str]
    metrics: list[MetricInfo]
    dimensions: list[Choice]
    periods: list[Choice]
    cadences: list[Choice]
    reports: list[ReportKindInfo]
    audit_reports: list[AuditReportInfo]


class PeriodOut(Out):
    preset: str
    start: datetime
    end: datetime
    label: str
    start_date: date
    end_date: date


class PointOut(Out):
    bucket: date | None
    value: float | None
    suppressed: bool


class PartOut(Out):
    key: str | None
    label: str
    value: float | None
    suppressed: bool


class FigureOut(Out):
    key: str
    title: str
    definition: str
    unit: str
    section: str
    group: str
    kind: str
    dims: list[str]
    value: float | None
    #: Withheld: a count of fewer people than the threshold.
    suppressed: bool
    previous: float | None
    previous_suppressed: bool
    change: float | None
    target: float | None
    amber: float | None
    higher_is_better: bool
    #: green | amber | red, against the target; none without one.
    status: str | None
    series: list[PointOut]
    breakdown: list[PartOut]


class FiguresOut(Out):
    period: PeriodOut
    previous: PeriodOut | None
    office: str | None
    dim: str | None
    grain: str | None
    threshold: int
    metrics: list[FigureOut]


class TargetOut(Out):
    key: str
    title: str
    unit: str
    section: str
    group: str
    higher_is_better: bool
    default_target: float | None
    default_amber: float | None
    target: float | None
    amber: float | None
    customised: bool
    updated_at: datetime | None
    updated_by_name: str | None


class SettingsOut(Out):
    small_number_threshold: int
    updated_at: datetime | None
    updated_by_name: str | None
    targets: list[TargetOut]


class TargetIn(Schema):
    target: float = Field(ge=0)
    amber: float | None = Field(default=None, ge=0)


class ThresholdIn(Schema):
    small_number_threshold: int = Field(ge=1, le=100)


class AuditRowOut(Out):
    log_uuid: UUID
    event_type: str
    entity_type: str | None = None
    occurred_at: datetime
    actor_uuid: UUID | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    subject_uuid: UUID | None = None
    subject_name: str | None = None
    detail: dict[str, Any] | None = None


class AuditReportOut(Out):
    key: str
    title: str
    description: str
    events: list[str]
    period: PeriodOut
    items: list[AuditRowOut]
    next_cursor: str | None
    total: int
    summary: dict[str, Any]


class InventoryOut(Out):
    purposes: list[dict[str, Any]]
    processors: list[dict[str, Any]]
    sources: list[dict[str, Any]]


class ReportOut(Out):
    report_uuid: UUID
    kind: str
    title: str
    params: dict[str, Any]
    office: str | None
    format: str
    status: str
    file_sha256: str | None
    file_bytes: int | None
    error: str | None
    requested_by_name: str | None
    requested_role: str
    schedule_uuid: UUID | None
    created_at: datetime
    ready_at: datetime | None


class ReportIn(Schema):
    kind: str = Field(max_length=48)
    format: str = Field(pattern="^(pdf|xlsx|csv)$")
    period: str | None = Field(default=None, max_length=24)
    start: date | None = None
    end: date | None = None
    office: str | None = Field(default=None, pattern="^(rnd|hr)$")
    audit: str | None = Field(default=None, max_length=32)
    entity_type: str | None = Field(default=None, pattern="^(rights_request|breach)$")
    entity_uuid: UUID | None = None


class ScheduleOut(Out):
    schedule_uuid: UUID
    kind: str
    title: str
    params: dict[str, Any]
    format: str
    cadence: str
    recipient_roles: list[str]
    office: str | None
    active: bool
    created_by_name: str | None
    created_role: str
    created_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime


class ScheduleIn(Schema):
    kind: str = Field(max_length=48)
    format: str = Field(pattern="^(pdf|xlsx|csv)$")
    cadence: str = Field(pattern="^(weekly|monthly|quarterly)$")
    recipient_roles: list[str] = Field(min_length=1, max_length=10)
    office: str | None = Field(default=None, pattern="^(rnd|hr)$")
    audit: str | None = Field(default=None, max_length=32)


class ScheduleChangeIn(Schema):
    active: bool


# ------------------------------------------------------------------ figures


def _may_open(principal: Principal, section: str | None) -> None:
    """The section's own resource: health for the administrator, audit for
    the audit readers, analytics for the rest."""
    resource = {"health": "health_report", "quality": "report", "audit": "audit_report"}.get(
        section or "", "analytics"
    )
    if not can_read(resource, principal.role):
        raise Forbidden("Your role does not permit this action")


@router.get("/catalogue", response_model=CatalogueOut, summary="What this reader may see")
async def get_catalogue(principal: ReportReader) -> dict[str, Any]:
    return service.catalogue(_reader(principal))


@router.get("/figures", response_model=FiguresOut, summary="Figures for a period")
async def get_figures(
    principal: CurrentUser,
    section: Annotated[str | None, Query(max_length=24)] = None,
    keys: Annotated[list[str] | None, Query(max_length=60)] = None,
    period: PeriodQ = "this_month",
    start: DayQ = None,
    end: DayQ = None,
    office: OfficeQ = None,
    dim: Annotated[str | None, Query(max_length=24)] = None,
    compare: bool = True,
    trend: bool = True,
) -> dict[str, Any]:
    """The figures of a section, or the metrics named, for the period, with
    the previous period, the target and its status, a line and a breakdown."""
    _may_open(
        principal,
        section or (cat.metric(keys[0]).section if keys and keys[0] in cat.METRICS else None),
    )
    async with connection() as conn:
        return await service.figures(
            conn,
            _reader(principal),
            keys=keys,
            section=section,
            period=_period(period, start, end),
            office=office,
            dim=dim,
            compare=compare,
            trend=trend,
        )


@router.get("/inventory", response_model=InventoryOut, summary="The record of processing")
async def get_inventory(principal: InventoryReader, office: OfficeQ = None) -> dict[str, Any]:
    async with connection() as conn:
        return await service.inventory(conn, _reader(principal), office=office)


@router.get(
    "/audit-reports/{key}", response_model=AuditReportOut, summary="One ready-made audit report"
)
async def get_audit_report(
    key: Annotated[str, Field(max_length=32)],
    principal: AuditReportReader,
    page: Annotated[PageRequest, Depends(audit_paging)],
    period: PeriodQ = "last_30_days",
    start: DayQ = None,
    end: DayQ = None,
) -> dict[str, Any]:
    async with connection() as conn:
        out = await service.audit_report(
            conn, _reader(principal), key, period=_period(period, start, end), page=page
        )
    return out


# ------------------------------------------------- targets and the threshold


@router.get("/settings", response_model=SettingsOut, summary="Targets and the threshold")
async def get_settings(principal: SettingReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.settings_view(conn)


@router.put("/targets/{key}", response_model=SettingsOut, summary="Set a metric's target")
async def put_target(
    key: Annotated[str, Field(max_length=64)], body: TargetIn, principal: SettingWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.set_target(
            conn, key, target=body.target, amber=body.amber, actor_id=principal.user_id
        )


@router.delete("/targets/{key}", response_model=SettingsOut, summary="Back to the default target")
async def delete_target(
    key: Annotated[str, Field(max_length=64)], principal: SettingWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.set_target(
            conn, key, target=None, amber=None, actor_id=principal.user_id
        )


@router.put("/settings/threshold", response_model=SettingsOut, summary="The small-number threshold")
async def put_threshold(body: ThresholdIn, principal: SettingWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.set_threshold(
            conn, body.small_number_threshold, actor_id=principal.user_id
        )


# ------------------------------------------------------------------ reports


@reports_router.get("", response_model=list[ReportOut], summary="The reports this reader may see")
async def list_reports(principal: ReportReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await reports.listing(conn, _reader(principal))


@reports_router.post(
    "", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED, summary="Ask for a report"
)
async def create_report(body: ReportIn, principal: ReportWriter) -> dict[str, Any]:
    params = body.model_dump(exclude={"kind", "format"}, mode="json", exclude_none=True)
    async with transaction() as conn:
        return await reports.request(
            conn, _reader(principal), kind_key=body.kind, fmt=body.format, params=params
        )


@reports_router.get("/schedules", response_model=list[ScheduleOut], summary="Report schedules")
async def list_schedules(principal: ReportReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await reports.schedules(conn, _reader(principal))


@reports_router.post(
    "/schedules",
    response_model=ScheduleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Make a report on a cadence and mail it",
)
async def create_schedule(body: ScheduleIn, principal: ReportWriter) -> dict[str, Any]:
    params = {k: v for k, v in {"office": body.office, "audit": body.audit}.items() if v}
    async with transaction() as conn:
        return await reports.schedule(
            conn,
            _reader(principal),
            kind_key=body.kind,
            fmt=body.format,
            cadence=body.cadence,
            recipient_roles=body.recipient_roles,
            params=params,
        )


@reports_router.patch(
    "/schedules/{schedule_uuid}", response_model=ScheduleOut, summary="Pause or resume a schedule"
)
async def change_schedule(
    schedule_uuid: UUID, body: ScheduleChangeIn, principal: ReportWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await reports.set_active(
            conn, _reader(principal), str(schedule_uuid), active=body.active
        )


@reports_router.delete(
    "/schedules/{schedule_uuid}", response_model=Acknowledged, summary="Remove a schedule"
)
async def remove_schedule(schedule_uuid: UUID, principal: ReportWriter) -> dict[str, Any]:
    async with transaction() as conn:
        await reports.delete_schedule(conn, _reader(principal), str(schedule_uuid))
    return {"ok": True, "message": "The schedule is removed. Reports it made are kept."}


@reports_router.get("/{report_uuid}", response_model=ReportOut, summary="One report")
async def get_report(report_uuid: UUID, principal: ReportReader) -> dict[str, Any]:
    async with connection() as conn:
        return await reports.readable(conn, _reader(principal), str(report_uuid))


@reports_router.get("/{report_uuid}/file", summary="Download a report, as it was made")
async def download_report(report_uuid: UUID, principal: ReportReader) -> Response:
    async with transaction() as conn:
        data, name, mime = await reports.download(conn, _reader(principal), str(report_uuid))
    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store, private",
        },
    )


@reports_router.delete("/{report_uuid}", response_model=Acknowledged, summary="Delete a report")
async def delete_report(report_uuid: UUID, principal: ReportWriter) -> dict[str, Any]:
    async with transaction() as conn:
        await reports.delete(conn, _reader(principal), str(report_uuid))
    return {
        "ok": True,
        "message": "The report and its file are deleted. The trail keeps that it was.",
    }
