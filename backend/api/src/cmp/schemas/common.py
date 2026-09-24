"""Shared response shapes and validated primitives.

Two conventions enforced by types rather than by review:

* Every identifier crossing the boundary is a uuid. `IntId` does not exist here,
  and there is no serialiser that would emit one.
* Every list response has the same envelope, so the SPA has one parser and one
  loading path rather than eighteen.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Generic, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from cmp.validation.common import plausible_dob

T = TypeVar("T")


class Schema(BaseModel):
    """Base for every request and response model."""

    model_config = ConfigDict(
        extra="forbid",  # an unexpected field is a typo or an attack, not a feature
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True,
        use_enum_values=True,
    )


class Out(BaseModel):
    """Base for response models.

    Deliberately *not* `Schema`. Requests forbid unknown fields - an unexpected
    key in a request body is a typo or an attack, and silently accepting it is
    how a filter that was supposed to narrow a result set quietly stops doing so.

    Responses are the opposite case. A repository row carries internal columns
    (integer primary keys, join scaffolding) that must never reach the client,
    and `response_model` filtering is exactly the mechanism that strips them.
    Forbidding extras here would turn that filtering into a 500 - and, worse,
    would tempt someone to "fix" it by widening the model until the integer id
    ships to the browser.
    """

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        use_enum_values=True,
        ser_json_timedelta="iso8601",
    )


class Page(Out, Generic[T]):
    """The list envelope. Cursor, not offset - see cmp.core.pagination."""

    items: list[T]
    next_cursor: str | None = Field(
        default=None, description="Opaque. Pass back as ?cursor= for the next page."
    )
    total: int | None = Field(
        default=None,
        description="Total matching rows where it is cheap to know. Null means not counted.",
    )


class ErrorDetail(Out):
    code: str
    message: str
    field: str | None = None
    request_id: str


class ErrorResponse(Out):
    """The one error shape. Documented so the SPA can generate a type for it."""

    error: ErrorDetail


class Acknowledged(Out):
    """For state changes whose only interesting output is that they happened."""

    ok: bool = True
    message: str | None = None


class UuidRef(Out):
    uuid: UUID


# --------------------------------------------------------------- primitives
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=200)]
CodeText = Annotated[
    str,
    StringConstraints(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"),
]
LongText = Annotated[str, StringConstraints(min_length=1, max_length=20_000)]

#: A notice rendition: what a data principal actually reads.
#:
#: A minimum, and deliberately no maximum. Every other string here is bounded by
#: what its column holds, but this one is held in `text` and the ceiling was a
#: number somebody picked - and a notice is as long as the processing it has to
#: describe. A fiduciary running many purposes across several recipients writes
#: a long notice because section 5 requires it to, and refusing it is refusing
#: the lawful document. The request body limit still bounds it - `MAX_UPLOAD_BYTES`,
#: 25 MB by default, enforced by `BodyLimitMiddleware`.
NoticeText = Annotated[str, StringConstraints(min_length=1)]
Mobile = Annotated[str, StringConstraints(min_length=6, max_length=20, pattern=r"^\+?[0-9 \-]+$")]
OtpCode = Annotated[str, StringConstraints(min_length=4, max_length=10, pattern=r"^[0-9]+$")]

#: Where a processor is, for s.16: ISO 3166-1 alpha-2, upper-cased on the way in.
CountryCode = Annotated[
    str,
    StringConstraints(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$", to_upper=True),
    Field(description="ISO 3166-1 alpha-2 country code, e.g. IN"),
]

#: Section 9 turns on this date, so every body that accepts one checks it the
#: same way - see `cmp.validation.common.plausible_dob`.
DateOfBirth = Annotated[
    date, AfterValidator(plausible_dob), Field(description="Date of birth, YYYY-MM-DD")
]

# A URL that must be resolvable by a data subject reading the notice on a phone.
# Constrained to http(s) so a notice cannot carry a javascript: or data: link.
HttpUrl = Annotated[
    str, StringConstraints(min_length=8, max_length=2000, pattern=r"^https?://[^\s<>\"]+$")
]

Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class Timestamped(Out):
    created_at: datetime
    updated_at: datetime | None = None


def page_of(items: list[Any], next_cursor: str | None, total: int | None = None) -> dict[str, Any]:
    """Build the envelope from repository output."""
    return {"items": items, "next_cursor": next_cursor, "total": total}
