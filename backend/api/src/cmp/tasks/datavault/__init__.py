"""The platform's own call to DataVault (0070): after holders were found for
a rights request and a DCO Admin is among them. On the `default` queue - it is
nobody's sign-in code."""

from cmp.tasks.datavault.checks import check_request

__all__ = ["check_request"]
