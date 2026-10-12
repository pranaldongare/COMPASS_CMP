"""The stub is off unless asked for, never in production, and never with a
short token."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cmp.api.routers import _integration_routers
from cmp.core.config import Settings, settings


def test_off_by_default() -> None:
    assert Settings().databank_stub_enabled is False


def test_not_mounted_when_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "databank_stub_enabled", False)
    assert _integration_routers() == ()


def test_mounted_when_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "databank_stub_enabled", True)
    [router] = _integration_routers()
    assert router.prefix == "/integration/v1"


def test_never_in_production() -> None:
    with pytest.raises(ValidationError, match="never in production"):
        Settings(
            environment="production",
            databank_stub_enabled=True,
            databank_service_token="x" * 40,
        )


def test_never_with_a_short_token() -> None:
    with pytest.raises(ValidationError, match="32\\+ characters"):
        Settings(databank_stub_enabled=True, databank_service_token="short")
