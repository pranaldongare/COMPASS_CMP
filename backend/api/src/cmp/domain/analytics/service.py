"""The figures, for whoever is reading them (ADR 0045).

`figures()` answers one question: these metrics, for this period, for this
reader, compared with the period before, against their targets, split by one
breakdown and drawn as a line. Who the reader is decides three things:

* **which metrics** - the catalogue's audience (`cmp.core.metrics`);
* **which office** - management chooses (both, or one); an officer reads
  their own, as their session does; the roles that do the work read their own
  work, through the project register's scope; the administrator reads the
  platform's health, which belongs to no office;
* **what is withheld** - a count of people above nought and below the
  threshold the administrator sets is "fewer than N", in the figure, its
  comparison, its breakdown and its line.

Nothing is stored: every figure is counted from the record when asked, so it
is the record's. A report freezes what it was told (`cmp.domain.analytics.reports`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cmp.core import metrics as cat
from cmp.core.errors import Forbidden, NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.core.pagination import PageRequest
from cmp.core.permissions import OFFICE_TITLES, Role
from cmp.db.repositories import analytics as repo
from cmp.db.sql import Conn, Row
from cmp.domain.analytics.periods import Period, grain_for, previous
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

log = get_logger("cmp.analytics")

#: The queues the workers read (`cmp.tasks.app`), for the live queue depth.
QUEUES = ("high_priority", "email", "documents", "reports", "notifications", "default")

OFFICES = ("rnd", "hr")


@dataclass(frozen=True, slots=True)
class Reader:
    role: str
    user_id: int
    #: The session's office: an officer's, an author's, a collector's; None for
    #: management and the administrator.
    office: str | None


def office_for(reader: Reader, wanted: str | None) -> str | None:
    """The office the figures are of. Management chooses, or both; anybody in
    an office reads that office; nobody else names one."""
    if wanted is not None and wanted not in OFFICES:
        raise ValidationFailed("Choose an office: rnd or hr", field="office")
    if reader.role == Role.MANAGEMENT.value:
        return wanted
    if reader.office is not None:
        if wanted is not None and wanted != reader.office:
            raise Forbidden("You read your own office's figures")
        return reader.office
    if wanted is not None:
        raise Forbidden("These figures belong to no office")
    return None


def _scope(reader: Reader) -> tuple[str, list[Any]] | None:
    if reader.role not in cat.WORKERS:
        return None
    from cmp.db.repositories.projects import scope_predicate

    pred, params = scope_predicate(reader.role, reader.user_id)
    return pred, list(params)


def _round(unit: str, value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 1) if unit in ("percent", "days", "hours") else float(round(value))


def status(
    m: cat.Metric, value: float | None, target: float | None, amber: float | None
) -> str | None:
    """Green, amber or red against the target; None without one."""
    if value is None or target is None:
        return None
    line = target if amber is None else amber
    if m.higher_is_better:
        return "green" if value >= target else "amber" if value >= line else "red"
    return "green" if value <= target else "amber" if value <= line else "red"


def _label(dim: str, key: Any) -> str:
    if key is None:
        return "No office" if dim == "office" else "Not recorded"
    text = str(key)
    if dim == "office":
        return OFFICE_TITLES.get(text, text)
    return (
        text.replace("_", " ").capitalize()
        if dim not in ("project", "holder", "category")
        else text
    )


async def _rows(
    conn: Conn,
    m: cat.Metric,
    *,
    period: Period | None,
    office: str | None,
    dim: str | None,
    grain: str | None,
    reader: Reader,
) -> dict[tuple[Any, Any], float]:
    """{(bucket, dim): value} of a count or median metric."""
    snapshot = m.kind == cat.SNAPSHOT
    rows = await repo.series(
        conn,
        m.key,
        start=None if snapshot or period is None else period.start,
        end=None if snapshot or period is None else period.end,
        office=office,
        dim=dim,
        grain=None if snapshot else grain,
        median=m.kind == cat.MEDIAN,
        scope=_scope(reader),
        user_id=reader.user_id,
    )
    return {(r["bucket"], r["dim"]): float(r["value"]) for r in rows if r["value"] is not None}


async def _live(m: cat.Metric) -> dict[tuple[Any, Any], float]:
    """The depth of each worker queue, read from the broker - its own Redis
    database (`CELERY_BROKER_URL`), not the application's."""
    import redis.asyncio as aioredis

    from cmp.core.config import settings

    out: dict[tuple[Any, Any], float] = {}
    client = aioredis.from_url(settings.celery_broker_url, socket_timeout=2)  # type: ignore[no-untyped-call]
    try:
        for q in QUEUES:
            out[(None, q)] = float(await client.llen(q))
    except Exception as exc:  # a health page must open with the broker down
        log.warning("analytics.queue_depth_unavailable", error=type(exc).__name__)
    finally:
        await client.aclose()
    return out


