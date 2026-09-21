"""The blind index: how a sealed column can still be looked up.

DKMS ciphertext is randomised, which is the right property for data at rest and
the wrong one for a column the platform finds rows by. Sign-in looks up the
email typed in; "is this address taken" compares against every row; a one-time
code has to find the person it was requested for. None of that works on a value
that encrypts differently every time.

So beside each sealed lookup column sits its blind index:

    HMAC-SHA256(normalised value, BLIND_INDEX_KEY)

Deterministic, so the same address always yields the same index and a unique
constraint on the index column is a unique constraint on the address. Keyed, so
a dump of the table reveals no address and cannot be joined against a list of
guesses without the key. One-way, so the index is never decrypted - the sealed
column beside it is what a message is sent to, opened at the point of sending.

**Normalisation is part of the contract.** `index_of("email", "A@X.org")` and
`index_of("email", "a@x.org")` must agree, or the second registration of the
same address succeeds. Email is lowercased and stripped; mobile goes through the
platform's own `normalise_mobile`; username is lowercased. The `kind` is mixed
into the message so an email and a username that happen to share text do not
share an index.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Literal

from cmp.core.config import settings
from cmp.validation import normalise_mobile

Kind = Literal["email", "mobile", "username", "contact", "text", "ip"]


def normalise(kind: Kind, value: str) -> str:
    """The one form of a value that its index is computed on."""
    v = value.strip()
    if kind == "mobile":
        return normalise_mobile(v)
    if kind == "ip":
        # An address as the socket reported it. Lowercased for IPv6's hex.
        return v.lower()
    if kind == "text":
        # An identifier compared as typed - an employee number. Stripped, and
        # nothing else: case is part of it.
        return v
    if kind == "contact":
        # A contact is an email or a mobile, and the platform decides which the
        # same way everywhere: an @ makes it an address.
        return v.lower() if "@" in v else normalise_mobile(v)
    return v.lower()


def index_of(kind: Kind, value: str | None) -> str | None:
    """The blind index of a value, or None for None.

    Hex, 64 characters, so it fits a text column and reads in a query plan.
    """
    if value is None or not value.strip():
        return None
    key = settings.blind_index_key.get_secret_value().encode()
    msg = f"{kind}:{normalise(kind, value)}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
