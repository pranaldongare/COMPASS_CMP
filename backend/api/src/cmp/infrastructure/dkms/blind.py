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
import re
import unicodedata
from typing import Literal

from cmp.core.config import settings
from cmp.validation import normalise_mobile

Kind = Literal["email", "mobile", "username", "contact", "text", "ip"]

_SPACES = re.compile(r"\s+")


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


# ------------------------------------------------------------------ n-grams
#
# The exact index above answers "which row holds this address". It cannot
# answer "which rows have `shu` somewhere in the name", and that is the
# search staff lost when names were sealed. A second index brings it back:
# the name is cut into overlapping runs of three characters and each run is
# hashed the same way, so a row carries a set of hashes and a search term
# carries a smaller set that must be contained in it.
#
# **It leaks more than the exact index, and that is why it is not everywhere.**
# Anyone holding the column can count how often each run appears and compare
# that against the letter statistics of a language; with enough rows, common
# names come back without the key. So the runs are computed for the handful of
# columns staff actually search by part of - `NGRAM_INDEXED` in `fields.py`
# names them - and never for a contact, which is searched whole.
#
# The key service computes exactly these values from the same key
# (`POST /search_ngram`), so a caller that is not this process gets the same
# answer. This is here as well so that a search does not stop working when
# the key service is unreachable, which is the same reason `index_of` is.

#: Characters per run. Three: two matches almost every row, four needs a
#: four-character term before it can answer at all. Written into the hashed
#: message, so a column written with one length cannot be searched with
#: another and quietly return nothing.
NGRAM_SIZE = 3

#: The shortest term a substring search can be asked for.
MIN_NGRAM_TERM = NGRAM_SIZE


def normalise_for_ngrams(value: str) -> str:
    """The form the runs are computed on: composed, unspaced, lower case.

    Deliberately not `normalise()`. That one is fixed by the values already
    stored under it; this one is new, so it can do what a name search needs -
    fold "Amruta  Shukla" and "amruta shukla" together, and compose an accent
    the same way whichever keyboard typed it.
    """
    return _SPACES.sub(" ", unicodedata.normalize("NFKC", value).strip()).lower()


def ngrams_of(value: str | None, *, n: int = NGRAM_SIZE) -> list[str]:
    """The hashed runs of a value, for the column beside it.

    Deduplicated and in order of first appearance, so two calls on one value
    give one list and a stored array reads the same in a diff. A value
    shorter than a run yields the whole value, so a two-letter name is still
    findable by typing it in full.
    """
    if value is None:
        return []
    text = normalise_for_ngrams(value)
    if not text:
        return []
    runs = [text] if len(text) <= n else [text[i : i + n] for i in range(len(text) - n + 1)]
    key = settings.blind_index_key.get_secret_value().encode()
    seen: dict[str, None] = {}
    for run in runs:
        seen.setdefault(hmac.new(key, f"ngram{n}:{run}".encode(), hashlib.sha256).hexdigest(), None)
    return list(seen)


def search_ngrams(term: str, *, n: int = NGRAM_SIZE) -> list[str]:
    """The runs a row must contain, all of them, for `term` to be inside it.

    The same computation as `ngrams_of`; named apart because the SQL that
    takes it means `@> ARRAY[...]` rather than `=`, and because a term
    shorter than a run has no answer and gives an empty list, which a caller
    must read as "cannot search for this" rather than "nothing matched".
    """
    return ngrams_of(term, n=n) if len(term.strip()) >= n else []
