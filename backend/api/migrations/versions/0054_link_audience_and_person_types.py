"""Person types from the category, for the people an HR link brings (ADR 0034).

An HR activity reaches people who are not employees - a candidate whose
background is being verified, a visitor at a wellness camp - and the person
type written on an account that signs up through such a link should say so.
`person_type` gains `candidate` and `visitor`, and a category names the
type its link's new accounts default to:

  | Column | Holds |
  |---|---|
  | `hr_category.default_person_type` | the person type an account created through one of the category's activities' links is given; NULL leaves today's `external` |

A hint written on the account, never a permission (`PersonType` is never
consulted for one). An employee arriving by SSO is always `employee`.

`consent_link.audience_mode`, which the plan put here, arrived in 0053 (open
point F-2). `auth_user.sso_subject` is not added: nothing reads it, and an
employee is matched on the employee ID (open point F-11).

`rights_holder_source` gains `activity_processor`, the third way a rights
request's holder is found - an HR activity's category processors - here
rather than in 0055 (open point F-23).

The enum values are added in autocommit blocks, before the rest, and are never
removed on downgrade, as 0041 and 0051 did.

Revision ID: 0054
Revises: 0053
"""

from __future__ import annotations

from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

NEW_TYPES = (
    "ALTER TYPE person_type ADD VALUE IF NOT EXISTS 'candidate'",
    "ALTER TYPE person_type ADD VALUE IF NOT EXISTS 'visitor'",
    # A rights request's holder derived from an HR activity's category
    # processors (increment 6). Here rather than in 0055 so that increment
    # needs no migration of its own (open point F-23).
    "ALTER TYPE rights_holder_source ADD VALUE IF NOT EXISTS 'activity_processor'",
)

UPGRADE = """
ALTER TABLE hr_category ADD COLUMN default_person_type person_type;
COMMENT ON COLUMN hr_category.default_person_type IS
  'The person type of an account created through one of the category''s links; NULL is external';
"""

DOWNGRADE = """
ALTER TABLE hr_category DROP COLUMN default_person_type;
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for statement in NEW_TYPES:
            op.execute(statement)
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(DOWNGRADE)
