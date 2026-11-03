"""Sealing: what makes the queue and the bucket on AWS hold only ciphertext.

A request is personal data in transit - a contact, a one-time code, a session
cookie, a document. It waits in SQS for a moment, sometimes in S3, and AWS must
not be able to read it there. So the bridge seals it to the collector's public
key before it leaves the bridge's memory, and the collector seals the reply
under a key only the bridge that asked still holds.

The scheme is ECIES over X25519, in the shape of HPKE's base mode (RFC 9180):

* The collector has a long-lived X25519 key pair. Its private half never
  leaves the inside; the bridge is configured with the public half.
* For every request the bridge makes a fresh ephemeral pair, agrees a shared
  secret with the collector's public key, and derives two AES-256-GCM keys with
  HKDF-SHA256: one for the request, one for the reply. The ephemeral private
  key is discarded at once; the reply key stays in the bridge's memory until the
  reply arrives or the request times out.
* The collector derives the same two keys from its private key and the
  ephemeral public key carried in the message.

What that buys:

* **Confidentiality at rest on AWS.** SQS and S3 hold ciphertext. Their own
  encryption at rest (SSE-SQS, SSE-S3) is a second layer, not the one relied on.
* **Replies only the asker can read.** A reply is sealed under a key derived
  for that one request, so another bridge, or anyone reading the reply queue,
  cannot open it.
* **Authentic replies.** Only a holder of the collector's private key can
  derive the reply key, so a reply that opens came from a collector.
* **Bound to the request id.** Every seal authenticates the request id as
  associated data, so a sealed body cannot be moved onto another request.

What it does not buy: authenticity of *requests*. The collector's key is public
by design, so anyone allowed to send to the request queue can seal a request.
That is no more than any member of the public can already do through the
website, and the collector treats every request as untrusted input anyway - the
allow-list, the deadline and the API's own authorisation decide what happens.

The wire format of a sealed blob is `magic | ... | nonce | ciphertext`, with a
four-byte magic per kind so a blob of one kind can never be opened as another.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

#: A request envelope, sealed to the collector's public key.
REQUEST = b"CR1Q"
#: A reply envelope, sealed under the request's reply key.
REPLY = b"CR1R"
#: A request body carried in S3, sealed under the request key.
REQUEST_BODY = b"CR1B"
#: A reply body carried in S3, sealed under the reply key.
REPLY_BODY = b"CR1S"

_INFO = b"cmp-relay v1"
_KEY_ID_LEN = 8
_PUBLIC_LEN = 32
_NONCE_LEN = 12


class SealError(Exception):
    """A blob that is malformed, sealed to another key, or tampered with."""


@dataclass(frozen=True, repr=False)
class RequestKeys:
    """The two symmetric keys one request and its reply are sealed under."""

    request_key: bytes
    reply_key: bytes

    def __repr__(self) -> str:  # never print key material, even in a traceback
        return "RequestKeys(<redacted>)"


# ---------------------------------------------------------------- key handling


def _raw_public(key: X25519PublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _raw_private(key: X25519PrivateKey) -> bytes:
    return key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )


def key_id(public: X25519PublicKey) -> bytes:
    """Eight bytes naming a public key, so a collector holding a current and a
    previous key during a rotation knows which one a request was sealed to."""
    return hashlib.sha256(_raw_public(public)).digest()[:_KEY_ID_LEN]


def generate_keypair() -> tuple[str, str]:
    """A new collector key pair as (private, public), both base64."""
    private = X25519PrivateKey.generate()
    return (
        base64.b64encode(_raw_private(private)).decode(),
        base64.b64encode(_raw_public(private.public_key())).decode(),
    )


def _decode_32(value: str, what: str) -> bytes:
    try:
        raw = base64.b64decode(value.strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{what} is not valid base64") from exc
    if len(raw) != 32:
        raise ValueError(f"{what} must be 32 bytes, base64-encoded")
    return raw


def load_public(value: str) -> X25519PublicKey:
    """The collector's public key, from its base64 form."""
    return X25519PublicKey.from_public_bytes(_decode_32(value, "the collector public key"))


def load_private(value: str) -> X25519PrivateKey:
    """A collector private key, from its base64 form."""
    return X25519PrivateKey.from_private_bytes(_decode_32(value, "the collector private key"))


