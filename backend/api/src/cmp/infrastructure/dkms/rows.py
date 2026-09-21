"""Encrypting the personal columns of a row on its way into the database.

The repositories write SQL by hand, so there is no ORM hook to put this behind.
Instead each write of a table in `ENCRYPTED_FIELDS` calls `seal(table, row)` on
the values it is about to bind, and each server-side reader that needs the
plaintext - the message that greets a person by name, the export a person
downloads - calls `unseal`. The API's own responses are not unsealed: the
portals decrypt in their server layer, which is the design.

Two properties of `seal` are load-bearing:

* **It is a no-op for anything not personal.** A row for a table with no
  personal columns, a column not in the map, a `None`, a value already sealed -
  all pass through. So calling it is never wrong, and a repository can call it
  on every write of a table rather than only the writes it thinks matter.
* **It is one call.** A row with four personal columns is one request to the
  key service, not four. `seal_many` does the same for a list of rows.

Ciphertext is longer than plaintext - about 4/3 of the length plus 45 bytes -
which is why migration 0027 widened the columns it lands in to `text`.
"""

from __future__ import annotations

from typing import Any

from cmp.infrastructure.dkms.client import decrypt_records, encrypt_records
from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS

Row = dict[str, Any]


def _key_for(table: str, rows: list[Row]) -> dict[str, Any]:
    """The field mapping for the columns actually present in these rows."""
    mapping = ENCRYPTED_FIELDS.get(table)
    if not mapping:
        return {}
    present = {k for row in rows for k, v in row.items() if isinstance(v, str)}
    return {column: data_type for column, data_type in mapping.items() if column in present}


async def seal_many(table: str, rows: list[Row]) -> list[Row]:
    """Encrypt the personal columns of every row, in one call. Order preserved."""
    key = _key_for(table, rows)
    if not key:
        return [dict(r) for r in rows]
    return await encrypt_records(rows, key)


async def seal(table: str, row: Row) -> Row:
    """Encrypt the personal columns of one row about to be written."""
    return (await seal_many(table, [row]))[0]


async def unseal_many(table: str, rows: list[Row]) -> list[Row]:
    """Decrypt the personal columns of rows read back, for a server-side consumer.

    Tolerant: a row written before the rollout is plaintext and comes back as it
    is. That is what lets encryption be switched on for a table with rows in it.
    """
    key = _key_for(table, rows)
    if not key:
        return [dict(r) for r in rows]
    return await decrypt_records(rows, key, on_error="skip")


async def unseal(table: str, row: Row) -> Row:
    return (await unseal_many(table, [row]))[0]


async def unseal_value(table: str, column: str, value: Any) -> Any:
    """One sealed value back to plaintext, for a server-side consumer.

    For the places that hold a single field rather than a row: the name that
    goes into a greeting, the contact a ticket is sent to. Anything that is not
    a sealed string comes back as it went in.
    """
    if not isinstance(value, str) or not value.startswith("SE::"):
        return value
    return (await unseal(table, {column: value}))[column]
