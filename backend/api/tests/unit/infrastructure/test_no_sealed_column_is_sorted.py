"""No SQL orders rows by a sealed column.

`ORDER BY u.full_name` on a sealed column orders the envelopes - an order
nobody chose, so a list of people reads as shuffled. Until 2026-10-05 the
staff pickers and the project export did exactly that. The query orders by
something stable (an id, a time) and the reader sorts once the names are
open: `exchange.service._in_name_order`, and `inNameOrder` in the portals.

Static, over the SQL text in `src/`: a sealed column's name after `ORDER BY`
on the same line, including inside `array_agg(... ORDER BY ...)`.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.unit.infrastructure.test_no_sealed_column_is_concatenated import SEALED

SOURCE = Path(__file__).resolve().parents[3] / "src" / "cmp"

PATTERN = re.compile(
    r"ORDER\s+BY\b[^;\"]*?(?:\b\w+\.)?\b(?P<col>" + "|".join(map(re.escape, SEALED)) + r")\b(?!_)",
    re.IGNORECASE,
)


def test_no_sql_sorts_by_a_sealed_column() -> None:
    offenders: list[str] = []
    for path in sorted(SOURCE.rglob("*.py")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if PATTERN.search(line):
                offenders.append(f"{path.relative_to(SOURCE)}:{number}: {line.strip()}")
    assert not offenders, "sealed columns sorted in SQL:\n" + "\n".join(offenders)


def test_the_check_would_catch_the_old_query() -> None:
    assert PATTERN.search("           ORDER BY u.role, u.full_name")
    assert PATTERN.search("ORDER BY u.full_name, ca.affirmative_action_at")
    assert not PATTERN.search("ORDER BY u.id, ca.affirmative_action_at")
    assert not PATTERN.search("ORDER BY full_name_hash")