async def _values(
    conn: Conn,
    m: cat.Metric,
    *,
    period: Period | None,
    office: str | None,
    dim: str | None,
    grain: str | None,
    reader: Reader,
) -> tuple[dict[tuple[Any, Any], float | None], dict[tuple[Any, Any], float | None] | None]:
    """The metric's values, and - where it counts people - the counts a value
    is withheld by: its own, or for a rate the group under it."""
    if m.kind == cat.LIVE:
        values = await _live(m)
        if dim is None:
            return {(None, None): sum(v for v in values.values())}, None
        return dict(values), None
    if m.kind == cat.RATIO:
        assert m.numerator and m.denominator
        num_m, den_m = cat.metric(m.numerator), cat.metric(m.denominator)
        kw: dict[str, Any] = {
            "period": period,
            "office": office,
            "dim": dim,
            "grain": grain,
            "reader": reader,
        }
        num = await _rows(conn, num_m, **kw)
        den = await _rows(conn, den_m, **kw)
        out: dict[tuple[Any, Any], float | None] = {}
        for k, d in den.items():
            out[k] = (100.0 * num.get(k, 0.0) / d) if d else None
        basis: dict[tuple[Any, Any], float | None] | None = (
            dict(den) if (num_m.people or den_m.people) else None
        )
        return out, basis
    rows = dict(
        await _rows(conn, m, period=period, office=office, dim=dim, grain=grain, reader=reader)
    )
    return dict(rows), (dict(rows) if m.people else None)


def _total(values: dict[tuple[Any, Any], float | None], m: cat.Metric) -> float | None:
    if not values:
        return None if m.kind in (cat.RATIO, cat.MEDIAN) else 0.0
    if len(values) == 1:
        return next(iter(values.values()))
    if m.kind == cat.LIVE:
        return float(sum(v or 0 for v in values.values()))
    return next(iter(values.values()))


