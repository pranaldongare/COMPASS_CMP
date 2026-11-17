"""Every five minutes: the breach duties about to fall due, or overdue (2026-10-08).

The organisation's board is owed word within thirty minutes and CERT-In
within six hours, so a daily pass is too slow. This one reads the dated duties
of every open breach and queues an email to every DPO for each duty entering
its last sixth, and again once it is overdue - each once, remembered in Redis
(`cmp.domain.alerts.breach_duties`). Nothing here changes a duty.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.logging import get_logger
from cmp.db.pool import transaction
from cmp.tasks.maintenance.rights import _run

log = get_logger("cmp.tasks.maintenance")


@shared_task(name="cmp.maintenance.alert_breach_duties", acks_late=True)
def alert_breach_duties() -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        async with ratelimit.lock("alert_breach_duties", ttl_s=240) as acquired:
            if not acquired:
                log.info("maintenance.skipped", task="alert_breach_duties")
                return {"skipped": True}

            from cmp.core.context import RequestContext, use_context
            from cmp.domain import alerts

            with use_context(RequestContext(request_id="beat:alert_breach_duties")):
                async with transaction() as conn:
                    queued = await alerts.breach_duties(conn)
            log.info("maintenance.breach_duties_alerted", queued=queued)
            return {"queued": queued}

    result: dict[str, Any] = _run(work)
    return result


@shared_task(name="cmp.maintenance.escalate_incident_reports", acks_late=True)
def escalate_incident_reports() -> dict[str, Any]:
    """Every minute: a report from the public link that neither office has
    taken up within half an hour is mailed to the escalation list, once
    (0073). `cmp.domain.breach.intake.escalate_waiting`."""

    async def work() -> dict[str, Any]:
        async with ratelimit.lock("escalate_incident_reports", ttl_s=50) as acquired:
            if not acquired:
                log.info("maintenance.skipped", task="escalate_incident_reports")
                return {"skipped": True}

            from cmp.core.context import RequestContext, use_context
            from cmp.domain.breach import intake

            with use_context(RequestContext(request_id="beat:escalate_incident_reports")):
                async with transaction() as conn:
                    escalated = await intake.escalate_waiting(conn)
            if escalated:
                log.info("maintenance.incident_reports_escalated", escalated=escalated)
            return {"escalated": escalated}

    result: dict[str, Any] = _run(work)
    return result
