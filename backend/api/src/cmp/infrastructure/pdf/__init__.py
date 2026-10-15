"""PDF documents, built from plain blocks (2026-10-15).

The first PDF the platform produces is the consent record an auditor keeps
(`cmp.domain.consent.record`). This module knows nothing of consent: it lays
out headings, fields, tables and verbatim text, in any of the languages the
platform stores, and returns the bytes.

Two things it has to get right that a simpler PDF library gets wrong:

* **Indian scripts.** A notice served in Hindi, Tamil or Kannada is evidence
  only if the PDF shows the words as they were shown. Those scripts join and
  reorder letters, which needs a shaping engine (HarfBuzz, through
  `uharfbuzz`) and a font per script. The fonts are bundled in `fonts/`, so
  the output does not depend on what the server has installed.
* **Nothing from outside the document.** No network fetch, no system font, no
  image from a URL: the bytes depend on the blocks alone, so the same record
  gives the same pages on any server.

A document may also carry attachments: files embedded in the PDF itself, for
a reader that wants the data rather than the page.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TableCellFillMode, XPos, YPos
from fpdf.fonts import FontFace

FONTS = Path(__file__).parent / "fonts"

#: The Latin face for labels and English text; the scripts follow as fallbacks,
#: tried glyph by glyph, so a line mixing Hindi and "DPDP Act 2023" renders both.
_BASE = "NotoSans"
_SCRIPTS = ("Devanagari", "Bengali", "Gujarati", "Kannada", "Tamil", "Telugu")

_INK = (31, 41, 55)
_MUTED = (100, 110, 125)
_ACCENT = (31, 92, 158)
_RULE = (215, 220, 228)
_PANEL = (244, 246, 249)
_TONES = {
    "success": (22, 120, 72),
    "warning": (166, 105, 0),
    "danger": (180, 35, 45),
    "neutral": (90, 100, 115),
}


# ---------------------------------------------------------------- blocks
@dataclass(frozen=True, slots=True)
class Heading:
    text: str


@dataclass(frozen=True, slots=True)
class Paragraph:
    text: str
    muted: bool = False
    size: float = 9.5


@dataclass(frozen=True, slots=True)
class Banner:
    """One line that says what the document is about, large: a status."""

    label: str
    value: str
    tone: str = "neutral"
    note: str = ""


@dataclass(frozen=True, slots=True)
class Fields:
    """Label and value, two columns."""

    rows: Sequence[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class Table:
    headers: Sequence[str]
    rows: Sequence[Sequence[str]]
    #: Relative column widths; equal when empty.
    widths: Sequence[int] = ()


@dataclass(frozen=True, slots=True)
class Verbatim:
    """Text reproduced exactly, line breaks kept, in a panel: a quotation."""

    text: str
    caption: str = ""


Block = Heading | Paragraph | Banner | Fields | Table | Verbatim


@dataclass(frozen=True, slots=True)
class Attachment:
    name: str
    data: bytes
    mime_type: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Document:
    title: str
    blocks: Sequence[Block]
    created_at: datetime
    subtitle: str = ""
    #: Printed at the foot of every page, beside the page number.
    footer: str = ""
    #: Printed at the head of every page.
    header: str = ""
    subject: str = ""
    keywords: Sequence[str] = ()
    attachments: Sequence[Attachment] = field(default_factory=tuple)


# ---------------------------------------------------------------- render
@cache
def _font_files() -> tuple[tuple[str, str, Path], ...]:
    files = [
        (_BASE, "", FONTS / "NotoSans-Regular.ttf"),
        (_BASE, "B", FONTS / "NotoSans-Bold.ttf"),
    ]
    files += [(f"{_BASE}{s}", "", FONTS / f"NotoSans{s}-Regular.ttf") for s in _SCRIPTS]
    missing = [str(p) for _, _, p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"PDF fonts missing: {', '.join(missing)}")
    return tuple(files)


class _Pdf(FPDF):
    def __init__(self, doc: Document) -> None:
        super().__init__(orientation="portrait", unit="mm", format="A4")
        self._doc = doc
        self.set_margins(18, 20, 18)
        self.set_auto_page_break(auto=True, margin=18)
        for family, style, path in _font_files():
            self.add_font(family, style, str(path))
        self.set_fallback_fonts([f"{_BASE}{s}" for s in _SCRIPTS])
        self.set_text_shaping(True)
        self.alias_nb_pages()

    def header(self) -> None:
        if not self._doc.header:
            return
        self.set_y(9)
        self.set_font(_BASE, "", 7.5)
        self.set_text_color(*_MUTED)
        self.cell(0, 4, self._doc.header, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.6)
        self.line(self.l_margin, 14, self.w - self.r_margin, 14)
        self.set_y(20)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_draw_color(*_RULE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y() - 1.5, self.w - self.r_margin, self.get_y() - 1.5)
        self.set_font(_BASE, "", 7)
        self.set_text_color(*_MUTED)
        width = self.w - self.l_margin - self.r_margin
        self.cell(width * 0.8, 4, self._doc.footer)
        self.cell(width * 0.2, 4, f"Page {self.page_no()} of {{nb}}", align="R")


def _line(pdf: FPDF, height: float, text: str) -> None:
    # Ragged right, never justified: justification stretches the spaces of a
    # quoted notice, and the words should sit as they were written.
    pdf.multi_cell(0, height, text, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _heading(pdf: FPDF, block: Heading) -> None:
    pdf.ln(3)
    if pdf.get_y() > pdf.h - 60:  # never a heading alone at the foot of a page
        pdf.add_page()
    pdf.set_font(_BASE, "B", 11.5)
    pdf.set_text_color(*_ACCENT)
    _line(pdf, 6, block.text)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin, pdf.get_y() + 0.5, pdf.w - pdf.r_margin, pdf.get_y() + 0.5)
    pdf.ln(2.5)


def _paragraph(pdf: FPDF, block: Paragraph) -> None:
    pdf.set_font(_BASE, "", block.size)
    pdf.set_text_color(*(_MUTED if block.muted else _INK))
    _line(pdf, block.size * 0.5, block.text)
    pdf.ln(1.5)


def _banner(pdf: FPDF, block: Banner) -> None:
    colour = _TONES.get(block.tone, _TONES["neutral"])
    top = pdf.get_y()
    pdf.set_fill_color(*_PANEL)
    height = 15 if block.note else 11
    pdf.rect(pdf.l_margin, top, pdf.w - pdf.l_margin - pdf.r_margin, height, style="F")
    pdf.set_fill_color(*colour)
    pdf.rect(pdf.l_margin, top, 1.6, height, style="F")
    pdf.set_xy(pdf.l_margin + 5, top + 2)
    pdf.set_font(_BASE, "", 8)
    pdf.set_text_color(*_MUTED)
    pdf.cell(32, 7, block.label.upper())
    pdf.set_font(_BASE, "B", 13)
    pdf.set_text_color(*colour)
    pdf.cell(0, 7, block.value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if block.note:
        pdf.set_x(pdf.l_margin + 5)
        pdf.set_font(_BASE, "", 8.5)
        pdf.set_text_color(*_INK)
        pdf.cell(0, 4.5, block.note)
    pdf.set_y(top + height + 3)


def _table(
    pdf: FPDF, headers: Sequence[str], rows: Sequence[Sequence[str]], widths: Sequence[int]
) -> None:
    pdf.set_font(_BASE, "", 8.5)
    pdf.set_text_color(*_INK)
    pdf.set_draw_color(*_RULE)
    pdf.set_fill_color(255, 255, 255)
    pdf.set_line_width(0.2)
    with pdf.table(
        col_widths=tuple(widths) or None,
        cell_fill_mode=TableCellFillMode.NONE,
        first_row_as_headings=bool(headers),
        headings_style=FontFace(emphasis="BOLD", color=_MUTED, fill_color=_PANEL),
        borders_layout="HORIZONTAL_LINES",
        line_height=4.6,
        padding=(1.6, 2, 1.6, 2),
        text_align="LEFT",
        v_align="TOP",
    ) as table:
        if headers:
            table.row(list(headers))
        for values in rows:
            table.row([str(v) for v in values])
    pdf.ln(3)


def _fields(pdf: FPDF, block: Fields) -> None:
    pdf.set_font(_BASE, "", 8.5)
    pdf.set_text_color(*_INK)
    pdf.set_draw_color(*_RULE)
    pdf.set_fill_color(255, 255, 255)
    # Styles go on the cells: the table is drawn when its block closes, so a
    # colour set between rows would apply to none of them.
    label_style = FontFace(color=_MUTED)
    with pdf.table(
        col_widths=(30, 70),
        cell_fill_mode=TableCellFillMode.NONE,
        first_row_as_headings=False,
        borders_layout="HORIZONTAL_LINES",
        line_height=4.6,
        padding=(1.4, 2, 1.4, 2),
        text_align="LEFT",
        v_align="TOP",
    ) as table:
        for label, value in block.rows:
            row = table.row()
            row.cell(label, style=label_style)
            row.cell(value)
    pdf.ln(3)


def _verbatim(pdf: FPDF, block: Verbatim) -> None:
    if block.caption:
        pdf.set_font(_BASE, "", 8)
        pdf.set_text_color(*_MUTED)
        _line(pdf, 4.2, block.caption)
        pdf.ln(1)
    pdf.set_font(_BASE, "", 9)
    pdf.set_text_color(*_INK)
    pdf.set_fill_color(*_PANEL)
    # A panel across pages: multi_cell fills each line it writes, so a notice
    # longer than a page stays visibly one quotation.
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0,
        4.8,
        block.text.replace("\r\n", "\n").strip("\n"),
        fill=True,
        align="L",
        padding=(3, 4, 3, 4),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)


def render(doc: Document) -> bytes:
    """The document as PDF bytes."""
    pdf = _Pdf(doc)
    pdf.set_title(doc.title)
    pdf.set_subject(doc.subject or doc.title)
    pdf.set_creator("COMPASS Consent Management Platform")
    pdf.set_producer("COMPASS CMP")
    if doc.keywords:
        pdf.set_keywords(", ".join(doc.keywords))
    pdf.set_lang("en")
    pdf.set_creation_date(doc.created_at)
    for attachment in doc.attachments:
        pdf.embed_file(
            bytes=attachment.data,
            basename=attachment.name,
            mime_type=attachment.mime_type,
            modification_date=doc.created_at,
            desc=attachment.description,
        )

    pdf.add_page()
    pdf.set_font(_BASE, "B", 17)
    pdf.set_text_color(*_INK)
    _line(pdf, 8, doc.title)
    if doc.subtitle:
        pdf.set_font(_BASE, "", 9.5)
        pdf.set_text_color(*_MUTED)
        _line(pdf, 5, doc.subtitle)
    pdf.ln(3)

    for block in doc.blocks:
        match block:
            case Heading():
                _heading(pdf, block)
            case Paragraph():
                _paragraph(pdf, block)
            case Banner():
                _banner(pdf, block)
            case Fields():
                _fields(pdf, block)
            case Table():
                _table(pdf, block.headers, block.rows, block.widths)
            case Verbatim():
                _verbatim(pdf, block)
    return bytes(pdf.output())
