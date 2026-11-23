"""Making a report, and running the schedules (ADR 0045)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from celery import shared_task

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.logging import get_logger
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.db.redis import close_redis, open_redis

log = get_logger("cmp.tasks.reports")


def _run(coro: Any) -> Any:
    """One async unit of work in a synchronous task: fresh pools per task,
    as the maintenance tasks do, because a pool shared across forked workers
    hands one socket to two processes."""
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def wrapper() -> Any:
        await open_pool()
        await open_redis()
        try:
            return await coro()
        finally:
            await close_redis()
            await close_pool()

    return asyncio.run(wrapper())


@shared_task(name="cmp.reports.generate_report", acks_late=True)
def generate_report(report_uuid: str) -> dict[str, Any]:
    """Make one report. Redelivered, it finds the report made and stops."""
    from cmp.domain.analytics import reports

    async def work() -> dict[str, Any]:
        async with transaction() as conn:
            row = await reports.make(conn, report_uuid)
        return {"status": (row or {}).get("status")}

    return _run(work)


@shared_task(name="cmp.reports.run_schedules", acks_late=True)
def run_report_schedules() -> dict[str, Any]:
    """Every due schedule: its report, made now, then mailed."""
    from cmp.domain.analytics import reports
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.updates import send_report_ready

    async def work() -> dict[str, Any]:
        async with ratelimit.lock("report_schedules", ttl_s=1800) as acquired:
            if not acquired:
                return {"skipped": True}
            now = datetime.now(UTC)
            async with transaction() as conn:
                due = await reports.run_due(conn, now)
            mailed = 0
            for report_uuid, emails, period in due:
                async with transaction() as conn:
                    row = await reports.make(conn, report_uuid)
                if not row or row.get("status") != "ready":
                    continue
                for email in emails:
                    dispatch_optional(
                        send_report_ready,
                        email,
                        str(row["title"]),
                        period,
                        str(row["file_ref"]),
                        str(row["format"]),
                    )
                    mailed += 1
            log.info("reports.schedules_run", reports=len(due), mailed=mailed)
            return {"reports": len(due), "mailed": mailed}

    return _run(work)
