"""The provider that ships with this service: AES-256-GCM, keys derived per type.

There is no vendor SDK in this repository, so this is the implementation the
service runs on until one arrives. It is not a placeholder - it is the real
scheme, and `app/dkms/sdk.py` is the adapter that steps in front of it when a
vendor library is installed and configured.

**The scheme.** One master key. Every data type gets its own key, derived by
HKDF-SHA256 with the type's name as the info string, so a compromise limited to
one type's key is limited to that type. Each value is encrypted with AES-256-GCM
under a fresh 12-byte nonce. The data type and the key version go into the
additional authenticated data, which is what makes a NAME blob refuse to open as
an EMAIL.

**The envelope**, as bytes, before encoding:

    | 'D' | 'K' | version:u8 | type_id:u8 | nonce:12 | ciphertext+tag |

The header is authenticated by being the AAD, so flipping the version or the
type byte does not produce a blob that decrypts - it produces a tag failure.
`encrypt` base64url-encodes that envelope and puts `SE::` in front of it;
`encrypt_bytes` standard-base64-encodes the same envelope with no prefix. The
two forms hold identical bytes, so a value written one way can be read the
other, and the choice is only about what the field it lands in can carry.

**What it is not.** The ciphertext is randomised: encrypting the same address
twice gives two different blobs. That is the correct property for data at rest
and it means an encrypted column cannot be looked up, joined or uniquely
indexed. Anything the platform searches by - the email you sign in with, the
mobile a code goes to - needs a blind index as well, and that is a deliberate
design decision rather than something to work around here.
"""

from __future__ import annotations

import base64
import os
from typing import Final

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.dkms.base import DkmsError
from app.dkms.types import BY_ID, TYPE_IDS, DataType

PREFIX: Final = "SE::"
MAGIC: Final = b"DK"
NONCE_BYTES: Final = 12
HEADER_BYTES: Final = 4  # magic(2) + version(1) + type(1)


def _derive(master: bytes, data_type: DataType, version: int) -> bytes:
    """One key per (type, version), from the master key.

    The version is in the salt rather than the info so that rotating the master
    key rotates every derived key with it, while the info keeps two types apart
    under the same master.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=f"cmp-dkms-v{version}".encode(),
        info=f"type:{data_type.value}".encode(),
    ).derive(master)


class LocalAesProvider:
    """AES-256-GCM against keys derived from a master secret.

    `previous` holds retired master keys by version, so ciphertext written
    before a rotation still opens. Writing always uses `version`.
    """

    name = "local-aes-gcm"

    def __init__(
        self,
        master_key: bytes,
        *,
        version: int = 1,
        previous: dict[int, bytes] | None = None,
    ) -> None:
        if len(master_key) < 32:
            raise DkmsError("the master key must be at least 32 bytes")
        if not 0 < version < 256:
            raise DkmsError("the key version must fit in one byte")
        self._version = version
        self._masters: dict[int, bytes] = {version: master_key, **(previous or {})}
        #: Derived lazily and kept: HKDF is cheap, but not per record per field.
        self._keys: dict[tuple[int, DataType], AESGCM] = {}

    # ------------------------------------------------------------------ keys
    def _cipher(self, data_type: DataType, version: int) -> AESGCM:
        cached = self._keys.get((version, data_type))
        if cached is not None:
            return cached
        master = self._masters.get(version)
        if master is None:
            raise DkmsError(
                f"no key for version {version} - it was retired without being kept",
                data_type=data_type,
            )
        cipher = AESGCM(_derive(master, data_type, version))
        self._keys[(version, data_type)] = cipher
        return cipher

    # --------------------------------------------------------------- envelope
    def _seal(self, value: str, data_type: DataType) -> bytes:
        type_id = TYPE_IDS[data_type]
        header = MAGIC + bytes([self._version, type_id])
        nonce = os.urandom(NONCE_BYTES)
        sealed = self._cipher(data_type, self._version).encrypt(
            nonce, value.encode("utf-8"), header
        )
        return header + nonce + sealed

    def _open(self, envelope: bytes, data_type: DataType) -> str:
        if len(envelope) < HEADER_BYTES + NONCE_BYTES + 16 or envelope[:2] != MAGIC:
            raise DkmsError("not a DKMS envelope", data_type=data_type)
        version, type_id = envelope[2], envelope[3]
        written_as = BY_ID.get(type_id)
        if written_as is None:
            raise DkmsError(f"unknown data type id {type_id}", data_type=data_type)
        if written_as is not data_type:
            # Said plainly, because the caller's key mapping is what is wrong
            # and the tag failure underneath would only say "invalid".
            raise DkmsError(
                f"this value was encrypted as {written_as.value}, not {data_type.value}",
                data_type=data_type,
            )
        header = envelope[:HEADER_BYTES]
        nonce = envelope[HEADER_BYTES : HEADER_BYTES + NONCE_BYTES]
        body = envelope[HEADER_BYTES + NONCE_BYTES :]
        try:
            return self._cipher(data_type, version).decrypt(nonce, body, header).decode("utf-8")
        except InvalidTag as exc:
            raise DkmsError(
                "the value does not decrypt under this key - it was written "
                "under another key, or it has been altered",
                data_type=data_type,
            ) from exc

    # ------------------------------------------------------------------- API
    def encrypt(self, value: str, data_type: DataType) -> str:
        return PREFIX + base64.urlsafe_b64encode(self._seal(value, data_type)).decode("ascii")

    def decrypt(self, value: str, data_type: DataType) -> str:
        if not value.startswith(PREFIX):
            raise DkmsError(f"expected a value beginning {PREFIX}", data_type=data_type)
        try:
            envelope = base64.urlsafe_b64decode(value[len(PREFIX) :])
        except (ValueError, TypeError) as exc:
            raise DkmsError("the value is not valid base64", data_type=data_type) from exc
        return self._open(envelope, data_type)

    def encrypt_bytes(self, value: str, data_type: DataType) -> str:
        return base64.b64encode(self._seal(value, data_type)).decode("ascii")

    def decrypt_bytes(self, value: str, data_type: DataType) -> str:
        try:
            envelope = base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc:
            raise DkmsError("the value is not valid base64", data_type=data_type) from exc
        return self._open(envelope, data_type)
