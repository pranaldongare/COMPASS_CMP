"""Texts go to Indian mobiles only (the product owner, 2026-11-20).

A number is refused where it is typed if it is not India's, and again before
any text goes, whichever gateway carries it.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from cmp.schemas.common import Mobile as FormMobile
from cmp.validation.contacts import NOT_INDIAN, Mobile, indian_mobile


@pytest.mark.parametrize(
    "typed",
    [
        "9876543210",
        "09876543210",
        "919876543210",
        "+919876543210",
        "+91 98765 43210",
        "(+91) 98765-43210",
        "0091 98765 43210",
    ],
)
def test_every_way_of_writing_an_indian_mobile_is_one_number(typed: str) -> None:
    assert indian_mobile(typed) == "+919876543210"


@pytest.mark.parametrize(
    "typed",
    [
        "+447700900123",  # a foreign code
        "00447700900123",
        "+12065550101",
        "987654321",  # nine digits
        "98765432101",  # eleven, no trunk zero
        "9198765432101",  # thirteen
        "0098765432",  # a trunk zero and nine
        "+910876543210",  # a national number starting 0
        "",
    ],
)
def test_anything_else_is_not(typed: str) -> None:
    assert indian_mobile(typed) is None


@pytest.mark.parametrize("field", [Mobile, FormMobile])
def test_a_form_refuses_a_foreign_number_and_keeps_an_indian_one_as_typed(field: object) -> None:
    adapter = TypeAdapter(field)
    assert adapter.validate_python("+91 98765 43210") == "+91 98765 43210"
    with pytest.raises(ValidationError, match=NOT_INDIAN.split(":")[0]):
        adapter.validate_python("+447700900123")


def test_no_text_goes_to_a_foreign_number_whatever_the_gateway(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cmp.core.messages import Message
    from cmp.infrastructure import messaging, sms

    sent: list[str] = []

    class Gateway:
        def send(self, *, to: str, body: str) -> dict[str, object]:
            sent.append(to)
            return {"delivered": True}

    monkeypatch.setattr(sms, "build_sms_transport", lambda: Gateway())
    monkeypatch.setattr(messaging, "load_overrides", lambda: {})
    with pytest.raises(messaging.NotAnIndianMobile):
        messaging.deliver(Message.LOGIN_CODE, to="+447700900123", code="482913", minutes=10)
    assert sent == []
    messaging.deliver(Message.LOGIN_CODE, to="+919876543210", code="482913", minutes=10)
    assert sent == ["+919876543210"]
