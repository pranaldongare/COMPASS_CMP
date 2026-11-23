"""Reports: asked for, made by the worker, kept, read, deleted, scheduled (ADR 0045).

A report is asked for in a request - the row is written, saying what it is
for, and the worker is queued after the commit - and made by the worker on the
`reports` queue: the figures counted, laid out, rendered, stored, hashed. Its
file is frozen from then on: a report of last month made today and one made
next week may differ, because the record may have changed, and each says when
it was made.

Who may read a report is who may ask for its kind (`cmp.core.metrics.REPORTS`),
of their own office or of none; a report of somebody's own work only they. The
product owner's rule: every report is kept until somebody who may read it
deletes it. Every download and every deletion is on the trail.

A schedule makes its kind on a cadence for the period just ended, and mails
it to the active accounts of the roles named - only roles that may read the
kind - as an attachment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cmp.core import metrics as cat
from cmp.core.errors import Forbidden, NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.core.permissions import OFFICE_TITLES, ROLE_TITLES, Role
from cmp.db.repositories import analytics as repo
from cmp.db.sql import Conn, Row
from cmp.domain.analytics import periods, service
from cmp.domain.analytics.service import Reader
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.report_files import Content, Section

log = get_logger("cmp.reports")

#: The figures a report's numbers are counted under: bump with the catalogue.
DEFINITIONS_VERSION = "2026-11-23"

_ENTITY_TYPES = ("rights_request", "breach")


# ------------------------------------------------------------------ access


def _kind(key: str) -> cat.ReportKind:
    kind = cat.REPORTS.get(key)
    if kind is None:
        raise NotFound("Report kind")
    return kind


def may_read(reader: Reader, row: Row) -> bool:
    kind = cat.REPORTS.get(str(row["kind"]))
    if kind is None or reader.role not in kind.audience:
        return False
    if kind.private and row.get("requested_by") != reader.user_id:
        return False
    # An officer reads their own office's reports and never one of both
    # offices - it would carry the other office's figures (ADR 0032). The
    # table's policy says the same.
    return reader.office is None or row.get("office") == reader.office


def _readable_kinds(reader: Reader) -> tuple[list[str], list[str]]:
    kinds = [k.key for k in cat.reports_for(reader.role)]
    private = [k for k in kinds if cat.REPORTS[k].private]
    return kinds, private


# ------------------------------------------------------------------ params


def _period_of(params: dict[str, Any]) -> periods.Period:
    from datetime import date

    def day(v: Any) -> date | None:
        return date.fromisoformat(str(v)) if v else None

    return periods.resolve(
        str(params.get("period") or "last_month"),
        start=day(params.get("start")),
        end=day(params.get("end")),
    )


async def _clean(
    conn: Conn, reader: Reader, kind: cat.ReportKind, fmt: str, params: dict[str, Any]
) -> tuple[dict[str, Any], str | None, str]:
    """What the report is for, checked; its office; its title."""
    if reader.role not in kind.audience:
        raise Forbidden(f"'{kind.title}' is not a report you may ask for")
    if fmt not in kind.formats:
        raise ValidationFailed(f"'{kind.title}' comes as {', '.join(kind.formats)}", field="format")
    out: dict[str, Any] = {}
    title = kind.title
    if kind.key != "case_evidence":
        period = _period_of(params)
        out.update(
            period=period.preset,
            start=params.get("start") if period.preset == "custom" else None,
            end=params.get("end") if period.preset == "custom" else None,
        )
        title = f"{kind.title} - {period.label}"
    office = None
    if kind.key not in ("health", "data_quality") or reader.office is not None:
        office = service.office_for(reader, params.get("office") or None)
    if kind.key in ("health",):
        office = None
    if kind.key == "audit":
        key = str(params.get("audit") or "")
        spec = cat.AUDIT_REPORTS.get(key)
        if spec is None:
            raise ValidationFailed(
                f"Choose an audit report: {', '.join(cat.AUDIT_REPORTS)}", field="audit"
            )
        out["audit"] = key
        title = f"{spec.title} - {title.split(' - ', 1)[1]}"
    if kind.key == "case_evidence":
        entity_type = str(params.get("entity_type") or "")
        if entity_type not in _ENTITY_TYPES:
            raise ValidationFailed("Choose a rights request or a breach", field="entity_type")
        found = await repo.entity_id_of(conn, entity_type, str(params.get("entity_uuid") or ""))
        if found is None:
            raise NotFound("Record")
        out.update(entity_type=entity_type, entity_uuid=str(params["entity_uuid"]))
        title = f"Evidence pack - {found[1]}"
    if office:
        title += f" ({OFFICE_TITLES.get(office, office)})"
    return out, office, title


async def request(
    conn: Conn, reader: Reader, *, kind_key: str, fmt: str, params: dict[str, Any]
) -> Row:
    """Ask for a report: written now, made by the worker after the commit."""
    kind = _kind(kind_key)
    clean, office, title = await _clean(conn, reader, kind, fmt, params)
    made = await repo.add_report(
        conn,
        kind=kind.key,
        title=title,
        params=clean,
        office=office,
        fmt=fmt,
        requested_by=reader.user_id,
        requested_role=reader.role,
    )
    await audit.record(
        conn,
        event=Event.REPORT_GENERATED,
        entity_type="report",
        entity_id=int(made["report_id"]),
        actor_user_id=reader.user_id,
        detail={"kind": kind.key, "format": fmt, "office": office, **clean},
    )
    _queue(str(made["report_uuid"]))
    row = await repo.report_by_id(conn, int(made["report_id"]))
    assert row is not None
    return row


def _queue(report_uuid: str) -> None:
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.reports import generate_report

    dispatch_optional(generate_report, report_uuid)


async def listing(conn: Conn, reader: Reader) -> list[Row]:
    kinds, private = _readable_kinds(reader)
    rows = await repo.reports(
        conn, kinds=kinds, office=reader.office, private_for=reader.user_id, private_kinds=private
    )
    return [r for r in rows if may_read(reader, r)]


async def readable(conn: Conn, reader: Reader, report_uuid: str) -> Row:
    row = await repo.report_by_uuid(conn, report_uuid)
    if row is None or not may_read(reader, row):
        raise NotFound("Report")
    return row


async def download(conn: Conn, reader: Reader, report_uuid: str) -> tuple[bytes, str, str]:
    """The frozen file, its name and its type. On the trail."""
    from cmp.core.security import file_hash
    from cmp.infrastructure.report_files import MIME
    from cmp.infrastructure.storage.service import read_upload

    row = await readable(conn, reader, report_uuid)
    if row["status"] != "ready" or not row["file_ref"]:
        raise ValidationFailed("This report is not ready", field="report")
    data = read_upload(str(row["file_ref"]))
    if file_hash(data) != row["file_sha256"]:
        # Kept as made, or not served: a file that no longer matches its
        # hash is not the report that was made.
        log.error("report.hash_mismatch", report=report_uuid)
        raise ValidationFailed("This report's file does not match what was made", field="report")
    await audit.record(
        conn,
        event=Event.REPORT_DOWNLOADED,
        entity_type="report",
        entity_id=int(row["report_id"]),
        actor_user_id=reader.user_id,
        detail={"kind": row["kind"], "format": row["format"], "sha256": row["file_sha256"]},
    )
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(row["title"]))[:80]
    return data, f"{stem.strip('-') or 'report'}.{row['format']}", MIME[str(row["format"])]


async def delete(conn: Conn, reader: Reader, report_uuid: str) -> None:
    """Gone, file and all; that it was made and deleted stays on the trail."""
    from cmp.infrastructure.storage.service import delete_upload

    row = await readable(conn, reader, report_uuid)
    await repo.delete_report(conn, int(row["report_id"]))
    await audit.record(
        conn,
        event=Event.REPORT_DELETED,
        entity_type="report",
        entity_id=int(row["report_id"]),
        actor_user_id=reader.user_id,
        detail={"kind": row["kind"], "sha256": row["file_sha256"]},
    )
    if row["file_ref"]:
        from cmp.core import after_commit

        ref = str(row["file_ref"])
        if not after_commit.defer(lambda: delete_upload(ref)):
            delete_upload(ref)


# ------------------------------------------------------------------ making


def _fmt_value(m: dict[str, Any], key: str = "value") -> str:
    v = m.get(key)
    if m.get("suppressed" if key == "value" else "previous_suppressed"):
        return "withheld (small number)"
    if v is None:
        return "-"
    unit = m["unit"]
    if unit == "percent":
        return f"{v:g}%"
    if unit in ("days", "hours"):
        return f"{v:g} {unit}"
    return f"{v:g}"


_STATUS = {"green": "On target", "amber": "Watch", "red": "Off target", None: ""}


def _scorecard_section(heading: str, figures: dict[str, Any]) -> Section:
    rows = []
    for m in figures["metrics"]:
        target = (
            ""
            if m["target"] is None
            else ("at least " if m["higher_is_better"] else "at most ")
            + _fmt_value({**m, "value": m["target"], "suppressed": False})
        )
        rows.append(
            [
                m["group"],
                m["title"],
                _fmt_value(m),
                _fmt_value(m, "previous") if m["kind"] not in (cat.SNAPSHOT, cat.LIVE) else "now",
                "" if m["change"] is None else f"{m['change']:+g}",
                target,
                _STATUS[m["status"]],
            ]
        )
    return Section(
        heading,
        ["Area", "Figure", "This period", "Previous", "Change", "Target", "Status"],
        rows,
        widths=[14, 26, 12, 12, 8, 14, 10],
    )


def _definitions(figures: dict[str, Any]) -> Section:
    return Section(
        "What each figure counts",
        ["Figure", "Definition"],
        [[m["title"], m["definition"]] for m in figures["metrics"]],
        widths=[30, 70],
    )


def _breakdowns(figures_by_dim: list[tuple[str, dict[str, Any]]]) -> list[Section]:
    out = []
    for dim, figures in figures_by_dim:
        rows = []
        for m in figures["metrics"]:
            for part in m["breakdown"]:
                rows.append(
                    [
                        m["title"],
                        part["label"],
                        _fmt_value({**m, **part, "suppressed": part["suppressed"]}),
                    ]
                )
        if rows:
            out.append(
                Section(
                    f"By {cat.DIMENSIONS[dim].lower()}",
                    ["Figure", cat.DIMENSIONS[dim], "Value"],
                    rows,
                )
            )
    return out


async def _by_dims(
    conn: Conn, reader: Reader, section: str, period: periods.Period, office: str | None
) -> list[tuple[str, dict[str, Any]]]:
    metrics = cat.for_role(reader.role, section)
    dims: list[str] = []
    for m in metrics:
        for d in m.dims:
            if d not in dims and (d != "office" or reader.role == Role.MANAGEMENT.value):
                dims.append(d)
    out = []
    for d in dims:
        keys = [m.key for m in metrics if d in m.dims]
        figures = await service.figures(
            conn, reader, keys=keys, period=period, office=office, dim=d, compare=False, trend=False
        )
        out.append((d, figures))
    return out


async def build(conn: Conn, row: Row, reader: Reader) -> Content:
    """The report's content, counted now from the record."""
    from cmp.core.config import settings

    kind = _kind(str(row["kind"]))
    params: dict[str, Any] = dict(row["params"] or {})
    office = row.get("office")
    about: list[tuple[str, str]] = []
    sections: list[Section] = []
    notes: list[str] = []
    footer = "Figures only: no record about a person is in this report."
    period = _period_of(params) if kind.key != "case_evidence" else None
    if period is not None:
        about.append(
            (
                "Period",
                f"{period.label} ({period.as_dict()['start_date']} to "
                f"{period.as_dict()['end_date']}, India time)",
            )
        )
    about.append(("Office", str(OFFICE_TITLES.get(office, office)) if office else "Both offices"))
    asked = row.get("requested_by_name") or ("a schedule" if row.get("schedule_uuid") else "-")
    about.append(("Asked for by", f"{asked} ({ROLE_TITLES.get(str(row['requested_role']), '')})"))
    about.append(("Organisation", settings.organisation_name))
    about.append(("Definitions", f"version {DEFINITIONS_VERSION}"))

    if kind.key in ("management_scorecard", "board_pack", "analytics_summary", "my_analytics"):
        assert period is not None
        section = {
            "management_scorecard": "management",
            "board_pack": "management",
            "analytics_summary": "analytics",
            "my_analytics": "mine",
        }[kind.key]
        figures = await service.figures(
            conn, reader, section=section, period=period, office=office, trend=False
        )
        prev = figures["previous"]["label"] if figures["previous"] else "-"
        about.append(("Compared with", prev))
        threshold = int(figures["threshold"])
        if threshold > 1:
            notes.append(
                f"A count of fewer than {threshold} people is withheld, and so is a rate "
                "worked out from one."
            )
        sections.append(_scorecard_section("The figures", figures))
        if kind.key == "board_pack":
            breaches = await repo.breaches_in(
                conn, start=period.start, end=period.end, office=office
            )
            sections.append(
                Section(
                    "Breaches in the period",
                    ["Reference", "Detected", "Confirmed", "Status", "Where", "Duties done"],
                    [
                        [
                            b["reference"],
                            b["detected_at"],
                            b["confirmed_at"] or "not confirmed",
                            b["status"],
                            b["location_kind"],
                            f"{b['completed']} of {b['duties']}",
                        ]
                        for b in breaches
                    ],
                )
            )
        sections.extend(_breakdowns(await _by_dims(conn, reader, section, period, office)))
        sections.append(_definitions(figures))
    elif kind.key in ("health", "data_quality"):
        assert period is not None
        section = "health" if kind.key == "health" else "quality"
        figures = await service.figures(
            conn, reader, section=section, period=period, office=office, trend=False
        )
        sections.append(_scorecard_section("The figures", figures))
        if kind.key == "health":
            quality = await service.figures(
                conn, reader, section="quality", period=period, office=office, trend=False
            )
            sections.append(_scorecard_section("Data quality", quality))
        sections.extend(_breakdowns(await _by_dims(conn, reader, section, period, office)))
        sections.append(_definitions(figures))
    elif kind.key == "audit":
        assert period is not None
        spec = cat.AUDIT_REPORTS[str(params["audit"])]
        about.insert(0, ("Report", spec.title))
        notes.append(spec.description)
        footer = "From the audit trail. Handle as confidential: it names the people who acted."
        rows = await _trail_rows(conn, reader, events=spec.events, period=period)
        sections.append(
            Section(
                "What happened",
                ["When", "Event", "By", "Role", "About", "Record"],
                rows,
                widths=[14, 22, 16, 12, 16, 20],
            )
        )
    elif kind.key == "case_evidence":
        entity_type = str(params["entity_type"])
        found = await repo.entity_id_of(conn, entity_type, str(params["entity_uuid"]))
        if found is None:
            raise NotFound("Record")
        about.insert(0, ("Record", f"{found[1]} ({entity_type.replace('_', ' ')})"))
        footer = "From the audit trail. Handle as confidential: it names the people who acted."
        rows = await _trail_rows(conn, reader, entity=(entity_type, found[0]))
        sections.append(
            Section(
                "Everything recorded, in order",
                ["When", "Event", "By", "Role", "About", "Record"],
                rows,
                widths=[14, 22, 16, 12, 16, 20],
            )
        )
    elif kind.key == "data_inventory":
        inv = await repo.inventory(conn, office=office)
        sections.append(
            Section(
                "Purposes",
                [
                    "Code",
                    "Name",
                    "Status",
                    "Lawful basis",
                    "Data",
                    "Retention",
                    "Retention basis",
                    "Consent valid for",
                    "Cross-border",
                    "Minors",
                    "Office",
                ],
                [
                    [
                        p["purpose_code"],
                        p["name"],
                        p["status"],
                        p["lawful_basis"],
                        ", ".join(p["data_categories"] or []),
                        p["retention_period"],
                        p["retention_basis"],
                        p["consent_validity_period"] or "-",
                        p["cross_border_permitted"],
                        p["permitted_for_minors"],
                        OFFICE_TITLES.get(p["office"], p["office"]),
                    ]
                    for p in inv["purposes"]
                ],
            )
        )
        sections.append(
            Section(
                "Processors",
                ["Name", "Type", "Status", "In-house", "Country", "Security confirmed", "Contract"],
                [
                    [
                        x["legal_name"],
                        x["type"],
                        x["status"],
                        x["is_in_house"],
                        x["location_country"] or "-",
                        x["security_confirmed_at"] or "-",
                        x["contract_ref"] or "-",
                    ]
                    for x in inv["processors"]
                ],
            )
        )
        sections.append(
            Section(
                "Data sources",
                ["Code", "Name", "Status", "Role", "Exchange", "Processor"],
                [
                    [
                        s["source_code"],
                        s["name"],
                        s["status"],
                        s["source_role"],
                        s["exchange_mode"],
                        s["processor"] or "-",
                    ]
                    for s in inv["sources"]
                ],
            )
        )
    return Content(
        title=str(row["title"]),
        subtitle=kind.description,
        about=about,
        sections=sections,
        notes=notes,
        footer=footer,
    )