async def figures(
    conn: Conn,
    reader: Reader,
    *,
    keys: list[str] | None = None,
    section: str | None = None,
    period: Period,
    office: str | None = None,
    dim: str | None = None,
    compare: bool = True,
    trend: bool = True,
) -> dict[str, Any]:
    """The figures this reader asked for, each complete."""
    if section is not None and section not in cat.SECTIONS:
        raise NotFound("Section")
    if section is not None and reader.role not in cat.SECTIONS[section]:
        raise Forbidden("This section is not yours to read")
    allowed = cat.for_role(reader.role, section)
    if keys:
        unknown = [k for k in keys if k not in cat.METRICS]
        if unknown:
            raise NotFound("Metric")
        refused = [k for k in keys if reader.role not in cat.metric(k).audience]
        if refused:
            raise Forbidden("A metric asked for is not yours to read")
        allowed = [cat.metric(k) for k in keys]
    office = office_for(reader, office)
    if dim is not None and dim not in cat.DIMENSIONS:
        raise ValidationFailed("Unknown breakdown", field="dim")
    if dim == "office" and reader.role != Role.MANAGEMENT.value:
        raise Forbidden("Only management reads the offices side by side")
    threshold = int((await repo.setting(conn))["small_number_threshold"])
    targets = await repo.targets(conn)
    before = previous(period) if compare else None
    grain = grain_for(period) if trend else None

    def gone(basis: dict[tuple[Any, Any], float | None] | None, k: tuple[Any, Any]) -> bool:
        """Withheld: it counts people, and fewer than the threshold of them."""
        if basis is None or threshold <= 1:
            return False
        n = basis.get(k)
        return n is not None and 0 < n < threshold

    out = []
    for m in allowed:
        kw: dict[str, Any] = {"office": office, "reader": reader}
        values, basis = await _values(conn, m, period=period, dim=None, grain=None, **kw)
        value = _round(m.unit, _total(values, m))
        whole = next(iter(values), (None, None))
        suppressed = gone(basis, whole)
        prev_value: float | None = None
        prev_suppressed = False
        if before is not None and m.kind not in (cat.SNAPSHOT, cat.LIVE):
            prev, prev_basis = await _values(conn, m, period=before, dim=None, grain=None, **kw)
            prev_value = _round(m.unit, _total(prev, m))
            prev_suppressed = gone(prev_basis, next(iter(prev), (None, None)))
        line: list[dict[str, Any]] = []
        if grain and m.kind not in (cat.SNAPSHOT, cat.LIVE):
            series, series_basis = await _values(
                conn, m, period=period, dim=None, grain=grain, **kw
            )
            for k, v in sorted(series.items(), key=lambda kv: str(kv[0][0])):
                hid = gone(series_basis, k)
                v2 = _round(m.unit, v)
                line.append({"bucket": k[0], "value": None if hid else v2, "suppressed": hid})
        split: list[dict[str, Any]] = []
        if dim is not None and dim in m.dims:
            parts, parts_basis = await _values(conn, m, period=period, dim=dim, grain=None, **kw)
            for k, v in sorted(parts.items(), key=lambda kv: -(kv[1] or 0)):
                key = k[1]
                v2 = _round(m.unit, v)
                hid = gone(parts_basis, k)
                split.append(
                    {
                        "key": key,
                        "label": _label(dim, key),
                        "value": None if hid else v2,
                        "suppressed": hid,
                    }
                )
        target, amber = _target_of(m, targets)
        change = (
            None
            if value is None or prev_value is None or suppressed or prev_suppressed
            else round(value - prev_value, 1)
        )
        out.append(
            {
                "key": m.key,
                "title": m.title,
                "definition": m.definition,
                "unit": m.unit,
                "section": m.section,
                "group": m.group,
                "kind": m.kind,
                "dims": list(m.dims),
                "value": None if suppressed else value,
                "suppressed": suppressed,
                "previous": None if prev_suppressed else prev_value,
                "previous_suppressed": prev_suppressed,
                "change": change,
                "target": target,
                "amber": amber,
                "higher_is_better": m.higher_is_better,
                "status": None if suppressed else status(m, value, target, amber),
                "series": line,
                "breakdown": split,
            }
        )
    return {
        "period": period.as_dict(),
        "previous": before.as_dict() if before else None,
        "office": office,
        "dim": dim,
        "grain": grain,
        "threshold": threshold,
        "metrics": out,
    }


def _target_of(m: cat.Metric, stored: dict[str, Row]) -> tuple[float | None, float | None]:
    row = stored.get(m.key)
    if row is not None:
        return float(row["target"]), (float(row["amber"]) if row["amber"] is not None else None)
    return m.target, m.amber


# ---------------------------------------------------------- the catalogue


def catalogue(reader: Reader) -> dict[str, Any]:
    """What this reader may see: sections, metrics, breakdowns, reports, periods."""
    from cmp.domain.analytics.periods import CADENCES, PRESETS

    return {
        "role": reader.role,
        "office": reader.office,
        "may_choose_office": reader.role == Role.MANAGEMENT.value,
        "sections": cat.sections_for(reader.role),
        "metrics": [
            {
                "key": m.key,
                "title": m.title,
                "definition": m.definition,
                "unit": m.unit,
                "section": m.section,
                "group": m.group,
                "kind": m.kind,
                "dims": list(m.dims),
                "people": m.people,
            }
            for m in cat.for_role(reader.role)
        ],
        "dimensions": [{"key": k, "label": v} for k, v in cat.DIMENSIONS.items()],
        "periods": [{"key": k, "label": v} for k, v in PRESETS.items()],
        "cadences": [{"key": k, "label": v} for k, v in CADENCES.items()],
        "reports": [
            {
                "key": r.key,
                "title": r.title,
                "description": r.description,
                "formats": list(r.formats),
                "schedulable": r.schedulable,
                "recipient_roles": sorted(r.audience),
            }
            for r in cat.reports_for(reader.role)
        ],
        "audit_reports": (
            [
                {"key": a.key, "title": a.title, "description": a.description}
                for a in cat.AUDIT_REPORTS.values()
            ]
            if reader.role in cat.AUDIT_READERS
            else []
        ),
    }


# ------------------------------------------------- targets and the threshold


