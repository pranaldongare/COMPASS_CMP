"""Excel workbooks in and out (2026-10-14): the registry imports.

Reading is defensive, because the file comes from outside:

* **Only .xlsx.** It is a zip of XML; anything that does not open as one is
  refused with a plain message. The old binary `.xls` is not read.
* **No XML tricks.** `defusedxml` is installed, and `openpyxl` uses it when it
  is, so an entity-expansion bomb is refused rather than parsed.
* **Values, not formulas.** The workbook is read with `data_only`, so a cell
  holding `=HYPERLINK(...)` gives its last computed value, never the formula.
* **Bounded.** At most `MAX_ROWS` data rows, and only the columns a caller
  names; a cell's text is stripped and capped. The zip is sized before it is
  opened (`MAX_UNPACKED_BYTES`) and no sheet is walked past Excel's last row
  (`MAX_SHEET_ROWS`), blank rows counted, because either can be small on disk.

Writing builds a template: a header row, optional example rows, a dropdown on
each column with a fixed set of values, and a sheet of instructions.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from cmp.core.errors import ValidationFailed

#: More than this is a migration, not an import.
MAX_ROWS = 1000
#: No registry value needs more; a longer cell is a mistake or an attack.
MAX_CELL_CHARS = 2000
#: What all the parts of a workbook may come to, unpacked. The largest list we
#: take is a few megabytes of XML, while a small zip can unpack to gigabytes and
#: `load_workbook` holds the shared strings in memory whole.
MAX_UNPACKED_BYTES = 200 * 1024 * 1024
#: Excel's last row. A row's number is whatever the file says, and the reader
#: walks the gap before it a row at a time, so a blank row costs what a full one
#: does. No real sheet goes further, however many blank rows it trails.
MAX_SHEET_ROWS = 1_048_576

_UNREADABLE = "The workbook could not be read. Save it again as .xlsx from Excel and upload it."

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True, slots=True)
class Column:
    """One column of a template, and how its header is recognised."""

    key: str
    header: str
    required: bool = False
    #: Shown in the instructions sheet.
    help: str = ""
    #: A fixed set of values: a dropdown in the template.
    choices: tuple[str, ...] = ()
    width: int = 24
    #: Other header texts that mean this column.
    aliases: tuple[str, ...] = ()
    #: Formatted as text in the template, so Excel keeps what is typed as typed:
    #: left to itself it makes a number of +91 98765 43210, and drops the plus.
    text: bool = False


@dataclass(frozen=True, slots=True)
class SheetSpec:
    title: str
    columns: tuple[Column, ...]
    examples: Sequence[Sequence[Any]] = field(default_factory=tuple)


def normalise_heading(text: object) -> str:
    """'Legal name *' -> 'legal name'; 'Security confirmed on (YYYY-MM-DD)' -> its words."""
    out = str(text or "").replace("*", " ").lower()
    if "(" in out:
        out = out.split("(", 1)[0]
    return " ".join(out.replace("_", " ").split())


def _cell(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()[:MAX_CELL_CHARS]
        return value or None
    return value


def match_headings(
    header: Sequence[object], columns: Sequence[Column]
) -> tuple[dict[int, Column], list[str]]:
    """Which column of a sheet is which of `columns`, by its place in the row,
    and the headings none of them took. A column named twice is taken once."""
    wanted: dict[str, Column] = {}
    for col in columns:
        for text in (col.header, col.key, *col.aliases):
            wanted[normalise_heading(text)] = col
    position: dict[int, Column] = {}
    others: list[str] = []
    for index, heading in enumerate(header):
        match = wanted.get(normalise_heading(heading))
        if match is not None and match not in position.values():
            position[index] = match
        elif str(heading or "").strip():
            others.append(str(heading).strip())
    return position, others


def _check_unpacked(payload: bytes) -> None:
    """Refuse a zip that would unpack past the budget, before anything unpacks
    it. The sizes are the zip's own word, and `zipfile` holds a member to it:
    one that runs on fails its check rather than filling memory."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        unpacked = sum(member.file_size for member in archive.infolist())
    if unpacked > MAX_UNPACKED_BYTES:
        raise ValidationFailed(
            "This workbook is too large to read. Split it into smaller files.", field="file"
        )