async def _trail_rows(
    conn: Conn,
    reader: Reader,
    *,
    events: tuple[str, ...] | None = None,
    period: periods.Period | None = None,
    entity: tuple[str, int] | None = None,
) -> list[list[Any]]:
    """The trail as an auditor reads it: names opened, record labels joined."""
    from cmp.db.repositories import audit as audit_repo
    from cmp.db.repositories import entities as entity_repo
    from cmp.domain.audit.vocabulary import event_types
    from cmp.infrastructure.dkms import unseal_strings

    filters = audit_repo.AuditFilters(
        event_types=events,
        date_from=period.start if period else None,
        date_to=period.end if period else None,
        entity_type=entity[0] if entity else None,
        entity_id=entity[1] if entity else None,
        office=reader.office,
    )
    rows = await audit_repo.export_rows(conn, filters)
    rows = list(reversed(await entity_repo.attach(conn, rows, reader_role=reader.role)))
    opened = await unseal_strings(
        [
            v
            for r in rows
            for v in (r.get("actor_name"), r.get("subject_name"), r.get("entity_label"))
        ]
        + [p for r in rows for p in (r.get("entity_label_parts") or [])]
    )

    def plain(value: Any) -> Any:
        return opened.get(value, value) if isinstance(value, str) else value

    labels = {e["value"]: f"{e['group_label']}: {e['label'].lower()}" for e in event_types()}
    out = []
    for r in rows:
        parts = r.get("entity_label_parts")
        record = " ".join(str(plain(p)) for p in parts) if parts else plain(r.get("entity_label"))
        out.append(
            [
                r["occurred_at"],
                labels.get(r["event_type"], r["event_type"]),
                plain(r.get("actor_name")) or "the platform",
                ROLE_TITLES.get(str(r.get("actor_role") or ""), ""),
                plain(r.get("subject_name")) or "",
                record or r.get("entity_type") or "",
            ]
        )
    return out


