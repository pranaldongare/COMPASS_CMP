"""One code, one success, however many requests carry it at once.

The verifier used to read the digest with GET, compare in Python, and delete
in a later pipeline. Two concurrent requests with the same correct code could
both read before either deleted, and both were told yes; the September 2026
review reproduced exactly that. The check, the delete and the attempt count
are now one server-side script, and this test races it for real.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.core.errors import RateLimited
from cmp.core.security import new_token

pytestmark = pytest.mark.integration


class TestAtomicVerify:
    async def test_of_many_racing_verifications_exactly_one_succeeds(self, redis_conn: Any) -> None:
        identity = f"race-{new_token(6)}"
        issued = await otp.issue(otp.Scope.SUBJECT_LOGIN, identity)

        results = await asyncio.gather(
            *[otp.verify(otp.Scope.SUBJECT_LOGIN, identity, issued.code) for _ in range(8)]
        )
        assert results.count(True) == 1, results
        # And the code is gone: a ninth try with the right digits finds nothing.
        assert await otp.verify(otp.Scope.SUBJECT_LOGIN, identity, issued.code) is False

    async def test_consume_false_checks_without_spending(self, redis_conn: Any) -> None:
        identity = f"peek-{new_token(6)}"
        issued = await otp.issue(otp.Scope.SUBJECT_REGISTER, identity)

        assert await otp.verify(otp.Scope.SUBJECT_REGISTER, identity, issued.code, consume=False)
        assert await otp.verify(otp.Scope.SUBJECT_REGISTER, identity, issued.code, consume=False)
        assert await otp.verify(otp.Scope.SUBJECT_REGISTER, identity, issued.code)
        assert await otp.verify(otp.Scope.SUBJECT_REGISTER, identity, issued.code) is False

    async def test_the_attempt_budget_discards_the_code(self, redis_conn: Any) -> None:
        identity = f"guess-{new_token(6)}"
        issued = await otp.issue(otp.Scope.SUBJECT_LOGIN, identity)
        wrong = "000000" if issued.code != "000000" else "111111"

        for _ in range(4):
            assert await otp.verify(otp.Scope.SUBJECT_LOGIN, identity, wrong) is False
        with pytest.raises(RateLimited):
            await otp.verify(otp.Scope.SUBJECT_LOGIN, identity, wrong)
        # The right code no longer works either: the budget discarded it.
        assert await otp.verify(otp.Scope.SUBJECT_LOGIN, identity, issued.code) is False

    async def test_a_code_from_another_scope_does_not_verify(self, redis_conn: Any) -> None:
        identity = f"scope-{new_token(6)}"
        issued = await otp.issue(otp.Scope.CONSENT_LINK, identity)
        assert await otp.verify(otp.Scope.SUBJECT_LOGIN, identity, issued.code) is False
        assert await otp.verify(otp.Scope.CONSENT_LINK, identity, issued.code) is True
