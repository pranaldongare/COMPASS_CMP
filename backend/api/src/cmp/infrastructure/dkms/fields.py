"""Which column holds which kind of personal data.

One place, so that "what is encrypted" is answerable by reading a file rather
than by grepping call sites. The roster is `docs/domain/personal-data.md`, and
this is that document made executable.

**Two lists, and the difference between them is the whole design.**

`ENCRYPTED_FIELDS` is what can be encrypted with a randomised scheme: written
once, read back whole, never searched. `LOOKUP_FIELDS` is what cannot - not
because it is less sensitive, but because the platform *finds rows by it*. DKMS
ciphertext is randomised, so two encryptions of the same address differ; an
encrypted `email` column cannot answer "is this address already registered",
cannot be uniquely indexed, and cannot be the thing a one-time code is sent to
after a lookup. Encrypting those without a deterministic blind index alongside
would not be a stricter system, it would be a broken sign-in.
"""

from __future__ import annotations

from enum import StrEnum


class DataType(StrEnum):
    """The service's vocabulary, mirrored so callers import one thing.

    Kept in step with `backend/dkms/app/dkms/types.py` by
    `tests/unit/infrastructure/test_dkms_field_map.py`, which asks the running
    service for its roster and fails if this list has drifted.
    """

    NAME = "NAME"
    EMAIL = "EMAIL"
    MOBILE = "MOBILE"
    CONTACT = "CONTACT"
    DOB = "DOB"
    ORG_ID = "ORG_ID"
    PERSON_TYPE = "PERSON_TYPE"
    ADDRESS = "ADDRESS"
    IP = "IP"
    FREE_TEXT = "FREE_TEXT"
    FILE_NAME = "FILE_NAME"
    GOVT_ID = "GOVT_ID"
    GENERIC = "GENERIC"


#: The number each type is written into a ciphertext envelope under, byte 3 of
#: the header. Mirrors `TYPE_IDS` in the service and is checked against it by
#: the same test that checks the enum. It is what lets a consumer holding a
#: sealed value - and nothing else - ask for it back under the right type.
TYPE_IDS: dict[int, DataType] = {
    1: DataType.NAME,
    2: DataType.EMAIL,
    3: DataType.MOBILE,
    4: DataType.CONTACT,
    5: DataType.DOB,
    6: DataType.ORG_ID,
    7: DataType.PERSON_TYPE,
    8: DataType.ADDRESS,
    9: DataType.IP,
    10: DataType.FREE_TEXT,
    11: DataType.FILE_NAME,
    12: DataType.GOVT_ID,
    13: DataType.GENERIC,
}


def type_of(sealed: str) -> DataType | None:
    """The data type a sealed value was written as, read off its envelope.

    `SE::` + base64url( 'D' 'K' version type_id nonce ciphertext ). Anything
    that does not parse as that is not ours, and the answer is None.
    """
    import base64

    if not sealed.startswith("SE::"):
        return None
    try:
        head = base64.urlsafe_b64decode(sealed[4:12] + "==")[:4]
    except (ValueError, TypeError):
        return None
    if len(head) < 4 or head[:2] != b"DK":
        return None
    return TYPE_IDS.get(head[3])


#: Table to {column: type}. Written once, read back whole, never searched -
#: so a randomised ciphertext costs nothing but the decryption.
ENCRYPTED_FIELDS: dict[str, dict[str, DataType]] = {
    "auth_user": {
        "full_name": DataType.NAME,
        "organization_id": DataType.ORG_ID,
    },
    "nomination": {
        "nominee_name": DataType.NAME,
    },
    "rights_request": {
        "submitted_name": DataType.NAME,
        "request_text": DataType.FREE_TEXT,
        "verification_note": DataType.FREE_TEXT,
        "refusal_reason": DataType.FREE_TEXT,
        "remedy_text": DataType.FREE_TEXT,
        "response_text": DataType.FREE_TEXT,
    },
    "rights_request_holder": {
        "responder_name": DataType.NAME,
        "responder_contact": DataType.CONTACT,
        "instruction": DataType.FREE_TEXT,
        # `brief` is not here: it is jsonb, a structured scope summary the
        # holder reads, and it is derived from rows that are sealed themselves.
        "return_summary": DataType.FREE_TEXT,
        "sent_back_reason": DataType.FREE_TEXT,
    },
    "rights_ticket_message": {
        "body": DataType.FREE_TEXT,
        "evidence_name": DataType.FILE_NAME,
    },
    "rights_response_file": {
        "file_name": DataType.FILE_NAME,
    },
    "consent_artefact": {
        "ip_address": DataType.IP,
    },
    "processor_respondent": {
        "name": DataType.NAME,
        "contact": DataType.CONTACT,
    },
    "person_type_history": {
        "reason": DataType.FREE_TEXT,
    },
    "delegation": {
        "reason": DataType.FREE_TEXT,
    },
    "project_processor": {
        "decision_reason": DataType.FREE_TEXT,
    },
    "project_status_history": {
        "reason": DataType.FREE_TEXT,
    },
    "import_batch": {
        "file_name": DataType.FILE_NAME,
    },
}

#: Personal, and *not* in the list above, each with the reason. A field arrives
#: here rather than being quietly omitted, so nobody has to work out whether it
#: was considered.
LOOKUP_FIELDS: dict[str, dict[str, str]] = {
    "auth_user": {
        "email": "signs a person in, and is unique across the register - a "
        "randomised ciphertext cannot answer 'is this address taken'",
        "secondary_email": "signs a person in as well, and carries the same "
        "one-address-one-account rule",
        "mobile": "signs a person in, and is where a one-time code is sent",
        "username": "signs a person in, on the accounts that carry one",
        "dob": "the s.9 minor test is a comparison, run in SQL",
    },
    "nomination": {
        "nominee_email": "the acceptance flow finds the nomination by contact",
        "nominee_mobile": "the acceptance flow finds the nomination by contact, "
        "and the code is sent to it",
    },
    "rights_request": {
        "submitted_contact": "the public request is verified by sending a code "
        "to it, and later requests are matched against it",
    },
}


def fields_for(table: str) -> dict[str, DataType]:
    """The key mapping for a table, in the shape the service's API takes."""
    return dict(ENCRYPTED_FIELDS.get(table, {}))