async def make(conn: Conn, report_uuid: str) -> Row | None:
    """The worker's half: count, lay out, render, store, hash. A failure is
    recorded on the row, never raised past it: a report that cannot be made
    says so where it is listed."""
    from cmp.core.security import file_hash
    from cmp.infrastructure.report_files import render
    from cmp.infrastructure.storage.service import storage

    row = await repo.report_by_uuid(conn, report_uuid)
    if row is None or row["status"] != "queued":
        return row
    reader = Reader(
        role=str(row["requested_role"]),
        user_id=int(row["requested_by"] or 0),
        office=row.get("office") if str(row["requested_role"]) in ("dpo", "legal") else None,
    )
    if reader.role in cat.WORKERS:
        from cmp.db.repositories import users as user_repo

        person = await user_repo.by_id(conn, reader.user_id) if reader.user_id else None
        reader = Reader(reader.role, reader.user_id, (person or {}).get("office_code"))
    try:
        await repo.read_as(conn, reader.office)
        content = await build(conn, row, reader)
        data = render(content, str(row["format"]))
        ref = storage().save(data, subdir="reports", suggested_name=f"report.{row['format']}")
        await repo.report_ready(
            conn, int(row["report_id"]), file_ref=ref, sha256=file_hash(data), size=len(data)
        )
    except Exception as exc:  # recorded, and the worker goes on
        log.error("report.failed", report=report_uuid, error=type(exc).__name__)
        await repo.report_failed(conn, int(row["report_id"]), f"{type(exc).__name__}: {exc}"[:300])
    return await repo.report_by_uuid(conn, report_uuid)


