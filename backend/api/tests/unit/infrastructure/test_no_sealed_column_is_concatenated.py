"""No SQL in the repositories glues a sealed column to other text.

`SE::...` concatenated with a reference or a project name is a value nobody
can open: the portal's walker sees a string that starts with the prefix but
is not an envelope, and the key service refuses the batch it is in - which
is how a notification feed once left every name on the page sealed. A label
that needs a person's name beside other words returns the pieces
(`label_parts`) and the reader joins them after opening.

Static, over the SQL text: a `||` on either side of a sealed column's name,
within the same statement. Coarse on purpose - a false positive costs a
comment here, a false negative costs a page.
"""

from __future__ import annotations

import re
from pathlib import Path

from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS

REPOSITORIES = Path(__file__).resolve().parents[3] / "src" / "cmp" / "db" / "repositories"

#: Sealed column names that are also plain columns elsewhere and would only
#: produce noise: `name` is a purpose's, a queue's, a source's.
AMBIGUOUS = {"name", "reason", "body", "contact"}

SEALED = sorted(
    {c for cols in ENCRYPTED_FIELDS.values() for c in cols if c not in AMBIGUOUS},
    key=len,
    reverse=True,
)

#: `alias.column || ...` or `... || alias.column`, with optional whitespace,
#: where the column is a sealed one. `coalesce(' — ' || s.full_name, '')`
#: matches through the second alternative.
PATTERN = re.compile(
    r"(?:\b\w+\.)?(?P<col>" + "|".join(map(re.escape, SEALED)) + r")\b\s*\|\||"
    r"\|\|\s*(?:\w+\.)?(?P<col2>" + "|".join(map(re.escape, SEALED)) + r")\b"
)


def test_no_repository_sql_concatenates_a_sealed_column() -> None:
    offenders: list[str] = []
    for path in sorted(REPOSITORIES.glob("*.py")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if PATTERN.search(line):
                offenders.append(f"{path.name}:{number}: {line.strip()}")
    assert not offenders, "sealed columns joined to text in SQL:\n" + "\n".join(offenders)
