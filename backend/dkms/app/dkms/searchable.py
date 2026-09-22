"""Hashing, so that sealed values can still be found.

Ciphertext is randomised: the same address encrypted twice gives two
different blobs, which is what stops anyone reading the column and is also
what makes `WHERE email = …` impossible. Two hashes bring back the two kinds
of lookup a platform actually needs, and neither of them can be reversed by
reading the database.

**Exact** - `hash_of(type, value)`. `HMAC-SHA256(normalised value)` under a
key this service holds. Deterministic, so it can carry a unique index and
answer "is this address already registered" and "sign this person in". It
reveals nothing without the key, and equal hashes mean equal values, which
is the whole point and also the whole leak: an observer learns which rows
share a value, and nothing else.

**Substring** - `ngrams_of(type, value)`. The normalised value is cut into
overlapping runs of `n` characters and each run is hashed the same way. A
search for "shu" hashes that one run and looks for rows whose set contains
it; "amruta shu" hashes eight runs and looks for rows containing all of
them. That is how a name search survives encryption.

**What the n-grams cost, stated plainly.** They leak more than the exact
hash. An observer with the column can count how often each run appears and
compare that against the letter statistics of any language: with enough
rows, common names can be recovered without the key. That is inherent to
substring search over encrypted data, not an implementation flaw. So they
are computed for the few fields where staff genuinely have to search by part
of a name, never for a contact - a contact is searched whole, through the
exact hash - and the decision is recorded beside each field in the platform's
field map rather than being a property of this service.

**The key is not the master key.** `DKMS_HASH_KEY` is its own secret, so a
hash says nothing about an encryption key and either can be rotated without
the other. It is shared with the platform - the platform's `BLIND_INDEX_KEY`
is the same string, to the character - for one reason worth stating: the
platform computes these hashes locally as well, so that people can still
sign in when this service is unreachable. That also means the labels and the
normalisation below are a contract between two codebases, not an internal
detail: change either and every hash already stored stops matching.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata

from app.dkms.types import DataType

#: The default run length. Three is the usual choice for this kind of index:
#: two is short enough that most rows match most queries, four needs a
#: four-character query before it can answer at all.
DEFAULT_N = 3

#: The shortest term worth an n-gram search. Below this there is no run to
#: hash, and the caller is told rather than being given an empty answer that
#: looks like "no matches".
MIN_TERM = DEFAULT_N

_SPACES = re.compile(r"\s+")
_NOT_DIGIT = re.compile(r"[^0-9]")
_LEADING_PLUS = re.compile(r"^[^0-9+]*\+")

#: A type's label in the hashed message, and the rule its value is reduced by.
#:
#: These are **the platform's** labels, not this service's type names, and
#: that is deliberate: the platform computes the same hashes locally so that
#: people can sign in while this service is unreachable, the columns holding
#: them already have values in them, and a label changed here would make
#: every stored hash unfindable. `NAME` maps to `username` because the only
#: name the platform hashes exactly is a sign-in username; a person's full
#: name is searched by substring, which has its own label.
LABELS: dict[DataType, str] = {
    DataType.EMAIL: "email",
    DataType.MOBILE: "mobile",
    DataType.CONTACT: "contact",
    DataType.IP: "ip",
    DataType.NAME: "username",
    DataType.ORG_ID: "text",
    DataType.GOVT_ID: "text",
}


def _label(data_type: DataType) -> str:
    return LABELS.get(data_type, "text")


def _normalise_mobile(raw: str) -> str:
    """Digits, and a leading plus if one was written before the first digit."""
    plus = _LEADING_PLUS.match(raw) is not None
    return ("+" if plus else "") + _NOT_DIGIT.sub("", raw)


def normalise(data_type: DataType, value: str) -> str:
    """The one form of a value that its exact hash is computed on.

    Character for character what the platform's own `index_of` does, because
    a hash the two compute differently is a row neither can find. Every
    difference that should not make two values different is removed here and
    nowhere else: an address typed in capitals, a number written with spaces
    or brackets.
    """
    raw = value.strip()
    label = _label(data_type)
    if label == "mobile":
        return _normalise_mobile(raw)
    if label == "contact":
        # One box that takes either. An `@` decides which, the way the rest
        # of the platform decides it.
        return raw.lower() if "@" in raw else _normalise_mobile(raw)
    if label == "text":
        # An identifier is compared as issued: case can be part of it.
        return raw
    # email, username, ip.
    return raw.lower()


def normalise_for_ngrams(value: str) -> str:
    """The form the *substring* hashes are computed on.

    Free of the compatibility constraint above - no column holds these yet -
    so it can do the two things a name search needs and the exact hash
    cannot be changed to do: compose accents one way (NFKC), so a name typed
    on two keyboards gives one answer, and treat any run of whitespace as one
    space, so "Amruta  Shukla" and "amruta shukla" are the same string.
    """
    return _SPACES.sub(" ", unicodedata.normalize("NFKC", value).strip()).lower()


def _mac(key: bytes, label: str, message: str) -> str:
    return hmac.new(key, f"{label}:{message}".encode(), hashlib.sha256).hexdigest()


def hash_of(key: bytes, data_type: DataType, value: str) -> str:
    """The exact-match hash of one value: 64 hex characters, or "" for empty.

    The label is part of the message, so the same string filed as an address
    and as a number hashes differently and a lookup cannot cross a column by
    accident.
    """
    text = normalise(data_type, value)
    return _mac(key, _label(data_type), text) if text else ""


def ngrams_of(key: bytes, data_type: DataType, value: str, *, n: int = DEFAULT_N) -> list[str]:
    """The hashed runs of `n` characters, in order of first appearance.

    Deduplicated: a row's set answers "does it contain this run", and a
    repeated run says nothing more. Ordered so that two calls on the same
    value give the same list, which makes a stored column comparable in a
    test and in a diff.

    A value shorter than `n` yields one run - the whole value - so a
    two-letter name is still findable by typing it in full.
    """
    text = normalise_for_ngrams(value)
    if not text:
        return []
    runs = [text] if len(text) <= n else [text[i : i + n] for i in range(len(text) - n + 1)]
    seen: dict[str, None] = {}
    for run in runs:
        seen.setdefault(_mac(key, f"ngram{n}", run), None)
    return list(seen)


def search_ngrams(key: bytes, data_type: DataType, term: str, *, n: int = DEFAULT_N) -> list[str]:
    """The runs a substring search must find, all of them, in one row.

    The same function as `ngrams_of` - a search term is just a shorter value
    - and named separately because the caller's intent differs: these are a
    query, and the SQL that uses them means `@> ARRAY[...]`, not `=`.
    """
    return ngrams_of(key, data_type, term, n=n)
