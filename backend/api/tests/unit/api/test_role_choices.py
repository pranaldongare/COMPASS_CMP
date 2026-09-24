"""Every role the platform has can be given to an account.

The role drop-down on "Provision an account" is built from `/meta/enums`, whose
list had five roles when the platform has seven: DCO Admin and R&D Collection
Owner could not be provisioned from the console at all.
"""

from __future__ import annotations

from cmp.api.routers.v1.system import _ENUMS, _LABELS
from cmp.core.permissions import Role


def test_the_role_list_is_every_role() -> None:
    assert set(_ENUMS["user_role"]) == {r.value for r in Role}


def test_every_role_has_a_label() -> None:
    assert all(role in _LABELS for role in _ENUMS["user_role"])
