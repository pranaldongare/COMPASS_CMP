"""Composing an HR activity's notice from its template version (ADR 0033).

The version's locked text carries two slots, each exactly once:
`{{purposes}}`, filled with the purposes the activity chose, and
`{{description}}`, filled with the one free text the HR PoC writes. What
comes out is the text a participant is served and the hash her consent
records, so composing is pure and deterministic: the same version, the same
purposes in the same order and the same description give the same text,
byte for byte, and the same hash.

The description is evidence too - it is inside the served text - and it is
the only thing an HR PoC writes, so it is held to the slot: within the
version's limit, no placeholder of its own, no link. A link in a notice is
Legal's to write, in the locked text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Final

from cmp.core.errors import ValidationFailed
from cmp.core.security import content_hash

PURPOSES: Final = "{{purposes}}"
DESCRIPTION: Final = "{{description}}"
PLACEHOLDERS: Final = (PURPOSES, DESCRIPTION)

#: A link of any kind: a scheme, `www.`, or an address. A bare domain in
#: prose ("example.org") is let through; it does nothing in a served text.
_LINK = re.compile(r"(?i)\b(?:[a-z][a-z0-9+.-]*://|www\.|mailto:)")

_SLOT = re.compile("|".join(re.escape(slot) for slot in PLACEHOLDERS))

#: The hash of a composed or locked text: the notice's own (INV-4).
hash_text = content_hash


def placeholder_problems(text: str) -> list[str]:
    """Each slot not present exactly once, in words."""
    problems = []
    for slot in PLACEHOLDERS:
        n = text.count(slot)
        if n == 0:
            problems.append(f"{slot} is missing")
        elif n > 1:
            problems.append(f"{slot} appears {n} times")
    return problems


def check_description(description: str, *, max_length: int) -> str:
    """The description as it will be served, or a refusal naming the rule."""
    text = description.strip()
    if not text:
        raise ValidationFailed("Write the activity's description", field="description")
    if len(text) > max_length:
        raise ValidationFailed(
            f"The description is {len(text)} characters; this template allows {max_length}",
            field="description",
            details={"length": len(text), "max_length": max_length},
        )
    if "{{" in text or "}}" in text:
        raise ValidationFailed(
            "The description cannot contain {{ or }}: they mark the template's slots",
            field="description",
        )
    if _LINK.search(text):
        raise ValidationFailed(
            "The description cannot contain a link; links in a notice are Legal's",
            field="description",
        )
    return text


def render_purposes(purposes: Iterable[Mapping[str, Any]]) -> str:
    """The chosen purposes as the `{{purposes}}` block: one entry each, in the
    order given, saying what it is, what it is used for, and the data it
    covers."""
    entries = []
    for p in purposes:
        need = "required" if p.get("is_mandatory") else "optional"
        lines = [f"- {p['name']} ({need})"]
        if p.get("uses"):
            lines.append(f"  What it is used for: {str(p['uses']).strip()}")
        categories = [str(c) for c in (p.get("data_categories") or [])]
        if categories:
            lines.append(f"  Data: {', '.join(categories)}")
        entries.append("\n".join(lines))
    return "\n".join(entries)


def compose(
    locked_text: str,
    purposes: Iterable[Mapping[str, Any]],
    description: str,
    *,
    max_length: int,
) -> str:
    """The served text: the locked text with both slots filled."""
    problems = placeholder_problems(locked_text)
    if problems:
        # A version is checked at approval; one that reaches here without its
        # slots was changed behind the service's back.
        raise ValidationFailed("The template text is not composable: " + "; ".join(problems))
    filled = {
        PURPOSES: render_purposes(purposes),
        DESCRIPTION: check_description(description, max_length=max_length),
    }
    # One pass: what fills one slot is never read as the other.
    return _SLOT.sub(lambda m: filled[m.group(0)], locked_text)
