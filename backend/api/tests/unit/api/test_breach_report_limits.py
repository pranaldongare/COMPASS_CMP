"""What the finalise window and the mandatory mark may send (0064).

A body is refused before it reaches the service: too many addresses, a key
nobody declared, a mark that is not yes or no.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from cmp.api.routers.v1.breach_settings import BoardRecipientMandatoryIn
from cmp.api.routers.v1.breaches import BreachDocumentFinaliseIn


def test_a_body_names_the_entries_and_the_extras_default_to_none() -> None:
    chosen = uuid4()
    body = BreachDocumentFinaliseIn.model_validate({"recipients": [str(chosen)]})
    assert body.recipients == [chosen] and body.extra == []


def test_the_entries_must_be_named_even_if_none_are_chosen() -> None:
    with pytest.raises(ValidationError):
        BreachDocumentFinaliseIn.model_validate({"extra": []})


def test_two_hundred_entries_and_no_more() -> None:
    BreachDocumentFinaliseIn.model_validate({"recipients": [str(uuid4()) for _ in range(200)]})
    with pytest.raises(ValidationError):
        BreachDocumentFinaliseIn.model_validate({"recipients": [str(uuid4()) for _ in range(201)]})


def test_twenty_extras_and_no_more() -> None:
    extra = [{"email": f"a{i}@elsewhere.org"} for i in range(21)]
    BreachDocumentFinaliseIn.model_validate({"recipients": [], "extra": extra[:20]})
    with pytest.raises(ValidationError):
        BreachDocumentFinaliseIn.model_validate({"recipients": [], "extra": extra})


@pytest.mark.parametrize(
    "body",
    [
        {"recipients": [], "cc": ["a@elsewhere.org"]},
        {"recipients": [], "extra": [{"email": "a@elsewhere.org", "mandatory": True}]},
        {"recipients": [], "extra": [{"full_name": "A"}]},
        {"recipients": [], "extra": [{"email": "a@" + "x" * 260}]},
        {"recipients": [], "extra": [{"email": "a@b.org", "full_name": "x" * 201}]},
        {"recipients": ["not a uuid"]},
    ],
    ids=["unknown key", "unknown extra key", "no address", "long address", "long name", "uuid"],
)
def test_what_the_window_does_not_send_is_refused(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        BreachDocumentFinaliseIn.model_validate(body)


def test_the_mark_is_yes_or_no() -> None:
    assert BoardRecipientMandatoryIn.model_validate({"mandatory": True}).mandatory is True
    for body in ({}, {"mandatory": "perhaps"}, {"mandatory": True, "why": "x"}):
        with pytest.raises(ValidationError):
            BoardRecipientMandatoryIn.model_validate(body)
