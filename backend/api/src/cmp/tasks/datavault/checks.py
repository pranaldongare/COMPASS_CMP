"""Ask DataVault what it holds of a request's person, unattended (0070).

Queued when holders are found and one of them is a project's DCO Admin. The
task decides nothing the request page's button does not: the same `prepare`,
`ask`, `store`, with nobody as the actor. It is tried again a few times when
DataVault does not answer, and each attempt is on the request's trail; a
request that has meanwhile been closed, or a DataVault switched off, ends it
quietly.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.logging import get_logger
from cmp.db.pool import across_offices, connection, transaction
from cmp.tasks.maintenance.rights import _run

log = get_logger("cmp.tasks.datavault")

#: Attempts after the first, and the wait before each.
RETRIES = 3
RETRY_AFTER_S = 120


@shared_task(
    name="cmp.datavault.check_request",
    bind=True,
    acks_late=True,
    max_retries=RETRIES,
    default_retry_delay=RETRY_AFTER_S,
)
def check_request(self: Any, request_id: int) -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        from cmp.core.context import RequestContext, use_context
        from cmp.core.errors import CmpError
        from cmp.db.repositories import rights as rights_repo
        from cmp.domain.datavault import checks

        with use_context(RequestContext(request_id=f"task:datavault_check:{request_id}")):
            async with connection() as conn, across_offices(conn):
                row = await rights_repo.by_id(conn, request_id)
                if row is None:
                    return {"skipped": "no such request"}
                try:
                    what = await checks.prepare(conn, row, role=None)
                except CmpError as refused:
                    return {"skipped": refused.code}
            answer = await checks.ask(what)
            async with transaction() as conn, across_offices(conn):
                await checks.store(conn, what, answer, actor_id=None)
        if isinstance(answer, str):
            return {"failed": answer}
        return {"assets": len(answer)}

    result: dict[str, Any] = _run(work)
    failed = result.get("failed")
    # A refused key or an unknown address will not mend by itself; a timeout
    # or an upstream fault may.
    passing = failed in ("timeout", "unreachable") or str(failed).startswith("status_5")
    if passing and self.request.retries < RETRIES:
        raise self.retry()
    log.info("datavault.checked", rights_request=request_id, **result)
    return result
