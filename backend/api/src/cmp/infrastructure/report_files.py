"""A report's content as a file: PDF, Excel or CSV (ADR 0045).

The analytics build a report as plain content - a title, what it is about,
and sections of tables - and this turns it into the format asked for. The PDF
is the platform's own document layout (`cmp.infrastructure.pdf`), fonts and
all; the workbook has a sheet per section and a first sheet that says what
the report is; the CSV is every section one after the other.

Every text cell is neutralised against spreadsheet formulas (`text_cell`), in
the workbook and the CSV alike: a project's name that starts with `=` is a
name, never a formula.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cmp.core.csv_safety import text_cell

MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv; charset=utf-8",
}


@dataclass(frozen=True, slots=True)
class Section:
    heading: str
    headers: Sequence[str]
    rows: Sequence[Sequence[Any]]
    intro: str = ""
    #: Relative column widths in the PDF; equal when empty.
    widths: Sequence[int] = ()


@dataclass(frozen=True, slots=True)
class Content:
    title: str
    subtitle: str
    #: What the report is: period, office, who asked, when, definitions version.
    about: Sequence[tuple[str, str]]
    sections: Sequence[Section]
    notes: Sequence[str] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    #: Printed at the foot of every PDF page.
    footer: str = "Figures only: no record about a person is in this report."


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int | float):
        return value
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return text_cell(value)


def _text(value: Any) -> str:
    v = _cell(value)
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def render(content: Content, fmt: str) -> bytes:
    if fmt == "pdf":
        return render_pdf(content)
    if fmt == "xlsx":
        return render_xlsx(content)
    if fmt == "csv":
        return render_csv(content)
    raise ValueError(f"no such format: {fmt}")


def render_pdf(content: Content) -> bytes:
    from cmp.core.config import settings
    from cmp.infrastructure import pdf

    blocks: list[pdf.Block] = [pdf.Fields(rows=[(k, v) for k, v in content.about])]
    for section in content.sections:
        blocks.append(pdf.Heading(section.heading))
        if section.intro:
            blocks.append(pdf.Paragraph(section.intro, muted=True))
        if section.rows:
            blocks.append(
                pdf.Table(
                    headers=list(section.headers),
                    rows=[[_text(c) for c in row] for row in section.rows],
                    widths=list(section.widths),
                )
            )
        else:
            blocks.append(pdf.Paragraph("Nothing in this period.", muted=True))
    for note in content.notes:
        blocks.append(pdf.Paragraph(note, muted=True, size=8))
    doc = pdf.Document(
        title=content.title,
        subtitle=content.subtitle,
        blocks=blocks,
        created_at=content.created_at,
        header=f"{settings.organisation_name} - {content.title}",
        footer=content.footer,
        subject=content.title,
    )
    return pdf.render(doc)


def render_xlsx(content: Content) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    book = Workbook()
    about = book.active
    assert about is not None
    about.title = "About"
    about.append([content.title])
    about["A1"].font = Font(bold=True, size=14)
    about.append([content.subtitle])
    about.append([])
    for k, v in content.about:
        about.append([k, text_cell(v)])
    for note in content.notes:
        about.append([])
        about.append([text_cell(note)])
    about.column_dimensions["A"].width = 28
    about.column_dimensions["B"].width = 80
    header_fill = PatternFill("solid", fgColor="1F6F4A")
    used: set[str] = {"About"}
    for section in content.sections:
        name = _sheet_name(section.heading, used)
        ws = book.create_sheet(name)
        if section.intro:
            ws.append([text_cell(section.intro)])
            ws.append([])
        ws.append(list(section.headers))
        header_row = ws.max_row
        for i in range(1, len(section.headers) + 1):
            cell = ws.cell(row=header_row, column=i)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = header_fill
            ws.column_dimensions[get_column_letter(i)].width = 22
        for row in section.rows:
            ws.append([_cell(c) for c in row])
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


def _sheet_name(heading: str, used: set[str]) -> str:
    base = "".join(ch for ch in heading if ch not in r"[]:*?/\\")[:28] or "Sheet"
    name, n = base, 2
    while name in used:
        name = f"{base[:25]} {n}"
        n += 1
    used.add(name)
    return name


def render_csv(content: Content) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([text_cell(content.title)])
    for k, v in content.about:
        w.writerow([text_cell(k), text_cell(v)])
    for section in content.sections:
        w.writerow([])
        w.writerow([text_cell(section.heading)])
        w.writerow([text_cell(h) for h in section.headers])
        for row in section.rows:
            w.writerow([_text(c) for c in row])
    # A byte-order mark, so Excel opens it as UTF-8 and a name in Devanagari
    # reads as written.
    return ("﻿" + buf.getvalue()).encode("utf-8")
