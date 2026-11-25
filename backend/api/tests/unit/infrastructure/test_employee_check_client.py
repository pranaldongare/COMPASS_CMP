"""Reading VerifyEmail's answer (ADR 0046): strictly, and only about the
address asked."""

from __future__ import annotations

import httpx
import pytest

from cmp.infrastructure.employee_check import EmployeeCheckFailed, Verdict, read, verify_email

ASKED = "someone@company.example"


@pytest.mark.parametrize(
    ("body", "verdict"),
    [
        ({"MySingleID": ASKED, "IsActive": True, "Status": True}, Verdict.ACTIVE),
        ({"MySingleID": ASKED, "IsActive": False, "Status": True}, Verdict.INACTIVE),
        ({"MySingleID": ASKED, "IsActive": True, "Status": False}, Verdict.INACTIVE),
        (
            {"MySingleID": "SOMEONE@Company.example", "IsActive": True, "Status": True},
            Verdict.ACTIVE,
        ),
        ({"IsActive": True, "Status": True}, Verdict.ACTIVE),
    ],
)
def test_both_flags_true_is_an_active_employee(body: dict[str, object], verdict: Verdict) -> None:
    assert read(body, ASKED) is verdict


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ([], "unreadable"),
        ({"MySingleID": ASKED, "IsActive": "true", "Status": True}, "unreadable"),
        ({"MySingleID": ASKED, "IsActive": 1, "Status": 1}, "unreadable"),
        ({"MySingleID": ASKED, "Status": True}, "unreadable"),
        ({"MySingleID": "other@company.example", "IsActive": True, "Status": True}, "mismatch"),
    ],
)
def test_anything_else_is_no_answer(body: object, code: str) -> None:
    with pytest.raises(EmployeeCheckFailed) as caught:
        read(body, ASKED)
    assert caught.value.code == code


async def test_a_redirect_is_not_followed_and_an_error_body_not_kept() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if request.url.host == "verify.test":
            return httpx.Response(302, headers={"Location": "http://elsewhere.test/VerifyEmail"})
        raise AssertionError("followed a redirect")

    with pytest.raises(EmployeeCheckFailed) as caught:
        await verify_email(
            base_url="http://verify.test",
            email=ASKED,
            api_key=None,
            api_key_header="X-API-Key",
            transport=httpx.MockTransport(answer),
        )
    assert caught.value.code == "status_302"
    assert ASKED not in str(caught.value)


def test_the_stand_in_exists_only_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/dev/verify-email` says anybody is an employee: only on a developer's
    machine, and only when DEV_VERIFY_EMAIL asks for it."""
    from cmp.api.routers import _development_routers

    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", False)
    monkeypatch.setattr("cmp.core.config.settings.sso_mock", False)
    monkeypatch.setattr("cmp.core.config.settings.dev_verify_email", False)
    assert _development_routers() == ()
    monkeypatch.setattr("cmp.core.config.settings.dev_verify_email", True)
    paths = [route.path for r in _development_routers() for route in r.routes]  # type: ignore[attr-defined]
    assert paths == ["/dev/verify-email/VerifyEmail"]
