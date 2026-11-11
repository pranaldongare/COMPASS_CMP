"""The consented list the Data Collection Tool loads (2026-11-11).

The DCT tags, in each file a collection agent captures, the consented people
who appear in it. It loads one list per project, and the list is its data
contract, version 1 (the DCT's `docs/consent-tagging/data-contract.md`): ten
columns, fixed, checked by its own validator before it will tag anything. The
project export does not pass it - withdrawn people are in it, contacts in full,
and timestamps with `+00:00` - so this is a second export beside it, recorded
the same way: `export_log`, one `export_line` per person, the audit event, the
bytes kept and the bytes downloaded.

**Who is on it.** One row per person: their latest current consent on the
project, and only if that one is fully in force.

* **Latest, not latest of the good ones.** A person whose newest consent here is
  a withdrawal or refused a purpose is left out, even if an older one stands. The
  DCT takes one consent per person, and the newest is what they last said.
* **Partial is out.** A person who refused any purpose may have refused this very
  collection; the list cannot say which purpose a file is collected under.
* **Lapsed is out**, by the rule `apply_retention_lapse` acts on: the consent's
  `affirmative_action_at` plus the shortest `consent_validity_period` among the
  purposes granted. A lapse still ahead is `consent_expires_at`, and the DCT
  will not tag a file captured after it.
* **A child is marked, and so is an unknown age.** `is_minor` is
  `cmp_is_minor(minor_until)`, whose own rule is that NULL is not an adult; the
  DCT never lets a person marked `true` be tagged, so an unknown age is `true`.
* **No name, no row.** The DCT refuses the whole file over an empty
  `display_name`, and an agent cannot recognise a person by nothing.

**An empty list is refused, not written.** A header with no rows names no
project, and the DCT rejects it (its rule L02); a file that cannot be loaded is
no use to anyone, and generating it would record a disclosure of nothing.

**What it never carries:** email, the mobile number beyond its last two digits,
the consent link, the notice, the site or the source, or any internal id. It is
copied onto collection laptops.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from cmp.core.config import settings
from cmp.core.csv_safety import text_cell
from cmp.core.errors import Conflict, ServiceUnavailable
from cmp.infrastructure.dkms import unseal_many
from cmp.infrastructure.dkms.fields import PREFIX as SEALED

Row = dict[str, Any]

#: The contract's columns, in its order. The DCT reads them by name, but a
#: person opening the file reads them left to right.
COLUMNS: Final = (
    "project_id",
    "project_name",
    "person_id",
    "consent_id",
    "display_name",
    "contact_hint",
    "consent_expires_at",
    "is_minor",
    "list_generated_at",
    "list_valid_until",
)


def utc_z(moment: datetime) -> str:
    """A timestamp as the contract writes one: UTC, whole seconds, a `Z`.
    `isoformat()` gives `+00:00`, which the DCT does not read."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_name(project_uuid: object, generated_at: datetime) -> str:
    """`consented_list_<project_id>_<YYYYMMDD>.csv`, on the UTC date it was made."""
    return f"consented_list_{str(project_uuid).lower()}_{generated_at.astimezone(UTC):%Y%m%d}.csv"


def contact_hint(mobile: str | None) -> str:
    """The last two digits of the mobile, `…42`: enough to tell two people of
    one name apart, and nothing to call."""
    digits = re.sub(r"\D", "", mobile or "")
    return f"…{digits[-2:]}" if len(digits) >= 2 else ""


def _status(c: Row) -> str:
    # The project export's own words for a consent (`service._consent_status`).
    if c["is_withdrawal"] and not c["granted_count"]:
        return "withdrawn"
    return "consented" if not c["refused_count"] else "partial"


def latest(consents: list[Row]) -> list[Row]:
    """Each person's newest current consent on the project."""
    newest: dict[int, Row] = {}
    for c in consents:
        held = newest.get(int(c["auth_user_id"]))
        if held is None or (c["affirmative_action_at"], c["consent_id"]) > (
            held["affirmative_action_at"],
            held["consent_id"],
        ):
            newest[int(c["auth_user_id"])] = c
    return list(newest.values())


async def choose(consents: list[Row], *, now: datetime) -> tuple[list[Row], dict[str, int]]:
    """Who goes on the list, in name order, and how many were left out and why.

    The names are opened here, on the way into the file, for only the people
    who qualify. A name that will not open is the key service failing, and a
    list that quietly left those people out would look complete, so it stops.
    """
    left_out = {"withdrawn": 0, "partial": 0, "lapsed": 0, "no_name": 0}
    keep: list[Row] = []
    for c in latest(consents):
        status = _status(c)
        if status != "consented":
            left_out[status] += 1
        elif c["consent_expires_at"] is not None and c["consent_expires_at"] <= now:
            left_out["lapsed"] += 1
        else:
            keep.append(c)
    opened = await unseal_many("auth_user", keep)
    named: list[Row] = []
    for c in opened:
        name = str(c.get("full_name") or "").strip()
        if name.startswith(SEALED) or str(c.get("mobile") or "").startswith(SEALED):
            raise ServiceUnavailable("The names could not be opened. Try again in a minute")
        if not name:
            left_out["no_name"] += 1
            continue
        named.append({**c, "full_name": name})
    named.sort(key=lambda c: (c["full_name"].casefold(), str(c["person_uuid"])))
    return named, left_out


def write(project: Row, people: list[Row], *, generated_at: datetime) -> str:
    """The file, as the contract has it. RFC 4180 quoting, `\\n` line ends."""
    if not people:
        raise Conflict(
            "Nobody on this project has a consent in force, so there is no list for the "
            "Data Collection Tool. It cannot load a list with nobody on it",
            code="nobody_consented",
        )
    valid_until = generated_at + timedelta(days=settings.dct_list_valid_days)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(COLUMNS)
    for c in people:
        writer.writerow(
            [
                str(project["project_uuid"]).lower(),
                text_cell(project["project_name"]),
                str(c["person_uuid"]).lower(),
                str(c["consent_uuid"]).lower(),
                text_cell(c["full_name"]),
                contact_hint(c.get("mobile")),
                utc_z(c["consent_expires_at"]) if c["consent_expires_at"] else "",
                # Only a known adult is false: the DCT tags nobody marked true.
                "false" if c["is_minor"] is False else "true",
                utc_z(generated_at),
                utc_z(valid_until),
            ]
        )
    return buf.getvalue()
