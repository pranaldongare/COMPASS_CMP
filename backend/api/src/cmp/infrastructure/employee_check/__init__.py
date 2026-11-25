"""The organisation's VerifyEmail call (ADR 0046)."""

from cmp.infrastructure.employee_check.client import (
    EmployeeCheckFailed,
    Verdict,
    read,
    verify_email,
)

__all__ = ["EmployeeCheckFailed", "Verdict", "read", "verify_email"]
