"""Processors and data sources from a workbook (2026-10-14).

All or nothing; a re-upload skips what is registered; a source names its
processor as a person would. Every row created is audited as the form's create
is, because it goes through the same service.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook

from cmp.core.errors import ValidationFailed
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.registry import imports

pytestmark = pytest.mark.integration

SAMPLES = Path(__file__).resolve().parents[4] / "docs" / "registry-import"

PROCESSOR_HEAD = (
    "Legal name *",
    "Type *",
    "Contract reference *",
    "Security confirmed on *",
    "In-house",
    "Country",
)
SOURCE_HEAD = (
    "Source code *",
    "Name *",
    "Role *",
    "Exchange mode *",
    "ID scheme",
    "Processor",
    "Authoritative for",
)


def _book(head: tuple[str, ...], *rows: tuple[Any, ...]) -> bytes:
    book = Workbook()
    ws = book.active
    assert ws is not None
    ws.append(list(head))
    for row in rows:
        ws.append(list(row))
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


async def _processor_names(conn: Any, prefix: str) -> list[str]:
    rows = await fetch_all(
        conn,
        "SELECT legal_name FROM processor WHERE legal_name LIKE %s ORDER BY legal_name",
        (prefix + "%",),
    )
    return [r["legal_name"] for r in rows]


async def test_a_check_writes_nothing_and_an_import_creates_and_audits(
    conn: Any, seeded: dict[str, Any]
) -> None:
    payload = _book(
        PROCESSOR_HEAD,
        ("ZZImport Lab One", "Lab", "MSA-ZZ-1", "2026-09-01", "No", "in"),
        ("ZZImport Tool Two", "tool", "DPA-ZZ-2", "01/08/2026", "yes", None),
    )
    check = await imports.processors(conn, payload=payload, apply=False)
    assert (check["applied"], check["created"], check["errors"]) == (False, 2, 0)
    assert [r["outcome"] for r in check["rows"]] == ["ready", "ready"]
    assert await _processor_names(conn, "ZZImport") == []

    done = await imports.processors(conn, payload=payload, apply=True)
    assert (done["applied"], done["created"]) == (True, 2)
    assert all(r["uuid"] for r in done["rows"])
    row = await fetch_one(
        conn,
        """SELECT type::text, is_in_house, location_country, security_confirmed_at::text AS d
             FROM processor WHERE legal_name = 'ZZImport Lab One'""",
    )
    assert row == {"type": "lab", "is_in_house": False, "location_country": "IN", "d": "2026-09-01"}
    audited = await fetch_one(
        conn,
        """SELECT count(*) AS n FROM audit_log
            WHERE event_type = 'processor.created'
              AND detail_json->>'legal_name' LIKE 'ZZImport%%'""",
    )
    assert audited and audited["n"] == 2


async def test_uploading_the_same_file_again_skips_what_is_registered(
    conn: Any, seeded: dict[str, Any]
) -> None:
    payload = _book(
        PROCESSOR_HEAD,
        ("ZZImport Again", "lab", "MSA-ZZ-3", "2026-09-01", "No", "IN"),
        ("test processor ltd", "lab", "CTR-TEST", "2026-09-01", "No", "IN"),
    )
    first = await imports.processors(conn, payload=payload, apply=True)
    assert [r["outcome"] for r in first["rows"]] == ["created", "skipped"]
    again = await imports.processors(conn, payload=payload, apply=True)
    assert [r["outcome"] for r in again["rows"]] == ["skipped", "skipped"]
    assert await _processor_names(conn, "ZZImport Again") == ["ZZImport Again"]


async def test_one_bad_row_refuses_the_whole_file(conn: Any, seeded: dict[str, Any]) -> None:
    payload = _book(
        PROCESSOR_HEAD,
        ("ZZImport Fine", "lab", "MSA-ZZ-4", "2026-09-01", "No", "IN"),
        ("ZZImport Future", "robot", "", "2999-01-01", "maybe", "India"),
        ("ZZImport Fine", "lab", "MSA-ZZ-5", "2026-09-01", "No", "IN"),
    )
    with pytest.raises(ValidationFailed) as caught:
        await imports.processors(conn, payload=payload, apply=True)
    assert caught.value.code == "import_rejected"
    report = caught.value.details
    assert report["errors"] == 2
    bad = report["rows"][1]
    assert bad["row"] == 3
    assert {p["column"] for p in bad["problems"]} == {
        "Type",
        "Contract reference",
        "Security confirmed on",
        "In-house",
        "Country",
    }
    assert report["rows"][2]["problems"][0]["message"] == "Also on row 2 of this sheet"
    assert await _processor_names(conn, "ZZImport") == []


async def test_a_source_names_its_processor_by_name_or_contract(
    conn: Any, seeded: dict[str, Any]
) -> None:
    admin = seeded["users"]["admin"]["id"]
    payload = _book(
        SOURCE_HEAD,
        (
            "ZZ-SRC-1",
            "By name",
            "collection",
            "File export",
            "Lab ID",
            "Test Processor Ltd",
            "gait_video, voice_recording",
        ),
        ("ZZ-SRC-2", "In-house", "identity", "api", None, None, None),
    )
    done = await imports.sources(conn, payload=payload, apply=True, user_id=admin)
    assert done["created"] == 2
    row = await fetch_one(
        conn,
        """SELECT s.exchange_mode::text AS mode, s.is_authoritative_for AS elements,
                  p.legal_name FROM data_source s LEFT JOIN processor p USING (processor_id)
            WHERE s.source_code = 'ZZ-SRC-1'""",
    )
    assert row == {
        "mode": "file_export",
        "elements": ["gait_video", "voice_recording"],
        "legal_name": "Test Processor Ltd",
    }

    again = await imports.sources(conn, payload=payload, apply=False, user_id=admin)
    assert [r["outcome"] for r in again["rows"]] == ["skipped", "skipped"]


async def test_a_processor_that_cannot_be_placed_is_an_error(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await conn.execute(
        "UPDATE processor SET status = 'suspended' WHERE processor_id = %s",
        (seeded["processors"]["in_house"]["processor_id"],),
    )
    payload = _book(
        SOURCE_HEAD,
        ("ZZ-SRC-3", "Nobody", "collection", "api", None, "No Such Processor", None),
        # Both seeded processors share this contract reference.
        ("ZZ-SRC-4", "Two of them", "collection", "api", None, "ctr-test", None),
        ("ZZ-SRC-5", "Suspended", "collection", "api", None, "Test Internal Team", None),
        ("bad code!", "Code", "sideways", "pigeon", None, None, None),
    )
    report = await imports.sources(
        conn, payload=payload, apply=False, user_id=seeded["users"]["admin"]["id"]
    )
    messages = [r["problems"][0]["message"] for r in report["rows"]]
    assert "No processor is registered" in messages[0]
    assert "names 2 processors" in messages[1]
    assert "suspended" in messages[2]
    assert {p["column"] for p in report["rows"][3]["problems"]} == {
        "Source code",
        "Role",
        "Exchange mode",
    }
    assert report["errors"] == 4


async def test_the_committed_samples_import_cleanly(conn: Any, seeded: dict[str, Any]) -> None:
    """docs/registry-import: the processors first, then the sources that name them."""
    processors = await imports.processors(
        conn, payload=(SAMPLES / "processors-sample.xlsx").read_bytes(), apply=True
    )
    assert processors["errors"] == 0 and processors["total"] == 5
    sources = await imports.sources(
        conn,
        payload=(SAMPLES / "data-sources-sample.xlsx").read_bytes(),
        apply=True,
        user_id=seeded["users"]["admin"]["id"],
    )
    assert sources["errors"] == 0 and sources["total"] == 6
