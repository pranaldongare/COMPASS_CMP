"""A reference outlives four digits (2026-11-06).

`INC-`, `BR-` and `TPL-` numbers come from a sequence, padded by
`lpad(n::text, 4, '0')`. `lpad` also cuts a longer value down to the width, so
from 10000 every number lost its last digit: 10012 read 1001, and the nine after
it collided on the unique reference. An office could not have logged an
incident. Nothing here is close to ten thousand of anything real, but a sequence
never goes back, whatever became of the row, and the public link now lets anybody
draw on the incidents' one.

`cmp_next_number` pads as before and keeps every digit. It is a function because
a column default may not hold the subquery that reads the number once. Numbers
already issued stand. `RR-` numbers have six digits and are left alone.

Revision ID: 0062
Revises: 0061
"""

from __future__ import annotations

from alembic import op

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE FUNCTION cmp_next_number(seq regclass, width int DEFAULT 4) RETURNS text
LANGUAGE sql VOLATILE AS $$
  SELECT lpad(n::text, greatest(width, length(n::text)), '0') FROM nextval(seq) AS n
$$;
COMMENT ON FUNCTION cmp_next_number(regclass, int) IS
  'The next value of a sequence, padded with zeros to at least the width, never cut to it';
ALTER TABLE notice_template ALTER COLUMN template_code
  SET DEFAULT 'TPL-' || cmp_next_number('notice_template_code_seq');
"""

DOWNGRADE = """
ALTER TABLE notice_template ALTER COLUMN template_code
  SET DEFAULT 'TPL-' || lpad(nextval('notice_template_code_seq')::text, 4, '0');
DROP FUNCTION cmp_next_number(regclass, int);
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