# --------------------------------------------------------------- schedules


async def schedule(
    conn: Conn,
    reader: Reader,
    *,
    kind_key: str,
    fmt: str,
    cadence: str,
    recipient_roles: list[str],
    params: dict[str, Any],
) -> Row:
    kind = _kind(kind_key)
    if not kind.schedulable:
        raise ValidationFailed(f"'{kind.title}' is made on request only", field="kind")
    if cadence not in periods.CADENCES:
        raise ValidationFailed(f"Choose a cadence: {', '.join(periods.CADENCES)}", field="cadence")
    roles = sorted(set(recipient_roles))
    if not roles:
        raise ValidationFailed("Name at least one role to send it to", field="recipient_roles")
    outside = [r for r in roles if r not in kind.audience]
    if outside:
        raise ValidationFailed(
            f"'{kind.title}' may be read only by: "
            + ", ".join(ROLE_TITLES.get(r, r) for r in sorted(kind.audience)),
            field="recipient_roles",
        )
    if kind.private:
        raise ValidationFailed("A report of your own work is not mailed to others", field="kind")
    clean, office, title = await _clean(conn, reader, kind, fmt, {**params, "period": "last_month"})
    clean.pop("period", None)
    clean.pop("start", None)
    clean.pop("end", None)
    title = title.split(" - ")[0] + (f" ({OFFICE_TITLES[office]})" if office else "")
    made = await repo.add_schedule(
        conn,
        kind=kind.key,
        title=title,
        params=clean,
        fmt=fmt,
        cadence=cadence,
        recipient_roles=roles,
        office=office,
        created_by=reader.user_id,
        created_role=reader.role,
        next_run_at=periods.next_run(cadence, service.now_utc()),
    )
    await audit.record(
        conn,
        event=Event.REPORT_SCHEDULE_CREATED,
        entity_type="report_schedule",
        entity_id=int(made["schedule_id"]),
        actor_user_id=reader.user_id,
        detail={"kind": kind.key, "cadence": cadence, "roles": roles, "office": office},
    )
    row = await repo.schedule_by_uuid(conn, str(made["schedule_uuid"]))
    assert row is not None
    return row


