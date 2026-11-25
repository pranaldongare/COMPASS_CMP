"""Asking VerifyEmail about a person who has just signed in to the portal
(ADR 0046). On the `default` queue: nobody's sign-in waits for it."""

from cmp.tasks.employees.checks import check_account

__all__ = ["check_account"]
