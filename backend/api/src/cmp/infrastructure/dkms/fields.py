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
        # Sealed since 0028, when each got a blind index beside it. Sign-in,
        # uniqueness and "which of her contacts is this" all read the index.
        "email": DataType.EMAIL,
        "secondary_email": DataType.EMAIL,
        "mobile": DataType.MOBILE,
        "username": DataType.NAME,
        "dob": DataType.DOB,
    },
    "nomination": {
        "nominee_name": DataType.NAME,
        "nominee_email": DataType.EMAIL,
        "nominee_mobile": DataType.MOBILE,
    },
    "rights_request": {
        "submitted_name": DataType.NAME,
        "submitted_contact": DataType.CONTACT,
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

#: The sealed columns the platform finds rows by, and the blind index beside
#: each. A lookup compares the index; the value is opened only to send to it.
#: Before 0028 these stayed plaintext, for the reason each line still gives.
BLIND_INDEXED: dict[str, dict[str, str]] = {
    "auth_user": {
        "email": "email_hash",
        "secondary_email": "secondary_email_hash",
        "mobile": "mobile_hash",
        "username": "username_hash",
        "organization_id": "organization_id_hash",
    },
    "nomination": {
        "nominee_email": "nominee_email_hash",
        "nominee_mobile": "nominee_mobile_hash",
    },
    "rights_request": {
        "submitted_contact": "submitted_contact_hash",
    },
}

#: Columns that also carry a *substring* index: `<column>_ngrams`, a text
#: array of hashed three-character runs with a GIN index on it, so staff can
#: search by part of a name again.
#:
#: Three columns, and the shortness of the list is the point. A set of runs
#: leaks letter statistics that a single hash does not - with enough rows a
#: common name can be recovered from it without the key - so a column earns
#: one only where somebody genuinely types part of a value into a search box
#: and the alternative is that they cannot do their job:
#:
#: * `auth_user.full_name` - the staff register and the audit trail's "who
#:   was this about" picker.
#: * `rights_request.submitted_name` - the name on a request that has not
#:   been matched to an account yet, which is exactly when it is searched for.
#: * `nomination.nominee_name` - finding the nomination somebody is asking
#:   about on the phone.
#:
#: A contact is never here: it is searched whole, through the exact hash,
#: which leaks nothing but equality. Neither is free text - a request's words
#: are read on the request, not searched across the register.
NGRAM_INDEXED: dict[str, dict[str, str]] = {
    "auth_user": {"full_name": "full_name_ngrams"},
    "rights_request": {"submitted_name": "submitted_name_ngrams"},
    "nomination": {"nominee_name": "nominee_name_ngrams"},
}

#: Personal columns that are not sealed, each with the reason. Empty since
#: 0028 for the lookup columns - they have their indexes now - and kept as a
#: structure so the next column that cannot be sealed has somewhere to be
#: written down rather than quietly omitted.
LOOKUP_FIELDS: dict[str, dict[str, str]] = {
    "auth_user": {
        "minor_until": "the date a person stops being a child under s.9; a date "
        "comparison in SQL, and it says nothing but that date",
    },
}


def fields_for(table: str) -> dict[str, DataType]:
    """The key mapping for a table, in the shape the service's API takes."""
    return dict(ENCRYPTED_FIELDS.get(table, {}))
