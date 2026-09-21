"""The seat a vendor DKMS SDK takes when there is one.

The contract this adapter expects is the one the callers already describe: an
object with `encrypt`, `decrypt`, `encrypt_bytes` and `decrypt_bytes`, each
taking a value and a data type. If the library on the path exposes those under
other names, this is the single file that changes - nothing above it knows.

It is wired by configuration rather than by import luck: `DKMS_PROVIDER=sdk`
with `DKMS_SDK_MODULE` naming the module and `DKMS_SDK_FACTORY` the callable
that builds the client. Nothing is imported unless it is asked for, so an
environment without the vendor library starts normally on the local provider,
and an environment that asked for the SDK and cannot load it fails loudly at
startup rather than on the first record of the first batch.
"""

from __future__ import annotations

import importlib
from typing import Any

from app.dkms.base import DkmsError
from app.dkms.types import DataType


class SdkProvider:
    """Whatever the vendor client is, behind this service's four methods."""

    def __init__(self, client: Any, *, name: str = "vendor-sdk") -> None:
        for method in ("encrypt", "decrypt", "encrypt_bytes", "decrypt_bytes"):
            if not callable(getattr(client, method, None)):
                raise DkmsError(f"the DKMS client has no {method}()")
        self._client = client
        self.name = name

    def encrypt(self, value: str, data_type: DataType) -> str:
        return str(self._client.encrypt(value, data_type.value))

    def decrypt(self, value: str, data_type: DataType) -> str:
        return str(self._client.decrypt(value, data_type.value))

    def encrypt_bytes(self, value: str, data_type: DataType) -> str:
        return str(self._client.encrypt_bytes(value, data_type.value))

    def decrypt_bytes(self, value: str, data_type: DataType) -> str:
        return str(self._client.decrypt_bytes(value, data_type.value))


def load(module_name: str, factory_name: str) -> SdkProvider:
    """Import the vendor module and build its client, or say exactly why not."""
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise DkmsError(f"DKMS_PROVIDER=sdk, but {module_name!r} is not importable: {exc}") from exc
    factory = getattr(module, factory_name, None)
    if not callable(factory):
        raise DkmsError(f"{module_name}.{factory_name} is not callable")
    return SdkProvider(factory(), name=f"{module_name}.{factory_name}")
