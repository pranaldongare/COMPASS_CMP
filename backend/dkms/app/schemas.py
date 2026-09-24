"""The request and response bodies.

The request shape is the caller's, unchanged: `data`, `key`, `method`. Two
optional fields are additions rather than changes - `on_error` and
`skip_encrypted` both have defaults that behave exactly as the original
contract did if neither is sent.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.dkms.types import DataType

Method = Literal["string", "bytes"]

#: A record is a flat mapping: the field name as the caller's system spells it,
#: against whatever it holds. Values that are not strings pass through
#: untouched, because a number is not something to encrypt by accident.
Record = dict[str, Any]


class BulkRequest(BaseModel):
    """One batch, and the mapping that says which of its fields to act on."""

    model_config = ConfigDict(extra="forbid")

    data: Annotated[list[Record], Field(min_length=1, description="The records, in order.")]
    key: Annotated[
        dict[str, DataType],
        Field(
            min_length=1,
            description=(
                "Field name to DKMS data type. Only these fields are touched; "
                "every other field passes through exactly as it arrived."
            ),
            examples=[{"fullName": "NAME", "emailId": "EMAIL"}],
        ),
    ]
    method: Method = Field(
        "string",
        description=(
            "'string' uses encrypt()/decrypt() and the SE:: prefix; "
            "'bytes' uses encrypt_bytes()/decrypt_bytes() and plain base64."
        ),
    )
    on_error: Literal["fail", "skip"] = Field(
        "fail",
        description=(
            "'fail' refuses the whole batch and names the record and field. "
            "'skip' leaves that one value as it arrived and reports it in "
            "`errors`, which is what a migration over old rows wants."
        ),
    )
    skip_encrypted: bool = Field(
        True,
        description=(
            "On encrypt, leave a value that is already DKMS ciphertext alone. "
            "Stops a batch that is run twice from double-encrypting, which "
            "cannot be undone by the second decrypt."
        ),
    )
    with_hash: bool = Field(
        False,
        description=(
            "On encrypt, return `<field>_hash` beside each encrypted field: the "
            "exact-match hash of what was encrypted, for the caller to store in "
            "the column it looks rows up by. Off by default, so the contract is "
            "what it always was unless it is asked for."
        ),
    )
    with_ngrams: bool = Field(
        False,
        description=(
            "On encrypt, also return `<field>_ngrams`: the hashed character runs "
            "that make substring search possible. Ask for these only on fields "
            "that are searched by part of a value - they leak more than the "
            "exact hash, which is why they are not the default."
        ),
    )
    ngram_size: int = Field(3, ge=2, le=8, description="Characters per run.")


class FieldError(BaseModel):
    """Where it went wrong, without ever quoting what was in the field."""

    index: int = Field(description="Position of the record in `data`, from 0.")
    field: str
    data_type: DataType
    message: str


class BulkResponse(BaseModel):
    """The records back, in the order they came, with the fields replaced."""

    data: list[Record]
    method: Method
    records: int = Field(description="How many records were processed.")
    values: int = Field(description="How many individual values were transformed.")
    skipped: int = Field(description="Values left alone: absent, null, or already done.")
    errors: list[FieldError] = Field(default_factory=list)
    took_ms: float
    provider: str
    workers: int


# ------------------------------------------------------------------- hashing
class HashRequest(BaseModel):
    """The same shape as a bulk call, for the hashing of whole records."""

    model_config = ConfigDict(extra="forbid")

    data: Annotated[list[Record], Field(min_length=1, description="The records, in order.")]
    key: Annotated[
        dict[str, DataType],
        Field(min_length=1, description="Field name to DKMS data type."),
    ]
    with_ngrams: bool = Field(
        False, description="Also return `<field>_ngrams` for substring search."
    )
    ngram_size: int = Field(3, ge=2, le=8)


class HashResponse(BaseModel):
    """The records back, each named field replaced by its hash.

    A field that was `"amruta@x.org"` comes back as 64 hex characters; when
    `with_ngrams` is asked for, `<field>_ngrams` is added beside it. Values
    that are not strings, and absent fields, pass through as they arrived.
    """

    data: list[Record]
    records: int
    values: int
    took_ms: float


class SearchRequest(BaseModel):
    """One term, and what kind of value it is."""

    model_config = ConfigDict(extra="forbid")

    term: Annotated[str, Field(min_length=1, max_length=400)]
    type: DataType = Field(description="The type the stored column was sealed as.")


class SearchResponse(BaseModel):
    """What to look for, and what the caller should do with it.

    The service holds keys, not rows: it cannot search anything. It answers
    with the hash the caller's own `WHERE` clause needs, and says so in
    `sql`, so that two callers do not invent two different queries.
    """

    term_normalised: str = Field(description="What the term was reduced to before hashing.")
    hash: str = Field(description="Look for a row whose `<field>_hash` equals this.")
    sql: str = Field(description="The comparison this answer is for.")


class NgramSearchRequest(SearchRequest):
    ngram_size: int = Field(3, ge=2, le=8)


class NgramSearchResponse(BaseModel):
    """The runs a row must contain, all of them, for the term to be in it."""

    term_normalised: str
    ngrams: list[str] = Field(description="Every one must be present in the row's set.")
    ngram_size: int
    sql: str


class AutoDecryptRequest(BaseModel):
    """Sealed values by a key of the caller's choosing, with no types named.

    The shape the deployed key service answers on: a flat `payload` of
    key to `SE::` value. Each value's type is read off its envelope, so the
    caller need know nothing but that it holds ciphertext.
    """

    model_config = ConfigDict(extra="forbid")

    payload: Annotated[
        dict[str, str],
        Field(
            min_length=1,
            description="Caller's key to an `SE::` value.",
            examples=[{"v0": "SE::..."}],
        ),
    ]


class AutoDecryptResponse(BaseModel):
    """The same keys, each against its plaintext."""

    data: dict[str, str]
