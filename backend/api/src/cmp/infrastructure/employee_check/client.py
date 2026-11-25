"""The organisation's VerifyEmail call (2026-11-25, ADR 0046).

Is this address an active employee's?

    POST {base}/VerifyEmail
    {"MySingleID": "someone@company.example"}

    200 {"MySingleID": "someone@company.example", "IsActive": true, "Status": true}

`Status` says the organisation knows the address; `IsActive` that the person
is employed now. Both true is an active employee; anything else that reads
cleanly is not (left, or not known).

Called from inside the network only - by the API at a console sign-in and by
the worker after a portal sign-in - as DataVault is (ADR 0038). Nothing here
crosses the relay: a portal request reaches the API through the bridge, SQS
and the collector as it always has (ADR 0035), and the API makes this call on
its own side.

The rules of `cmp.infrastructure.external`, as for DataVault: an explicit
timeout, no redirect followed, and no address, key, email or body in a log
line or an error. A failure is a short code (`timeout`, `unreachable`,
`status_503`, `unreadable`, `mismatch`) - all the trail keeps.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import httpx

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.infrastructure.employee_check")


class Verdict(StrEnum):
    ACTIVE = "active"
    #: Known and not employed now, or not known at all.
    INACTIVE = "inactive"


class EmployeeCheckFailed(Exception):
    """No answer to rely on. `code` is safe to show and to keep."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def read(body: Any, email: str) -> Verdict:
    """The verdict in an answer, or `EmployeeCheckFailed`.

    Read strictly: both flags must be JSON booleans, and the address echoed
    must be the one asked about - an answer about somebody else is not an
    answer about this person (`mismatch`)."""
    if not isinstance(body, dict):
        raise EmployeeCheckFailed("unreadable")
    active, known = body.get("IsActive"), body.get("Status")
    if not isinstance(active, bool) or not isinstance(known, bool):
        raise EmployeeCheckFailed("unreadable")
    echoed = body.get("MySingleID")
    if echoed is not None and (
        not isinstance(echoed, str) or echoed.strip().lower() != email.strip().lower()
    ):
        raise EmployeeCheckFailed("mismatch")
    return Verdict.ACTIVE if active and known else Verdict.INACTIVE


async def verify_email(
    *,
    base_url: str,
    email: str,
    api_key: str | None,
    api_key_header: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Verdict:
    """Ask once. No retry: a sign-in is not held up for a second try."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers[api_key_header] = api_key
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.external_http_timeout_s),
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/VerifyEmail",
                json={"MySingleID": email},
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        log.warning("employee_check.timeout")
        raise EmployeeCheckFailed("timeout") from exc
    except httpx.HTTPError as exc:
        log.warning("employee_check.unreachable", error=type(exc).__name__)
        raise EmployeeCheckFailed("unreachable") from exc
    if response.status_code != 200:
        log.warning("employee_check.status", status=response.status_code)
        raise EmployeeCheckFailed(f"status_{response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        log.warning("employee_check.unreadable")
        raise EmployeeCheckFailed("unreadable") from exc
    return read(body, email)
