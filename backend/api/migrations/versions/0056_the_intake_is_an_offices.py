"""The shared intake is seen by an office's session, not by one that names none.

0051 wrote `rights_request`'s policy as "all, or no office, or mine": a
request in the shared intake (`office_id IS NULL`) was visible to every
connection, including one whose `app.office` is unset, empty or names no
office - the connection that bypassed the pool, or the bug that cleared the
setting, which the policies are there to leave reading nothing. Until 0055
routed requests no row had no office, so nothing showed it; the first
request left in the intake did (`test_office_isolation`, "saying nothing
reads nothing").

The rule now: all; or no office, *for a session of an office*; or mine. The
children of `rights_request` are policed through it and follow.

Revision ID: 0056
Revises: 0055
"""

from __future__ import annotations

from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

_ALL = "current_setting('app.office', true) = 'all'"
_MINE = (
    "(SELECT o.office_id FROM office o WHERE o.office_code = current_setting('app.office', true))"
)

_NOW = f"{_ALL} OR (office_id IS NULL AND {_MINE} IS NOT NULL) OR office_id = {_MINE}"
_BEFORE = f"{_ALL} OR office_id IS NULL OR office_id = {_MINE}"


def _policy(rule: str) -> str:
    return f"""
DROP POLICY IF EXISTS office_isolation ON rights_request;
CREATE POLICY office_isolation ON rights_request USING ({rule}) WITH CHECK ({rule});
"""


def upgrade() -> None:
    op.execute(_policy(_NOW))


def downgrade() -> None:
    op.execute(_policy(_BEFORE))
