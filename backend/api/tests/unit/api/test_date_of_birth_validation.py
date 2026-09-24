"""One rule for a plausible date of birth, on every body that takes one.

The database checked it until 0028 sealed the column; since then the API is the
only place it can be checked, and `PATCH /me` never did. Each body that accepts
a date of birth is exercised here, so a new one that forgets is visible.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from cmp.api.routers.public.consent import RegisterBody as LinkRegisterBody
from cmp.api.routers.v1.auth import RegisterBody as SignUpBody
from cmp.api.routers.v1.me import UpdateMe

TODAY = datetime.now(UTC).date()
BASE = {"full_name": "Asha Menon", "mobile": "+919876500001"}


def _bodies(dob: date) -> list[tuple[type, dict[str, object]]]:
    return [
        (SignUpBody, {**BASE, "dob": dob}),
        (LinkRegisterBody, {**BASE, "dob": dob}),
        (UpdateMe, {"dob": dob}),
    ]


@pytest.mark.parametrize("dob", [TODAY, TODAY + timedelta(days=1), date(1899, 12, 31)])
def test_an_implausible_date_is_refused_by_every_body(dob: date) -> None:
    for model, body in _bodies(dob):
        with pytest.raises(ValidationError):
            model.model_validate(body)


def test_a_plausible_date_is_accepted_by_every_body() -> None:
    for model, body in _bodies(date(1990, 5, 17)):
        assert model.model_validate(body).dob == date(1990, 5, 17)


def test_the_link_registration_requires_one() -> None:
    with pytest.raises(ValidationError):
        LinkRegisterBody.model_validate(BASE)
