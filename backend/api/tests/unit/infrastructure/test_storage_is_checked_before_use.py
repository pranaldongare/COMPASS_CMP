"""Storage is refused at start-up when it cannot work, and checked by `/ready`.

`STORAGE_BACKEND=object` selected a stub that raised on the first save - so a
deployment configured that way started, reported ready, and failed the first
time somebody uploaded an approval proof (review 2026-10-01, SCALE-5). And
`/ready` never looked at storage at all: a local upload root that could not
be written to was ready too.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from cmp.core.config import Settings
from cmp.infrastructure.storage.local import LocalFileStorage


def test_the_unbuilt_object_backend_is_refused_at_start_up() -> None:
    with pytest.raises(ValidationError, match="STORAGE_BACKEND=object"):
        Settings(storage_backend="object")


def test_local_storage_that_can_be_written_is_healthy(tmp_path: Path) -> None:
    ok, detail = LocalFileStorage(str(tmp_path / "uploads")).healthcheck()
    assert ok and detail is None
    assert list((tmp_path / "uploads").iterdir()) == [], "the probe is cleaned up"


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes anywhere")
def test_local_storage_that_cannot_be_written_is_not(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    root.mkdir()
    root.chmod(0o500)
    try:
        ok, detail = LocalFileStorage(str(root)).healthcheck()
    finally:
        root.chmod(0o700)
    assert not ok
    assert detail == "upload root is not writable"
    assert str(tmp_path) not in (detail or ""), "the path is not served on a public endpoint"