def read_rows(
    payload: bytes,
    *,
    columns: Sequence[Column],
    sheet: str | None = None,
    max_rows: int | None = None,
    check_headings: Callable[[set[str], list[str]], None] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """The data rows of one sheet as (spreadsheet row number, {column key: value}).

    The first sheet whose title matches `sheet` (any case), else the first
    sheet. The first row is the header. Rows with nothing in them are skipped.
    At most `max_rows` data rows, `MAX_ROWS` unless the caller says otherwise.
    `check_headings`, if given, sees the keys found and the headings left over
    before any row is read, and raises if the sheet will not do.
    """
    limit = max_rows or MAX_ROWS
    if not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValidationFailed(
            "That is not an Excel workbook (.xlsx). Save the file as .xlsx and upload it again.",
            field="file",
        )
    try:
        _check_unpacked(payload)
        book = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except ValidationFailed:
        raise
    except Exception as exc:  # a corrupt or hostile file - say so, plainly
        raise ValidationFailed(_UNREADABLE, field="file") from exc
    try:
        if not book.worksheets:
            raise ValidationFailed(
                "The workbook has no sheets in it: the first row must be the headings.",
                field="file",
            )
        names = {name.lower(): name for name in book.sheetnames}
        title = names.get(sheet.lower()) if sheet else None
        ws = book[title] if title else book.worksheets[0]
        rows = ws.iter_rows(values_only=True)
        header = next(rows, None)
        if not header:
            raise ValidationFailed(
                "The sheet is empty: the first row must be the headings.", field="file"
            )

        position, others = match_headings(header, columns)
        missing = [c.header for c in columns if c.required and c not in position.values()]
        if missing:
            raise ValidationFailed(
                f"The sheet '{ws.title}' is missing the column(s): {', '.join(missing)}. "
                "Download the template to see the headings it expects.",
                field="file",
            )
        if check_headings is not None:
            check_headings({c.key for c in position.values()}, others)

        out: list[tuple[int, dict[str, Any]]] = []
        for number, values in enumerate(rows, start=2):
            if number > MAX_SHEET_ROWS:
                raise ValidationFailed(
                    f"The sheet runs past row {MAX_SHEET_ROWS:,}, the last Excel has. "
                    "Save it again from Excel and upload it.",
                    field="file",
                )
            record = {
                col.key: _cell(values[index]) if index < len(values) else None
                for index, col in position.items()
            }
            if all(v is None for v in record.values()):
                continue
            if len(out) >= limit:
                raise ValidationFailed(
                    f"The sheet has more than {limit:,} rows. Split it into smaller files.",
                    field="file",
                )
            out.append((number, record))
        return out
    except ValidationFailed:
        raise
    except Exception as exc:  # a sheet is read as it is walked, not on opening
        raise ValidationFailed(_UNREADABLE, field="file") from exc
    finally:
        book.close()


_HEADER_FILL = PatternFill("solid", fgColor="1F5C9E")
_REQUIRED_FILL = PatternFill("solid", fgColor="0E3A6B")


def build_workbook(sheets: Iterable[SheetSpec], *, instructions: Sequence[str] = ()) -> bytes:
    """A template: one sheet per spec, with dropdowns, and an instructions sheet."""
    book = Workbook()
    book.remove(book.active)
    specs = list(sheets)
    for spec in specs:
        ws = book.create_sheet(spec.title)
        for index, col in enumerate(spec.columns, start=1):
            cell = ws.cell(
                row=1, column=index, value=f"{col.header} *" if col.required else col.header
            )
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = _REQUIRED_FILL if col.required else _HEADER_FILL
            cell.alignment = Alignment(vertical="center")
            ws.column_dimensions[get_column_letter(index)].width = col.width
            if col.text:
                ws.column_dimensions[get_column_letter(index)].number_format = "@"
            if col.choices:
                letter = get_column_letter(index)
                rule = DataValidation(
                    type="list",
                    formula1='"' + ",".join(col.choices) + '"',
                    allow_blank=not col.required,
                    showErrorMessage=True,
                    errorTitle=col.header,
                    error=f"Choose one of: {', '.join(col.choices)}",
                )
                rule.add(f"{letter}2:{letter}{MAX_ROWS + 1}")
                ws.add_data_validation(rule)
        for r, row in enumerate(spec.examples, start=2):
            for c, value in enumerate(row, start=1):
                cell = ws.cell(row=r, column=c, value=value)
                if isinstance(value, date | datetime):
                    cell.number_format = "yyyy-mm-dd"
        ws.freeze_panes = "A2"
        ws.row_dimensions[1].height = 22

    guide = book.create_sheet("How to fill")
    guide.column_dimensions["A"].width = 30
    guide.column_dimensions["B"].width = 12
    guide.column_dimensions["C"].width = 90
    line = 1
    for text in instructions:
        guide.cell(row=line, column=1, value=text).font = Font(bold=line == 1)
        line += 1
    for spec in specs:
        line += 1
        guide.cell(row=line, column=1, value=f"Sheet: {spec.title}").font = Font(bold=True, size=12)
        line += 1
        for title, value in (("Column", 1), ("Required", 2), ("What to put in it", 3)):
            guide.cell(row=line, column=value, value=title).font = Font(bold=True)
        line += 1
        for col in spec.columns:
            allowed = f" Allowed: {', '.join(col.choices)}." if col.choices else ""
            guide.cell(row=line, column=1, value=col.header)
            guide.cell(row=line, column=2, value="Yes" if col.required else "No")
            guide.cell(row=line, column=3, value=f"{col.help}{allowed}").alignment = Alignment(
                wrap_text=True, vertical="top"
            )
            line += 1
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
