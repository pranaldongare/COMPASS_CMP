"""Where an export goes, and whether it may (S2-04).

Section 16 lets a fiduciary transfer personal data outside India except to a
country the Government has notified as restricted. A purpose carried
`cross_border_permitted` and nothing read it; no processor said where it was
and no export said where it went. This is the check between the two, run on
every export before anything is written.

**Where a row goes.** Each export row is a consent given at a site, and a site
is run by a processor: that processor is the row's destination, and its
`location_country` is where the row goes. The destination is recorded on the
line, as it was at the moment of the export, beside the person it discloses.

**The rule, per destination:**

* **Unknown** - the processor has no recorded location - is refused. A transfer
  the platform cannot place is one it cannot say is lawful, and "we did not
  record it" must not pass as "domestic" (decided with the product owner).
* **India** is domestic, and goes.
* **Anywhere else** goes only if the country is not on the restricted list and
  every purpose each person granted permits a cross-border transfer - the
  notice said where their data could go, and a purpose that said "not abroad"
  binds. A row with nothing granted - a withdrawal, exported so the agent stops
  - carries no purpose to check.

One failing destination refuses the whole export, naming every reason: a file
is one disclosure, and half of one is not a thing the platform can produce.

**The list is data.** `restricted_country` is kept by the Privacy Office from
the Government's notifications - a country, the notification, and once, when it
was lifted - not code anybody deploys. What is on it is Legal's to say; the
platform only holds it and applies it.

**The decision is evidence.** An export records, per destination, the country
and the ground it went on (`export_log.transfer_basis`); a refusal is audited
with the reasons and the processors, never the people.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import exchange as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

Row = dict[str, Any]

DOMESTIC: Final = "IN"


class TransferRefused(ValidationFailed):
    code = "transfer_refused"


async def assess(conn: Conn, rows: list[Row]) -> dict[str, Any]:
    """The decision for every destination in an export. Raises when any fails."""
    by_processor: dict[int | None, list[Row]] = {}
    for row in rows:
        by_processor.setdefault(row.get("destination_processor_id"), []).append(row)

    destinations: list[Row] = []
    refusals: list[Row] = []
    for processor_id, group in by_processor.items():
        name = str(group[0].get("destination_name") or "a site with no processor")
        country = group[0].get("destination_country")
        if processor_id is None or not country:
            refusals.append({"cause": "location_unknown", "processor": name})
            continue
        if country == DOMESTIC:
            destinations.append(_destination(processor_id, name, country, "domestic", group))
            continue
        listed = await repo.restricted_active(conn, country)
        if listed:
            refusals.append(
                {
                    "cause": "restricted_country",
                    "processor": name,
                    "country": country,
                    "notification": listed["notification_ref"],
                }
            )
            continue
        barred = sorted(
            {code for row in group for code in (row.get("granted_not_cross_border") or [])}
        )
        if barred:
            refusals.append(
                {
                    "cause": "purpose_not_cross_border",
                    "processor": name,
                    "country": country,
                    "purposes": barred,
                }
            )
            continue
        destinations.append(_destination(processor_id, name, country, "s.16", group))

    if refusals:
        raise TransferRefused(_sentence(refusals), details={"refusals": refusals})
    return {"assessed_at": datetime.now(UTC).isoformat(), "destinations": destinations}


def _destination(processor_id: int, name: str, country: str, basis: str, rows: list[Row]) -> Row:
    ground = (
        "Domestic: the processor is in India."
        if basis == "domestic"
        else f"Section 16: {country} is not on the restricted list on this date, and every "
        "purpose granted in these rows permits a transfer outside India."
    )
    return {
        "processor_id": processor_id,
        "processor": name,
        "country": country,
        "basis": basis,
        "ground": ground,
        "rows": len(rows),
    }


def _sentence(refusals: list[Row]) -> str:
    parts = []
    for r in refusals:
        if r["cause"] == "location_unknown":
            parts.append(f"{r['processor']} has no recorded location - record its country first")
        elif r["cause"] == "restricted_country":
            parts.append(
                f"{r['processor']} is in {r['country']}, restricted by {r['notification']}"
            )
        else:
            parts.append(
                f"{r['processor']} is in {r['country']}, and "
                + ", ".join(r["purposes"])
                + " does not permit a transfer outside India"
            )
    return "This export cannot go: " + "; ".join(parts) + "."


async def record_refusal(
    conn: Conn, refused: TransferRefused, *, project_id: int, actor_id: int
) -> None:
    """The refusal as evidence, in its own transaction: the reasons and the
    processors, never the people in the file."""
    await audit.record(
        conn,
        event=Event.EXPORT_REFUSED,
        entity_type="project",
        entity_id=project_id,
        actor_user_id=actor_id,
        detail={"refusals": refused.details.get("refusals", [])},
    )


# ------------------------------------------------------------- the list
def _code(country_code: str) -> str:
    code = country_code.strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValidationFailed("A country is its two-letter ISO code", field="country_code")
    return code


async def restrict(conn: Conn, *, country_code: str, notification_ref: str, actor_id: int) -> Row:
    code = _code(country_code)
    if code == DOMESTIC:
        raise ValidationFailed(
            "India cannot be restricted for transfers out of India", field="country_code"
        )
    if not notification_ref.strip():
        raise ValidationFailed("Name the notification that restricts it", field="notification_ref")
    if await repo.restricted_active(conn, code):
        raise Conflict(f"{code} is already restricted", code="already_restricted")
    listed = await repo.restrict_country(
        conn, country_code=code, notification_ref=notification_ref.strip(), listed_by=actor_id
    )
    await audit.record(
        conn,
        event=Event.TRANSFER_COUNTRY_RESTRICTED,
        entity_type="restricted_country",
        entity_id=int(listed["country_id"]),
        actor_user_id=actor_id,
        detail={"country": code, "notification": notification_ref.strip()},
    )
    return listed


async def lift(conn: Conn, *, country_uuid: str, actor_id: int) -> Row:
    listed = await repo.restricted_by_uuid(conn, country_uuid)
    if not listed:
        raise NotFound("Restriction")
    if listed["lifted_at"] is not None:
        raise Conflict("This restriction has already been lifted", code="restriction_lifted")
    await repo.lift_restriction(conn, country_uuid, lifted_by=actor_id)
    await audit.record(
        conn,
        event=Event.TRANSFER_COUNTRY_LIFTED,
        entity_type="restricted_country",
        entity_id=int(listed["country_id"]),
        actor_user_id=actor_id,
        detail={"country": listed["country_code"]},
    )
    fresh = await repo.restricted_by_uuid(conn, country_uuid)
    assert fresh is not None
    return fresh
