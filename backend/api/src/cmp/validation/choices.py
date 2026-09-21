"""A caller's choice becomes an enum member, or a 422 that names the choices.

Request bodies and imported documents carry enumerated fields as plain strings,
so that a refusal can be a sentence of ours rather than a schema error. That
puts the conversion to an enum inside the service - where an unknown value used
to raise ValueError, or to reach PostgreSQL and be refused there, and either
was a 500 the caller could do nothing with. The rights probes found the first
on 2026-09-05; a notice whose language cell read "English (en-IN)" found the
second the same day. Every such conversion goes through here now.
"""

from __future__ import annotations

from enum import StrEnum

from cmp.core.errors import ValidationFailed


def spell_choices(enum: type[StrEnum]) -> str:
    """The members as a sentence fragment: "a, b or c"."""
    names = [m.value for m in enum]
    return f"{', '.join(names[:-1])} or {names[-1]}" if len(names) > 1 else names[0]


def choice[E: StrEnum](enum: type[E], value: str, *, field: str) -> E:
    """`value` as a member of `enum`, or a 422 on `field` naming the members."""
    try:
        return enum(value)
    except ValueError:
        raise ValidationFailed(f"Choose {spell_choices(enum)}", field=field) from None