async def settings_view(conn: Conn) -> dict[str, Any]:
    stored = await repo.targets(conn)
    setting = await repo.setting(conn)
    return {
        "small_number_threshold": int(setting["small_number_threshold"]),
        "updated_at": setting["updated_at"],
        "updated_by_name": setting["updated_by_name"],
        "targets": [
            {
                "key": m.key,
                "title": m.title,
                "unit": m.unit,
                "section": m.section,
                "group": m.group,
                "higher_is_better": m.higher_is_better,
                "default_target": m.target,
                "default_amber": m.amber,
                "target": _target_of(m, stored)[0],
                "amber": _target_of(m, stored)[1],
                "customised": m.key in stored,
                "updated_at": stored[m.key]["updated_at"] if m.key in stored else None,
                "updated_by_name": stored[m.key]["updated_by_name"] if m.key in stored else None,
            }
            for m in cat.CATALOGUE
            if m.unit != "count" or m.has_target
        ],
    }


async def set_target(
    conn: Conn, key: str, *, target: float | None, amber: float | None, actor_id: int
) -> dict[str, Any]:
    """A metric's target and amber line; `target` None goes back to the default."""
    if key not in cat.METRICS:
        raise NotFound("Metric")
    m = cat.metric(key)
    if target is None:
        changed = await repo.reset_target(conn, key)
        detail: dict[str, Any] = {"metric": key, "reset": True}
    else:
        if m.unit == "percent" and not (0 <= target <= 100):
            raise ValidationFailed("A percentage target is between 0 and 100", field="target")
        if target < 0 or (amber is not None and amber < 0):
            raise ValidationFailed("A target cannot be negative", field="target")
        if amber is not None and (
            (m.higher_is_better and amber > target) or (not m.higher_is_better and amber < target)
        ):
            raise ValidationFailed(
                "The amber line is on the far side of the target: below it where higher is "
                "better, above it where lower is",
                field="amber",
            )
        await repo.set_target(conn, key, target=target, amber=amber, actor_id=actor_id)
        changed = True
        detail = {"metric": key, "target": target, "amber": amber}
    if changed:
        await audit.record(
            conn,
            event=Event.ANALYTICS_TARGET_CHANGED,
            entity_type="analytics_target",
            entity_id=0,
            actor_user_id=actor_id,
            detail=detail,
        )
        await _told(conn, f"the target of '{m.title}'", actor_id)
    return await settings_view(conn)


async def set_threshold(conn: Conn, threshold: int, *, actor_id: int) -> dict[str, Any]:
    if not 1 <= threshold <= 100:
        raise ValidationFailed("The threshold is between 1 and 100", field="small_number_threshold")
    before = int((await repo.setting(conn))["small_number_threshold"])
    if before != threshold:
        await repo.set_threshold(conn, threshold, actor_id=actor_id)
        await audit.record(
            conn,
            event=Event.ANALYTICS_SETTING_CHANGED,
            entity_type="analytics_setting",
            entity_id=1,
            actor_user_id=actor_id,
            detail={"small_number_threshold": threshold, "was": before},
        )
        await _told(conn, "the small-number threshold of the analytics", actor_id)
    return await settings_view(conn)


async def _told(conn: Conn, setting: str, actor_id: int) -> None:
    from cmp.domain import alerts

    await alerts.setting_changed(conn, setting=setting, actor_id=actor_id)


# --------------------------------------------------------- audit reports


async def audit_report(
    conn: Conn,
    reader: Reader,
    key: str,
    *,
    period: Period,
    page: PageRequest,
) -> dict[str, Any]:
    """One ready-made audit report: its rows, a page at a time, and its shape."""
    from cmp.db.repositories import audit as audit_repo

    if reader.role not in cat.AUDIT_READERS:
        raise Forbidden("Audit reports are not yours to read")
    spec = cat.AUDIT_REPORTS.get(key)
    if spec is None:
        raise NotFound("Audit report")
    filters = audit_repo.AuditFilters(
        event_types=spec.events,
        date_from=period.start,
        date_to=period.end,
        office=reader.office,
    )
    items, next_cursor, total = await audit_repo.search(conn, page, filters)
    shape = await audit_repo.summary(conn, filters, days=min(period.days, 400))
    return {
        "key": spec.key,
        "title": spec.title,
        "description": spec.description,
        "events": list(spec.events),
        "period": period.as_dict(),
        "items": items,
        "next_cursor": next_cursor,
        "total": total,
        "summary": shape,
    }


async def inventory(conn: Conn, reader: Reader, *, office: str | None) -> dict[str, Any]:
    if reader.role not in cat.SECTIONS["inventory"]:
        raise Forbidden("The record of processing is not yours to read")
    return await repo.inventory(conn, office=office_for(reader, office))


def now_utc() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)
