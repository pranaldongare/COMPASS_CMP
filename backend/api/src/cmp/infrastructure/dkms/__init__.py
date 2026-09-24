"""Talking to the DKMS service.

`backend/dkms` holds the key; this holds the database. The two are separate
processes so that one compromise is not both, which means every encryption is a
call over the network and the cost of a call is what shapes this module: the
unit is a *batch*, never a field. A write that encrypts four fields of one row
makes one call, and a write that encrypts four fields of two hundred rows makes
one call as well.
"""

from cmp.infrastructure.dkms.client import (
    DkmsClient,
    DkmsUnavailable,
    SealedValueUnreadable,
    decrypt_records,
    encrypt_records,
    get_dkms,
    unseal_values_sync,
    unseal_variables_sync,
)
from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS, DataType, fields_for
from cmp.infrastructure.dkms.rows import (
    opened,
    seal,
    seal_many,
    unseal,
    unseal_many,
    unseal_strings,
    unseal_value,
)

__all__ = [
    "ENCRYPTED_FIELDS",
    "DataType",
    "DkmsClient",
    "DkmsUnavailable",
    "SealedValueUnreadable",
    "decrypt_records",
    "encrypt_records",
    "fields_for",
    "get_dkms",
    "opened",
    "seal",
    "seal_many",
    "unseal",
    "unseal_many",
    "unseal_strings",
    "unseal_value",
    "unseal_values_sync",
    "unseal_variables_sync",
]
