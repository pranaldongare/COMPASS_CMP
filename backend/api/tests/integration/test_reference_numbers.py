"""A reference outlives four digits (0062).

`INC-`, `BR-` and `TPL-` numbers are padded to four digits. `lpad` alone also
cuts a longer value down to four, so 10012 read 1001 and the nine numbers after
it collided on the unique reference: an office could not log an incident. The
sequences only go forward, and the public link draws on one.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.db.sql import fetch_val

pytestmark = pytest.mark.integration


async def _numbers(conn: Any, start: int, count: int) -> list[str]:
    await conn.execute(f"CREATE TEMP SEQUENCE reference_under_test START {start}")
    return [
        str(await fetch_val(conn, "SELECT cmp_next_number('reference_under_test')"))
        for _ in range(count)
    ]


async def test_a_small_number_is_padded(conn: Any) -> None:
    assert await _numbers(conn, 7, 2) == ["0007", "0008"]


async def test_a_long_number_keeps_every_digit(conn: Any) -> None:
    assert await _numbers(conn, 9999, 3) == ["9999", "10000", "10001"]


async def test_a_template_code_from_the_default_keeps_every_digit(conn: Any) -> None:
    default = await fetch_val(
        conn,
        """SELECT column_default FROM information_schema.columns
            WHERE table_name = 'notice_template' AND column_name = 'template_code'""",
    )
    assert "cmp_next_number" in str(default) and "lpad" not in str(default)
