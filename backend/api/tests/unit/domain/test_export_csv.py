"""A cell that a spreadsheet would run is written so that it is only read.

Quoting a comma is not the same as neutralising a formula: `=HYPERLINK(...)`
survives CSV quoting intact and Excel evaluates it on open. Free-text fields
are prefixed with an apostrophe when they begin with a formula character; a
mobile number begins with `+` on purpose and is validated to be digits after
it, so it is left alone.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import pytest

from cmp.domain.consent.service import receipt_contact
from cmp.domain.exchange.service import EXPORT_COLUMNS, _text_cell, _write_csv


class TestTextCell:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ('=HYPERLINK("http://x","open")', '\'=HYPERLINK("http://x","open")'),
            ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
            ("-2+3", "'-2+3"),
            ("@SUM(A1)", "'@SUM(A1)"),
            ("\tstart", "'\tstart"),
            ("Asha Rao", "Asha Rao"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_formula_leaders_are_neutralised(self, value: object, expected: str) -> None:
        assert _text_cell(value) == expected


class TestWriteCsv:
    def test_the_project_name_is_neutralised_on_the_empty_export(self) -> None:
        project: dict[str, Any] = {
            "project_name": "=1+1",
            "project_uuid": "6f1a2b3c-0000-4000-8000-000000000000",
        }
        payload = _write_csv(project, [])
        rows = list(csv.reader(io.StringIO(payload)))
        assert rows[0] == list(EXPORT_COLUMNS)
        assert rows[1][0] == "'=1+1"


class TestReceiptContact:
    def test_a_verified_email_comes_first(self) -> None:
        user = {
            "email": "a@example.org",
            "email_verified_at": "2026-09-01",
            "mobile": "+919000000001",
            "mobile_verified_at": "2026-09-01",
        }
        assert receipt_contact(user) == "a@example.org"

    def test_a_mobile_only_principal_gets_the_receipt_on_the_mobile(self) -> None:
        user = {
            "email": None,
            "email_verified_at": None,
            "mobile": "+919000000001",
            "mobile_verified_at": "2026-09-01",
        }
        assert receipt_contact(user) == "+919000000001"

    def test_an_unverified_email_is_skipped_for_a_verified_mobile(self) -> None:
        user = {
            "email": "typo@example.org",
            "email_verified_at": None,
            "mobile": "+919000000001",
            "mobile_verified_at": "2026-09-01",
        }
        assert receipt_contact(user) == "+919000000001"

    def test_a_legacy_row_with_no_stamps_still_gets_a_receipt(self) -> None:
        user = {
            "email": "old@example.org",
            "email_verified_at": None,
            "mobile": None,
            "mobile_verified_at": None,
        }
        assert receipt_contact(user) == "old@example.org"

    def test_nothing_on_file_means_no_receipt(self) -> None:
        assert receipt_contact({"email": None, "mobile": None}) is None