def _may_manage(reader: Reader, row: Row) -> bool:
    kind = cat.REPORTS.get(str(row["kind"]))
    return bool(
        kind
        and reader.role in kind.audience
        and (reader.office is None or row.get("office") == reader.office)
    )


async def schedules(conn: Conn, reader: Reader) -> list[Row]:
    kinds, private = _readable_kinds(reader)
    rows = await repo.schedules(
        conn, kinds=[k for k in kinds if k not in private], office=reader.office
    )
    return [r for r in rows if _may_manage(reader, r)]


async def _schedule(conn: Conn, reader: Reader, schedule_uuid: str) -> Row:
    row = await repo.schedule_by_uuid(conn, schedule_uuid)
    if row is None or not _may_manage(reader, row):
        raise NotFound("Schedule")
    return row


async def set_active(conn: Conn, reader: Reader, schedule_uuid: str, *, active: bool) -> Row:
    row = await _schedule(conn, reader, schedule_uuid)
    await repo.set_schedule(conn, int(row["schedule_id"]), active=active)
    if active and not row["active"]:
        await repo.schedule_ran(
            conn,
            int(row["schedule_id"]),
            ran_at=row["last_run_at"] or service.now_utc(),
            next_at=periods.next_run(str(row["cadence"]), service.now_utc()),
        )
    await audit.record(
        conn,
        event=Event.REPORT_SCHEDULE_UPDATED,
        entity_type="report_schedule",
        entity_id=int(row["schedule_id"]),
        actor_user_id=reader.user_id,
        detail={"active": active},
    )
    fresh = await repo.schedule_by_uuid(conn, schedule_uuid)
    assert fresh is not None
    return fresh


