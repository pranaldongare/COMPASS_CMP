"""Who someone is allowed to be.

`Role` itself lives in `cmp.core.permissions` — it is vocabulary, it depends on
nothing, and half the codebase needs it. This module is the part that has
opinions: which roles are staff, which are privileged, and which need a second
factor.

The distinction that matters most in this file is the one the DPDP Act cares
about: **role is authorisation, person type is identity.** A DPO who becomes an
ex-employee keeps her permissions until somebody changes her role. Coupling the
two would mean an HR record silently revoking access — which sounds prudent
until it happens to the only person who can publish a notice.
"""

from __future__ import annotations

from cmp.core.permissions import Role

#: Everyone who works for the fiduciary. Excludes the data subject, who is not
#: staff and whose entire surface is `/me`.
#:
#: Derived rather than listed. The list this replaced named four roles and was
#: never updated when the DCO Admin and the RCO arrived, so `is_staff()` said
#: they were not - harmlessly, because the route guards derive their own list,
#: but a second definition that disagrees with the first is a bug waiting for a
#: caller.
STAFF_ROLES: frozenset[Role] = frozenset(r for r in Role if r is not Role.DATA_SUBJECT)

#: Roles that can see across every project, or provision accounts. Not because
#: they are more trusted, but because a compromise of either is unbounded. They
#: were the first two to get a second factor; every staff role has one now, and
#: the set stays because it still answers other questions.
PRIVILEGED_ROLES: frozenset[Role] = frozenset({Role.DPO, Role.ADMIN})

#: Roles that may act on behalf of the organisation in the consent record. A
#: data subject acts for herself; these act for the fiduciary.
FIDUCIARY_ROLES: frozenset[Role] = frozenset({Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO})


def is_staff(role: Role | str) -> bool:
    try:
        return Role(role) in STAFF_ROLES
    except ValueError:
        return False


def is_privileged(role: Role | str) -> bool:
    try:
        return Role(role) in PRIVILEGED_ROLES
    except ValueError:
        return False


def requires_mfa(role: Role | str, *, configured: tuple[str, ...] | None = None) -> bool:
    """Whether this role must complete a second factor to hold a full session.

    Every staff role, by default: a password alone is one phished credential
    away from a signed consent record. Reads the configured list rather than
    `STAFF_ROLES` so a deployment can narrow it without editing code - and
    narrowing it is a decision that deployment answers for.
    """
    from cmp.core.config import settings

    allowed = configured if configured is not None else settings.mfa_required_roles
    return str(role) in allowed
