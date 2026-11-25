"""Is the person who just signed in to the portal an active employee? (ADR 0046)

Queued when a portal sign-in code is entered. The answer is kept on the account
and changes nothing about the sign-in, which has already happened: a former
employee is still a data principal (the portal fails open). An employee-only
link reads the answer when the person next follows one.

No retry: the next sign-in asks again, and a failure leaves the account's
status unknown rather than stale.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.logging import get_logger
from cmp.db.pool import connection, transaction
from cmp.tasks.maintenance.rights import _run

log = get_logger("cmp.tasks.employees")


@shared_task(name="cmp.employees.check_account", acks_late=True)
def check_account(user_uuid: str) -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        from cmp.core.context import RequestContext, use_context
        from cmp.domain.employees import check

        with use_context(RequestContext(request_id="task:employee_check")):
            async with connection() as conn:
                found = await check.portal_subject(conn, user_uuid)
            if found is None:
                return {"skipped": "not asked"}
            user_id, email, link = found
            answer = await check.ask(link, email)
            async with transaction() as conn:
                await check.record(conn, user_id=user_id, flow=check.PORTAL, answer=answer)
        return {"result": answer.result, "failure": answer.code}

    result: dict[str, Any] = _run(work)
    return result