async def delete_schedule(conn: Conn, reader: Reader, schedule_uuid: str) -> None:
    row = await _schedule(conn, reader, schedule_uuid)
    await repo.delete_schedule(conn, int(row["schedule_id"]))
    await audit.record(
        conn,
        event=Event.REPORT_SCHEDULE_DELETED,
        entity_type="report_schedule",
        entity_id=int(row["schedule_id"]),
        actor_user_id=reader.user_id,
        detail={"kind": row["kind"]},
    )


async def run_due(conn: Conn, now: datetime) -> list[tuple[str, list[str], str]]:
    """Each due schedule's report, asked for now for the period just ended.
    Returns, per report, who it goes to and the period's words: the worker
    makes it and mails it once this commits."""
    out = []
    for s in await repo.due_schedules(conn, now):
        period = periods.covered_by(str(s["cadence"]), now)
        params = {
            **dict(s["params"] or {}),
            "period": "custom",
            "start": str(period.as_dict()["start_date"]),
            "end": str(period.as_dict()["end_date"]),
        }
        made = await repo.add_report(
            conn,
            kind=str(s["kind"]),
            title=f"{s['title']} - {period.label}",
            params=params,
            office=s.get("office"),
            fmt=str(s["format"]),
            requested_by=None,
            requested_role=str(s["created_role"]),
            schedule_id=int(s["schedule_id"]),
        )
        await audit.record(
            conn,
            event=Event.REPORT_GENERATED,
            entity_type="report",
            entity_id=int(made["report_id"]),
            actor_user_id=None,
            detail={"kind": s["kind"], "schedule": s["schedule_uuid"], "format": s["format"]},
        )
        await repo.schedule_ran(
            conn,
            int(s["schedule_id"]),
            ran_at=now,
            next_at=periods.next_run(str(s["cadence"]), now),
        )
        emails = await repo.emails_for_roles(
            conn, list(s["recipient_roles"] or []), office=s.get("office")
        )
        out.append((str(made["report_uuid"]), emails, period.label))
    return out
