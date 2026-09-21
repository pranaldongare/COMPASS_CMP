"""The data types a field can be encrypted as.

A type is not decoration. It is bound into the ciphertext as additional
authenticated data, so a blob written as an EMAIL cannot be decrypted as a NAME
even by somebody holding every key: the tag check fails. That turns a category
confusion - a mobile number handed to a field expecting a name - from a silent
wrong answer into a refusal.

The roster comes from `docs/domain/personal-data.md`, which is the inventory of
what this platform actually holds about people. A type is added here when that
document gains a kind of field, and never merely because a caller sent one.
"""

from __future__ import annotations

from enum import StrEnum


class DataType(StrEnum):
    """What a field holds, in DKMS's vocabulary."""

    #: A person's name, in any of its spellings.
    NAME = "NAME"
    #: An email address, primary or secondary.
    EMAIL = "EMAIL"
    #: A mobile number, in any format the register accepts.
    MOBILE = "MOBILE"
    #: A contact the caller has not distinguished - the public rights form takes
    #: one box and accepts either.
    CONTACT = "CONTACT"
    #: Date of birth. Its own type because s.9 turns it into a decision.
    DOB = "DOB"
    #: An employee or student number.
    ORG_ID = "ORG_ID"
    #: Employment or affiliation: employee, student, ex-employee, external.
    PERSON_TYPE = "PERSON_TYPE"
    #: A postal address or a place.
    ADDRESS = "ADDRESS"
    #: An IP address. Kept against a consent artefact, and nowhere else.
    IP = "IP"
    #: Anything a person wrote in their own words: a request, a ticket reply, a
    #: reason for a refusal.
    FREE_TEXT = "FREE_TEXT"
    #: The name of a file somebody uploaded, which is often a person's name.
    FILE_NAME = "FILE_NAME"
    #: A national identifier. Nothing in this platform stores one today; the
    #: type exists so that the day something does, it is not filed as GENERIC.
    GOVT_ID = "GOVT_ID"
    #: Personal data that fits none of the above. Correct, and a poor label:
    #: prefer adding a type to leaning on this one.
    GENERIC = "GENERIC"


#: A stable number per type, written into the ciphertext header. Append only,
#: and never reuse a number - a blob written years ago names its type by this.
TYPE_IDS: dict[DataType, int] = {
    DataType.NAME: 1,
    DataType.EMAIL: 2,
    DataType.MOBILE: 3,
    DataType.CONTACT: 4,
    DataType.DOB: 5,
    DataType.ORG_ID: 6,
    DataType.PERSON_TYPE: 7,
    DataType.ADDRESS: 8,
    DataType.IP: 9,
    DataType.FREE_TEXT: 10,
    DataType.FILE_NAME: 11,
    DataType.GOVT_ID: 12,
    DataType.GENERIC: 13,
}

BY_ID: dict[int, DataType] = {v: k for k, v in TYPE_IDS.items()}

assert len(TYPE_IDS) == len(DataType), "every type needs an id"
assert len(BY_ID) == len(TYPE_IDS), "two types share an id"
