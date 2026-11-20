"""Contact types.

A data subject is reached by email or mobile, and both are how they sign in —
there is no password on a data subject account. That makes these the identifiers
of a person as much as a way to contact them.
"""

from __future__ import annotations

import re
from typing import Annotated

import email_validator
from pydantic import AfterValidator, EmailStr, StringConstraints

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
#: And Indian (2026-11-20): texts go to Indian mobiles only, so a number of
#: any other country is refused where it is typed. Kept as typed.
Mobile = Annotated[
    str,
    StringConstraints(min_length=6, max_length=20, pattern=r"^\+?[0-9 \-]+$"),
    AfterValidator(lambda v: require_indian_mobile(v)),
]

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


#: The one message every form and list gives a number that is not India's.
NOT_INDIAN = "Enter an Indian mobile number: ten digits, with or without +91"


def indian_mobile(value: str) -> str | None:
    """The number as `+91` and its ten digits, or None if it is not India's.

    Texts go to Indian mobiles only (the product owner, 2026-11-20). Accepted,
    however punctuated: `+91 98765 43210`, `0091…`, `91…` with twelve digits,
    a trunk `0` and ten digits, or the ten digits alone. Anything else - a
    foreign code, a number of another length - is None, so that it is refused
    where it is typed rather than sent somewhere it was not meant for.
    """
    number = normalise_mobile(value)
    if number.startswith("+"):
        digits = number[1:]
        national = digits[2:] if digits.startswith("91") else ""
    elif number.startswith("00"):
        digits = number[2:]
        national = digits[2:] if digits.startswith("91") else ""
    elif len(number) == 12 and number.startswith("91"):
        national = number[2:]
    elif len(number) == 11 and number.startswith("0"):
        national = number[1:]
    else:
        national = number
    if len(national) != 10 or not national.isdigit() or national.startswith("0"):
        return None
    return "+91" + national


def require_indian_mobile(value: str) -> str:
    """For a form's mobile field: the value as typed, if it is India's.
    Stored as typed, as before; only its shape is checked."""
    if indian_mobile(value) is None:
        raise ValueError(NOT_INDIAN)
    return value


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
