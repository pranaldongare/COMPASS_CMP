"""What a DKMS provider has to be able to do.

Four methods, named for the contract the callers already use: `encrypt` and
`decrypt` work in the `SE::` string form, `encrypt_bytes` and `decrypt_bytes`
in the base64 form. Everything above this file speaks only to this protocol, so
the local provider and a vendor SDK are interchangeable and the service does
not know which one it is running.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.dkms.types import DataType


class DkmsError(Exception):
    """A failure inside the crypto layer, with nothing sensitive in it.

    The message is written to be safe to log and safe to return: it names the
    data type and what went wrong, never the value and never the key.
    """

    def __init__(self, message: str, *, data_type: DataType | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.data_type = data_type


@runtime_checkable
class DkmsProvider(Protocol):
    """The four operations, and the name of whoever is providing them."""

    name: str

    def encrypt(self, value: str, data_type: DataType) -> str:
        """Plaintext to an `SE::`-prefixed string."""

    def decrypt(self, value: str, data_type: DataType) -> str:
        """An `SE::`-prefixed string back to plaintext."""

    def encrypt_bytes(self, value: str, data_type: DataType) -> str:
        """Plaintext to base64, with no prefix."""

    def decrypt_bytes(self, value: str, data_type: DataType) -> str:
        """Base64 back to plaintext."""
