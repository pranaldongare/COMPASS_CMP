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
