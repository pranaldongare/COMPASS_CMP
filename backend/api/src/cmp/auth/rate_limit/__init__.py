"""Rate limiting, account lockout and distributed locks.

Redis-backed, because all three have to hold across processes. A per-process
counter is not a rate limit when there are four workers.

Lockout is keyed on the *account*, not the address: an attacker rotates
addresses, and a legitimate user behind a corporate NAT should not be locked out
because a colleague mistyped their password. The address has a budget of its own
- of failures, across accounts - against one address guessing at many.
"""

from cmp.auth.rate_limit.service import (
    account_key,
    check,
    clear_login_failures,
    enforce,
    is_locked_out,
    lock,
    record_address_failure,
    record_login_failure,
    refuse_spent_address,
)

__all__ = [
    "account_key",
    "check",
    "clear_login_failures",
    "enforce",
    "is_locked_out",
    "lock",
    "record_address_failure",
    "record_login_failure",
    "refuse_spent_address",
]
