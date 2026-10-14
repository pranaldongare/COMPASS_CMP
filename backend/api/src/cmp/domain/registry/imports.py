"""Processors and data sources from an Excel workbook (2026-10-14).

An administrator setting the registry up has a spreadsheet of the labs, tools
and partners the organisation works with, and of the sources each runs. Typing
them in one form at a time is where mistakes come from, so the registry takes
the spreadsheet.

The rules are the forms' rules, row by row, and three more:

* **All or nothing.** A file with any row in error creates nothing. Half a
  registry is worse than none: the rows that went in are the ones nobody
  checks again. `check` says what a file would do without doing it.
* **Re-uploading is safe.** A processor whose legal name is registered, or a
  source whose code is, is skipped and reported, not created twice and not
  overwritten. Changing a registered row is the form's job, where the change
  is audited as a change.
* **Names, not UUIDs.** A source names its processor by legal name or contract
  reference, as a person would.

Each row is created through `service`, so it is audited exactly as the form's
create is.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from cmp.core.enums import ExchangeMode, ProcessorType, SourceRole
from cmp.core.errors import ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import registry as repo
from cmp.db.sql import Conn
from cmp.domain.registry import service
from cmp.infrastructure.spreadsheets import Column, SheetSpec, build_workbook, read_rows

_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")

_YES = {"yes", "y", "true", "1"}
_NO = {"no", "n", "false", "0"}


# ================================================================ columns
PROCESSOR_COLUMNS: tuple[Column, ...] = (
    Column(
        "legal_name",
        "Legal name",
        required=True,
        width=40,
        help="The registered name of the lab, tool or partner. Up to 200 characters. "
        "A name already in the registry is skipped.",
        aliases=("name", "processor"),
    ),
    Column(
        "type",
        "Type",
        required=True,
        width=12,
        help="What kind of processor it is.",
        choices=tuple(t.value for t in ProcessorType),
    ),
    Column(
        "contract_ref",
        "Contract reference",
        required=True,
        width=24,
        help="The contract or DPA that governs the processing. Up to 120 characters.",
        aliases=("contract", "contract ref"),
    ),
    Column(
        "security_confirmed_at",
        "Security confirmed on",
        required=True,
        width=22,
        help="The date the processor's security safeguards were confirmed (Rule 6(1)(f)), "
        "as YYYY-MM-DD. Not in the future.",
        aliases=("security confirmed", "security confirmed at"),
    ),
    Column(
        "is_in_house",
        "In-house",
        width=12,
        help="Yes when this is the organisation collecting for itself; No (or blank) for "
        "a third party.",
        choices=("Yes", "No"),
        aliases=("in house", "is in house"),
    ),
    Column(
        "location_country",
        "Country",
        width=12,
        help="Where the processor is: a two-letter ISO country code such as IN or SG. "
        "An export to a processor without one is refused.",
        aliases=("location country", "location"),
    ),
)

SOURCE_COLUMNS: tuple[Column, ...] = (
    Column(
        "source_code",
        "Source code",
        required=True,
        width=20,
        help="A short unique code: letters, digits, '.', '_' or '-', starting with a letter "
        "or digit. Up to 80 characters. A code already in the registry is skipped.",
        aliases=("code",),
    ),
    Column(
        "name",
        "Name",
        required=True,
        width=36,
        help="What people call the source. Up to 200 characters.",
    ),
    Column(
        "source_role",
        "Role",
        required=True,
        width=14,
        help="identity: who the person is; collection: what is collected; both.",
        choices=tuple(r.value for r in SourceRole),
        aliases=("source role",),
    ),
    Column(
        "exchange_mode",
        "Exchange mode",
        required=True,
        width=16,
        help="How data moves between the source and the platform.",
        choices=tuple(m.value for m in ExchangeMode),
        aliases=("exchange",),
    ),
    Column(
        "id_scheme",
        "ID scheme",
        width=24,
        help="How the source identifies a person, e.g. 'Lab participant ID'. Optional; up to "
        "120 characters.",
        aliases=("id scheme",),
    ),
    Column(
        "processor",
        "Processor",
        width=36,
        help="The processor that runs the source, by legal name or contract reference, as "
        "registered. Blank for a source the organisation runs itself.",
        aliases=("processor name", "processor legal name"),
    ),
    Column(
        "is_authoritative_for",
        "Authoritative for",
        width=30,
        help="The data elements this source owns, separated by commas, e.g. "
        "'gait_video, sensor_reading'. Optional.",
        aliases=("authoritative for",),
    ),
)

_SAMPLE_PROCESSORS: tuple[tuple[Any, ...], ...] = (
    ("Pune Gait Research Labs Pvt Ltd", "lab", "MSA-2026-PGR-001", date(2026, 9, 15), "No", "IN"),
    ("Hyderabad Voice Data Services LLP", "lab", "MSA-2026-HVD-014", date(2026, 8, 28), "No", "IN"),
    ("LabelWorks Annotation Tool", "tool", "DPA-2026-LW-007", date(2026, 9, 2), "No", "SG"),
    ("COMPASS In-house Sensor Lab", "lab", "INT-2026-ISL-001", date(2026, 10, 1), "Yes", "IN"),
    ("Bengaluru Field Survey Partners", "other", "MSA-2026-BFS-021", date(2026, 7, 30), "No", "IN"),
)

_SAMPLE_SOURCES: tuple[tuple[Any, ...], ...] = (
    (
        "SRC-PGR-PUNE-01",
        "Pune gait capture studio",
        "collection",
        "file_export",
        "Lab participant ID",
        "Pune Gait Research Labs Pvt Ltd",
        "gait_video",
    ),
    (
        "SRC-PGR-ID-01",
        "Pune gait participant register",
        "identity",
        "api",
        "Lab participant ID",
        "MSA-2026-PGR-001",
        "",
    ),
    (
        "SRC-HVD-HYD-01",
        "Hyderabad voice booth uploads",
        "collection",
        "manual_upload",
        "Speaker ID",
        "Hyderabad Voice Data Services LLP",
        "voice_recording",
    ),
    (
        "SRC-LW-ANNOT-01",
        "LabelWorks annotation returns",
        "collection",
        "file_import",
        "",
        "LabelWorks Annotation Tool",
        "",
    ),
    (
        "SRC-ISL-BLR-01",
        "Bengaluru sensor lab",
        "both",
        "api",
        "Employee badge ID",
        "COMPASS In-house Sensor Lab",
        "sensor_reading, location",
    ),
    ("SRC-HR-MASTER", "HR master directory", "identity", "api", "Employee ID", "", ""),
)

PROCESSOR_SHEET = "Processors"
SOURCE_SHEET = "Data sources"

_GUIDE = (
    "How to fill in this workbook",
    "Fill one row per record on the first sheet. Columns marked * are required.",
    "Keep the headings in row 1 as they are. Columns can be in any order; extra columns "
    "are ignored.",
    "Upload it with 'Check' first: nothing is created until every row is valid.",
    "A row already in the registry is skipped, so the same file can be uploaded again.",
)


def template(kind: str, *, sample: bool = False) -> bytes:
    """The workbook to fill in, empty or with example rows."""
    if kind == "processors":
        spec = SheetSpec(PROCESSOR_SHEET, PROCESSOR_COLUMNS, _SAMPLE_PROCESSORS if sample else ())
    else:
        spec = SheetSpec(SOURCE_SHEET, SOURCE_COLUMNS, _SAMPLE_SOURCES if sample else ())
    return build_workbook([spec], instructions=_GUIDE)


# ================================================================ values
class _Row:
    """One spreadsheet row being read: its values and what is wrong with it."""

    def __init__(self, number: int, values: dict[str, Any], columns: Sequence[Column]) -> None:
        self.number = number
        self.values = values
        self.headers = {c.key: c.header for c in columns}
        self.problems: list[dict[str, str]] = []

    def fail(self, key: str, message: str) -> None:
        self.problems.append({"column": self.headers.get(key, key), "message": message})

    def text(self, key: str, *, required: bool = False, max_len: int = 200) -> str | None:
        raw = self.values.get(key)
        if isinstance(raw, float) and raw.is_integer():
            raw = int(raw)  # a code typed as 1001 arrives as 1001.0
        value = None if raw is None else str(raw).strip() or None
        if value is None:
            if required:
                self.fail(key, "Required")
            return None
        if len(value) > max_len:
            self.fail(key, f"At most {max_len} characters")
            return None
        return value

    def choice[E: StrEnum](self, key: str, enum: type[E]) -> E | None:
        value = self.text(key, required=True)
        if value is None:
            return None
        normal = "_".join(value.lower().replace("-", " ").split())
        try:
            return enum(normal)
        except ValueError:
            allowed = ", ".join(e.value for e in enum)
            self.fail(key, f"'{value}' is not one of: {allowed}")
            return None

    def day(self, key: str) -> date | None:
        raw = self.values.get(key)
        if raw is None:
            self.fail(key, "Required")
            return None
        value: date | None
        if isinstance(raw, datetime):
            value = raw.date()
        elif isinstance(raw, date):
            value = raw
        else:
            value = _parse_day(str(raw).strip())
        if value is None:
            self.fail(key, f"'{raw}' is not a date; write it as YYYY-MM-DD")
            return None
        if value > datetime.now(UTC).date():
            self.fail(key, "Cannot be dated in the future")
            return None
        return value

    def yes_no(self, key: str) -> bool:
        raw = self.values.get(key)
        if raw is None:
            return False
        if isinstance(raw, bool):
            return raw
        value = str(raw).strip().lower()
        if value in _YES:
            return True
        if value not in _NO:
            self.fail(key, f"'{raw}' is not Yes or No")
        return False


def _parse_day(text: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    return None


# ================================================================ reports
def _report(kind: str, rows: list[dict[str, Any]], *, applied: bool) -> dict[str, Any]:
    def count(outcome: str) -> int:
        return sum(1 for r in rows if r["outcome"] == outcome)

    return {
        "kind": kind,
        "applied": applied,
        "total": len(rows),
        "created": count("created") + count("ready"),
        "skipped": count("skipped"),
        "errors": count("error"),
        "rows": rows,
    }


def _line(row: _Row, name: str | None, outcome: str, message: str | None = None) -> dict[str, Any]:
    return {
        "row": row.number,
        "name": name,
        "outcome": outcome,
        "message": message,
        "problems": row.problems,
        "uuid": None,
    }


async def _run(
    conn: Conn,
    *,
    kind: str,
    rows: list[dict[str, Any]],
    creates: list[tuple[dict[str, Any], Callable[[], Any]]],
    apply: bool,
) -> dict[str, Any]:
    if not rows:
        raise ValidationFailed("The sheet has headings but no rows to import.", field="file")
    if not apply:
        return _report(kind, rows, applied=False)
    report = _report(kind, rows, applied=False)
    if report["errors"]:
        # The route's transaction rolls back with this, so nothing half-lands.
        raise ValidationFailed(
            f"{report['errors']} row(s) need fixing. Nothing was imported.",
            code="import_rejected",
            field="file",
            details=report,
        )
    for line, create in creates:
        created = await create()
        line["outcome"] = "created"
        line["uuid"] = str(created.get("processor_uuid") or created.get("source_uuid"))
    return _report(kind, rows, applied=True)


# ================================================================ processors
async def processors(conn: Conn, *, payload: bytes, apply: bool) -> dict[str, Any]:
    """What a processors workbook would do (`apply=False`), or doing it."""
    lines: list[dict[str, Any]] = []
    creates: list[tuple[dict[str, Any], Callable[[], Any]]] = []
    seen: dict[str, int] = {}

    for number, values in read_rows(payload, columns=PROCESSOR_COLUMNS, sheet=PROCESSOR_SHEET):
        row = _Row(number, values, PROCESSOR_COLUMNS)
        legal_name = row.text("legal_name", required=True)
        type_ = row.choice("type", ProcessorType)
        contract_ref = row.text("contract_ref", required=True, max_len=120)
        confirmed = row.day("security_confirmed_at")
        in_house = row.yes_no("is_in_house")
        country = row.text("location_country", max_len=2000)
        if country is not None:
            country = country.upper()
            if not _COUNTRY.match(country):
                row.fail("location_country", f"'{country}' is not a two-letter country code")

        if legal_name:
            key = legal_name.casefold()
            if key in seen:
                row.fail("legal_name", f"Also on row {seen[key]} of this sheet")
            else:
                seen[key] = number

        if row.problems:
            lines.append(_line(row, legal_name, "error"))
            continue
        assert legal_name and type_ and contract_ref and confirmed
        registered = [
            p
            for p in await repo.processors_named(conn, legal_name)
            if p["legal_name"].casefold() == legal_name.casefold()
        ]
        if registered:
            lines.append(_line(row, legal_name, "skipped", "Already registered"))
            continue

        line = _line(row, legal_name, "ready")
        lines.append(line)

        def create(
            legal_name: str = legal_name,
            type_: str = type_.value,
            contract_ref: str = contract_ref,
            confirmed: date = confirmed,
            in_house: bool = in_house,
            country: str | None = country,
        ) -> Any:
            return service.create_processor(
                conn,
                legal_name=legal_name,
                type_=type_,
                contract_ref=contract_ref,
                security_confirmed_at=confirmed,
                is_in_house=in_house,
                location_country=country,
            )

        creates.append((line, create))

    return await _run(conn, kind="processors", rows=lines, creates=creates, apply=apply)


# ================================================================ sources
async def sources(conn: Conn, *, payload: bytes, apply: bool, user_id: int) -> dict[str, Any]:
    """What a data-sources workbook would do (`apply=False`), or doing it.

    Created as the administrator: every processor is open to them, and a
    source with no processor is one the organisation runs itself.
    """
    lines: list[dict[str, Any]] = []
    creates: list[tuple[dict[str, Any], Callable[[], Any]]] = []
    seen: dict[str, int] = {}
    named: dict[str, list[dict[str, Any]]] = {}

    for number, values in read_rows(payload, columns=SOURCE_COLUMNS, sheet=SOURCE_SHEET):
        row = _Row(number, values, SOURCE_COLUMNS)
        code = row.text("source_code", required=True, max_len=80)
        if code and not _CODE.match(code):
            row.fail(
                "source_code",
                "Use letters, digits, '.', '_' or '-', starting with a letter or digit",
            )
        name = row.text("name", required=True)
        source_role = row.choice("source_role", SourceRole)
        exchange_mode = row.choice("exchange_mode", ExchangeMode)
        id_scheme = row.text("id_scheme", max_len=120)
        processor_text = row.text("processor")
        elements_text = row.text("is_authoritative_for", max_len=2000) or ""
        elements = [e.strip() for e in elements_text.split(",") if e.strip()]
        if any(len(e) > 80 for e in elements):
            row.fail("is_authoritative_for", "Each data element is at most 80 characters")

        if code:
            key = code.casefold()
            if key in seen:
                row.fail("source_code", f"Also on row {seen[key]} of this sheet")
            else:
                seen[key] = number

        processor_uuid: str | None = None
        if processor_text:
            key = processor_text.casefold()
            if key not in named:
                named[key] = await repo.processors_named(conn, processor_text)
            matches = named[key]
            if not matches:
                row.fail("processor", f"No processor is registered as '{processor_text}'")
            elif len(matches) > 1:
                row.fail(
                    "processor",
                    f"'{processor_text}' names {len(matches)} processors; "
                    "use the contract reference instead",
                )
            elif matches[0]["status"] != "active":
                row.fail(
                    "processor",
                    f"{matches[0]['legal_name']} is {matches[0]['status']} and cannot take "
                    "new data sources",
                )
            else:
                processor_uuid = str(matches[0]["processor_uuid"])

        if row.problems:
            lines.append(_line(row, name or code, "error"))
            continue
        assert code and name and source_role and exchange_mode
        if await repo.source_by_code(conn, code):
            lines.append(_line(row, name, "skipped", f"{code} is already registered"))
            continue

        line = _line(row, name, "ready")
        lines.append(line)

        def create(
            code: str = code,
            name: str = name,
            source_role: str = source_role.value,
            exchange_mode: str = exchange_mode.value,
            id_scheme: str | None = id_scheme,
            processor_uuid: str | None = processor_uuid,
            elements: list[str] = elements,
        ) -> Any:
            return service.create_source(
                conn,
                role=Role.ADMIN,
                user_id=user_id,
                source_code=code,
                name=name,
                source_role=source_role,
                exchange_mode=exchange_mode,
                id_scheme=id_scheme,
                processor_uuid=processor_uuid,
                site_uuid=None,
                is_authoritative_for=elements,
            )

        creates.append((line, create))

    return await _run(conn, kind="sources", rows=lines, creates=creates, apply=apply)
