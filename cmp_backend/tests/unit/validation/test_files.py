"""Naming what somebody uploaded, so a refusal is something they can act on.

The notice importer reads a `.docx`, which is a zip, and refuses anything that
is not one. That refusal used to say only what the file was not — which is no
help at all to somebody holding a document Word itself produced, and actively
misleading for the one mistake that is not carelessness: a `.doc`. Word calls
both of them a Word document, and only one of them is a zip.

Nothing here decides whether a file is accepted. The caller has already decided
to refuse by the time it asks what the file was, so a wrong guess costs a
slightly misleading sentence and never a wrong verdict.
"""

from __future__ import annotations

import pathlib

import pytest

from cmp.api.routers.v1.notices import _not_a_docx
from cmp.validation import describe_format

FIXTURE = pathlib.Path(__file__).parents[2] / "fixtures" / "notice_filled.docx"


class TestDescribeFormat:
    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            (b"%PDF-1.7\n", "a PDF"),
            (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "a .doc, the format Word used before 2007"),
            (b"{\\rtf1\\ansi", "an RTF document"),
            (b"\x89PNG\r\n\x1a\n", "a PNG image"),
            (b"\xff\xd8\xff\xe0", "a JPEG image"),
            (b"II*\x00", "a TIFF image"),
            (b"MM\x00*", "a TIFF image"),
            (b"<?xml version='1.0'?>", "an XML file"),
        ],
    )
    def test_it_names_what_people_upload_by_mistake(self, payload: bytes, expected: str) -> None:
        assert describe_format(payload) == expected

    def test_a_format_it_does_not_know_is_not_guessed_at(self) -> None:
        """Silence beats invention: the sentence then says what the file is not,
        which is still true, rather than something confidently wrong."""
        assert describe_format(b"\x00\x01\x02\x03nothing in particular") is None
        assert describe_format(b"") is None

    def test_a_real_docx_is_not_named_as_anything_else(self) -> None:
        """A zip is not in the table, so the one file that should be accepted is
        never described as a mistake."""
        assert describe_format(FIXTURE.read_bytes()) is None


class TestTheRefusal:
    def test_a_doc_is_answered_with_the_menu_item_that_fixes_it(self) -> None:
        """The person has a Word document and did nothing wrong. What they need
        is not another file, it is Save As."""
        message = _not_a_docx(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        assert ".doc" in message
        assert "Save As" in message
        assert ".docx" in message

    def test_a_pdf_is_named_and_the_reason_given(self) -> None:
        """Naming it matters: somebody who exported to PDF believes they have
        uploaded the notice, and the words are what cannot be read out of it."""
        message = _not_a_docx(b"%PDF-1.7\n")
        assert "a PDF" in message
        assert "cannot be" in message

    def test_an_unknown_file_still_says_what_to_do(self) -> None:
        message = _not_a_docx(b"\x00\x01\x02\x03")
        assert "not a .docx file" in message
        assert "template" in message
