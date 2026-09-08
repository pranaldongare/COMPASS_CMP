"""Contact types.

A data subject is reached by email or mobile, and both are how they sign in —
there is no password on a data subject account. That makes these the identifiers
of a person as much as a way to contact them.
"""

from __future__ import annotations

import re
from typing import Annotated

import email_validator
from pydantic import EmailStr, StringConstraints

from cmp.core.config import settings

#: The reserved top-level names a development deployment is allowed to use.
#:
#: `email-validator` refuses any address under `.local`, `.localhost` or
#: `.test`, because RFC 6761/6762 reserve them and no mail can be delivered
#: there. That is right in production. It is wrong everywhere else: the seed
#: creates every staff account as `name@cmp.local`, the README tells people to
#: sign in with those, and an administrator provisioning `dco2@cmp.local` from
#: the console was refused with "the part after the @-sign is a special-use or
#: reserved name" - which reads as an error about the @ itself.
#:
#: Edited on the library's own list, which is the mechanism it documents for
#: this, so pydantic's `EmailStr` and every other caller agree. Never removed in
#: production, where an address nobody can reach is a locked-out account.
DEVELOPMENT_DOMAINS: frozenset[str] = frozenset({"local", "localhost", "test"})

if not settings.is_production:
    for _name in DEVELOPMENT_DOMAINS:
        if _name in email_validator.SPECIAL_USE_DOMAIN_NAMES:
            email_validator.SPECIAL_USE_DOMAIN_NAMES.remove(_name)

#: Validated by `email-validator`, which checks the domain's syntax rather than
#: guessing at a regex. Length is bounded by the RFC and by the column.
Email = Annotated[EmailStr, StringConstraints(max_length=255)]

#: Deliberately permissive: this system operates in India and receives numbers
#: written with a country code, spaces or dashes. Normalising aggressively would
#: reject numbers people actually have, and a number we cannot reach is worse
#: than a number stored with a space in it.
Mobile = Annotated[str, StringConstraints(min_length=6, max_length=20, pattern=r"^\+?[0-9 \-]+$")]

#: Either of the above, for the sign-in form that accepts both.
Contact = Annotated[str, StringConstraints(min_length=3, max_length=255)]

_NOT_DIGIT = re.compile(r"\D")


def is_mobile(contact: str) -> bool:
    """A contact without an @ is a mobile. The two shapes share nothing else."""
    return "@" not in contact


def normalise_mobile(value: str) -> str:
    """A mobile as stored and compared: its digits, and a leading plus if it had one.

    People type "+91 90000 00001", "+91-90000-00001" and "(+91) 9000000001" for
    the same phone, and a lookup that compared the typed form found none of
    them. No country code is assumed for a number typed without one.
    """
    raw = value.strip()
    # A plus before the first digit, however it is bracketed: "(+91) 90000 00001".
    plus = re.match(r"^[^0-9+]*\+", raw) is not None
    return ("+" if plus else "") + _NOT_DIGIT.sub("", raw)


def normalise_contact(contact: str) -> str:
    """Lower-case an email; normalise a mobile."""
    raw = contact.strip()
    return normalise_mobile(raw) if is_mobile(raw) else raw.lower()


def mask_contact(contact: str) -> str:
    """Enough for its owner to recognise, nothing for a stranger to use.

    A mobile keeps its country code and last two digits; an email its first
    letter and its domain. Shown on the nomination acceptance page, which a
    link-holder can open before proving anything.
    """
    if is_mobile(contact):
        digits = normalise_mobile(contact)
        plus = digits.startswith("+")
        body = digits[1:] if plus else digits
        head = body[:2] if plus else ""
        rest = body[len(head) :]
        return ("+" if plus else "") + head + "\u2022" * max(len(rest) - 2, 0) + rest[-2:]
    local, _, domain = contact.strip().partition("@")
    return local[:1] + "\u2022" * max(len(local) - 1, 1) + "@" + domain
