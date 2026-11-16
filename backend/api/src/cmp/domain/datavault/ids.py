"""How a person, a consent, a project and a request are named to DataVault (0071).

DataVault's first build keys what it holds by the numbers the console shows -
Person ID, Consent ID, Project ID - and will move to uuids "once integration
is done properly" (the product owner, 2026-11-13). So which of the two goes
out is the administrator's to switch, once, for every call: `numeric` or
`uuid` on the connection. A request has no number of its own: by number it is
named by its reference (RR-2026-...), as the lookup has named it from the
start; by uuid, by its uuid.

What a message itself is called - an `erasure_id`, a `message_id` - is always
a uuid: it names the message, not a record. And an asset goes back to
DataVault with the consent DataVault gave for it, whatever the switch says:
that is its own word for it.
"""

from __future__ import annotations

from typing import Any, Final

NUMERIC: Final = "numeric"
UUID: Final = "uuid"
FORMATS: Final = (NUMERIC, UUID)


def of(fmt: str, *, no: Any, uuid: Any) -> int | str:
    """A person, a consent or a project: its number, or its uuid."""
    return int(no) if fmt == NUMERIC else str(uuid)


def request(fmt: str, *, reference: Any, uuid: Any) -> str:
    """A rights request: its reference, or its uuid."""
    return str(reference) if fmt == NUMERIC else str(uuid)
