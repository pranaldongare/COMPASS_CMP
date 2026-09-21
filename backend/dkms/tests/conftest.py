from __future__ import annotations

import base64
import os
from collections.abc import Iterator
from typing import Any

import pytest

#: A key for the suite alone, so a developer's `.env` cannot change what the
#: tests prove - and so nothing here is encrypted under a real one.
os.environ["DKMS_MASTER_KEY"] = base64.b64encode(b"t" * 32).decode()
os.environ["ENVIRONMENT"] = "test"
os.environ["DKMS_POOL_WORKERS"] = "4"
os.environ["DKMS_CHUNK_SIZE"] = "8"


@pytest.fixture
def client() -> Iterator[Any]:
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture
def provider() -> Any:
    from app.config import get_settings
    from app.dkms.local import LocalAesProvider

    s = get_settings()
    return LocalAesProvider(s.master_key_bytes, version=s.key_version)