def public_of(private: X25519PrivateKey) -> str:
    """The base64 public key that goes with a private key."""
    return base64.b64encode(_raw_public(private.public_key())).decode()


def _derive(shared: bytes, ephemeral: bytes, collector: bytes) -> RequestKeys:
    okm = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=ephemeral + collector,
        info=_INFO,
    ).derive(shared)
    return RequestKeys(request_key=okm[:32], reply_key=okm[32:])


def _aad(magic: bytes, request_id: str) -> bytes:
    return magic + b"|" + request_id.encode()


# -------------------------------------------------------------------- requests


def begin_request(collector: X25519PublicKey) -> tuple[bytes, RequestKeys]:
    """Agree a request's keys with the collector. Returns the header that carries
    the ephemeral public key, and the keys. The bridge needs the request key
    before it seals the envelope when a large body is sealed into S3 first."""
    ephemeral = X25519PrivateKey.generate()
    ephemeral_public = _raw_public(ephemeral.public_key())
    keys = _derive(ephemeral.exchange(collector), ephemeral_public, _raw_public(collector))
    return REQUEST + key_id(collector) + ephemeral_public, keys


def finish_request(header: bytes, keys: RequestKeys, plaintext: bytes, request_id: str) -> bytes:
    """Seal a request envelope under keys from `begin_request`."""
    nonce = os.urandom(_NONCE_LEN)
    sealed = AESGCM(keys.request_key).encrypt(nonce, plaintext, _aad(REQUEST, request_id))
    return header + nonce + sealed


def seal_request(
    collector: X25519PublicKey, plaintext: bytes, request_id: str
) -> tuple[bytes, RequestKeys]:
    """Seal a request envelope to the collector. Returns the blob and the keys the
    bridge keeps for this request (it needs the reply key to open the answer)."""
    header, keys = begin_request(collector)
    return finish_request(header, keys, plaintext, request_id), keys


def open_request(
    privates: list[X25519PrivateKey], blob: bytes, request_id: str
) -> tuple[bytes, RequestKeys]:
    """Open a request envelope with whichever of the collector's keys it was sealed
    to. Raises `SealError` for anything that does not open."""
    head = len(REQUEST) + _KEY_ID_LEN + _PUBLIC_LEN + _NONCE_LEN
    if len(blob) <= head or not blob.startswith(REQUEST):
        raise SealError("not a sealed request")
    offset = len(REQUEST)
    wanted = blob[offset : offset + _KEY_ID_LEN]
    offset += _KEY_ID_LEN
    ephemeral_public = blob[offset : offset + _PUBLIC_LEN]
    offset += _PUBLIC_LEN
    nonce = blob[offset : offset + _NONCE_LEN]
    sealed = blob[offset + _NONCE_LEN :]

    private = next((p for p in privates if key_id(p.public_key()) == wanted), None)
    if private is None:
        raise SealError("sealed to a key this collector does not hold")
    try:
        ephemeral = X25519PublicKey.from_public_bytes(ephemeral_public)
        keys = _derive(
            private.exchange(ephemeral), ephemeral_public, _raw_public(private.public_key())
        )
        plaintext = AESGCM(keys.request_key).decrypt(nonce, sealed, _aad(REQUEST, request_id))
    except (InvalidTag, ValueError) as exc:
        raise SealError("request does not open") from exc
    return plaintext, keys


# ------------------------------------------------- replies and bodies (symmetric)


def seal(key: bytes, magic: bytes, plaintext: bytes, request_id: str) -> bytes:
    """Seal a reply envelope or a body under one of a request's keys."""
    nonce = os.urandom(_NONCE_LEN)
    return magic + nonce + AESGCM(key).encrypt(nonce, plaintext, _aad(magic, request_id))


def open_sealed(key: bytes, magic: bytes, blob: bytes, request_id: str) -> bytes:
    """Open what `seal` made. Raises `SealError` for anything that does not open."""
    if len(blob) <= len(magic) + _NONCE_LEN or not blob.startswith(magic):
        raise SealError("not a sealed blob of this kind")
    nonce = blob[len(magic) : len(magic) + _NONCE_LEN]
    try:
        return AESGCM(key).decrypt(nonce, blob[len(magic) + _NONCE_LEN :], _aad(magic, request_id))
    except InvalidTag as exc:
        raise SealError("blob does not open") from exc
