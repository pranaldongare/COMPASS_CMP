"""The office's own records over HTTP: the trail, the message words, the
collection register, and the notice's later life.

The audit trail is where a leak would be permanent, so it gets the closest
look: every search, the summary, the lookup that finds a person, the CSV, and
one entry, all checked for words that should not be there.
"""

from __future__ import annotations

import csv
import io
import pathlib
from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import SEALED, call
from tests.http.world import World, build

FIXTURES = pathlib.Path(__file__).parents[1] / "fixtures"


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


class TestTheAuditTrail:
    async def test_search_summary_and_one_entry(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        page = await call(http, "GET", "/audit", session=world.dpo, params={"limit": 50})
        items = page.json()["items"]
        assert items, "the world just wrote a few hundred rows"
        for row in items:
            for key, value in (row.get("detail") or {}).items():
                assert key not in ("email", "mobile", "full_name", "contact"), (row, key)
                if isinstance(value, str):
                    assert "@" not in value or value.startswith("SE::"), (row["event_type"], key)
        entry = await call(
            http,
            "GET",
            f"/audit/{items[0]['log_uuid']}",
            template="/audit/{log_uuid}",
            session=world.dpo,
        )
        assert entry.json()["log_uuid"] == items[0]["log_uuid"]
        # Filters the console sends: an event kind, an actor, a subject.
        await call(http, "GET", "/audit", session=world.admin, params={"q": "consent"})
        await call(
            http,
            "GET",
            "/audit",
            session=world.dpo,
            params={"subject": world.principal.uuid},
        )
        summary = await call(http, "GET", "/audit/summary", session=world.dpo, params={"days": 1})
        assert summary.json()["total"] >= len(items)

    async def test_the_lookup_finds_a_person_by_the_whole_contact_only(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        hits = await call(
            http,
            "GET",
            "/audit/lookup",
            session=world.dpo,
            params={"kind": "data_subject", "q": world.principal_email},
        )
        assert [h["uuid"] for h in hits.json()] == [world.principal.uuid]
        assert hits.json()[0]["label"].startswith("SE::"), "the name comes back sealed"
        fragment = await call(
            http,
            "GET",
            "/audit/lookup",
            session=world.dpo,
            params={"kind": "data_subject", "q": world.principal_email.split("@")[0][:6]},
        )
        assert fragment.json() == []
        staff = await call(
            http,
            "GET",
            "/audit/lookup",
            session=world.admin,
            params={"kind": "staff", "q": plain(world.dpo.user["email"])},
        )
        assert [h["uuid"] for h in staff.json()] == [world.dpo.uuid]
        name = (
            await call(
                http,
                "GET",
                f"/projects/{world.project_uuid}",
                template="/projects/{project_uuid}",
                session=world.dpo,
            )
        ).json()["project_name"]
        projects = await call(
            http, "GET", "/audit/lookup", session=world.dpo, params={"kind": "project", "q": name}
        )
        assert any(h["uuid"] == world.project_uuid for h in projects.json())

    async def test_the_csv_carries_no_words_of_anybody(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        """From this world's first row on.

        Rows written before addresses were indexed (ADR 0015) carry them as
        they were: the chain hashes `detail_json`, so rewriting them would
        break the one property the trail exists for. What can be asserted is
        that nothing written since carries a word of anybody.
        """
        out = await call(
            http,
            "GET",
            "/audit/export.csv",
            session=world.dpo,
            params={"from": world.built_at},
            check_sealed=False,
        )
        assert out.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(out.text)))
        assert rows
        text = out.text
        assert world.principal_email not in text
        assert world.principal_mobile not in text
        assert plain(world.dpo.user["email"]) not in text
        assert "127.0.0.1" not in text, "addresses travel as their index"


class TestTheMessageWords:
    async def test_read_preview_replace_and_reset(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        listed = await call(http, "GET", "/messages", session=world.dpo)
        message = next(
            m for m in listed.json() if any(c["channel"] == "email" for c in m["channels"])
        )
        key = message["key"]
        one = await call(
            http, "GET", f"/messages/{key}", template="/messages/{key}", session=world.dpo
        )
        email = next(c for c in one.json()["channels"] if c["channel"] == "email")
        words = {"subject": email["subject"], "body": email["body"] + "\n\nWith our thanks."}
        preview = await call(
            http,
            "POST",
            f"/messages/{key}/email/preview",
            template="/messages/{key}/{channel}/preview",
            session=world.dpo,
            json=words,
        )
        assert "{{" not in preview.json()["body"], "sample values fill every variable"
        assert "With our thanks." in preview.json()["body"]
        saved = await call(
            http,
            "PUT",
            f"/messages/{key}/email",
            template="/messages/{key}/{channel}",
            session=world.admin,
            json=words,
        )
        assert next(c for c in saved.json()["channels"] if c["channel"] == "email")[
            "body"
        ].endswith("With our thanks.")
        reset = await call(
            http,
            "DELETE",
            f"/messages/{key}/email",
            template="/messages/{key}/{channel}",
            session=world.admin,
        )
        assert (
            next(c for c in reset.json()["channels"] if c["channel"] == "email")["body"]
            == email["body"]
        )


class TestTheCollectionRegister:
    async def test_the_batch_the_collection_and_its_assets(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        batch = await call(
            http,
            "GET",
            f"/imports/{world.batch_uuid}",
            template="/imports/{batch_uuid}",
            session=world.dco,
        )
        assert batch.json()["accepted_rows"] == 2
        collection = await call(
            http,
            "GET",
            f"/collections/{world.collection_uuid}",
            template="/collections/{collection_uuid}",
            session=world.dco,
        )
        assert collection.json()["mapped_asset_count"] == 2
        assets = await call(
            http,
            "GET",
            f"/collections/{world.collection_uuid}/assets",
            template="/collections/{collection_uuid}/assets",
            session=world.dpo,
        )
        assert len(assets.json()) == 2
        for asset in assets.json():
            for key in ("subject_name", "full_name", "email", "mobile"):
                if asset.get(key):
                    assert asset[key].startswith("SE::"), (key, asset)
        # A researcher may see their project's collections but not the people in them.
        await call(
            http,
            "GET",
            f"/collections/{world.collection_uuid}/assets",
            template="/collections/{collection_uuid}/assets",
            session=world.rnd,
            expect=(200, 403),
        )


class TestANoticesLaterLife:
    async def test_edit_copy_import_and_publish_on_a_fresh_project(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        tag = fresh("N")
        project = await call(
            http,
            "POST",
            "/projects",
            session=world.rnd,
            expect=201,
            json={
                "project_name": f"Copy Study {tag}",
                "description": "A second study.",
                "processor_uuids": [world.processor_uuid],
                "requesting_team": "Computer Vision",
            },
        )
        puuid = project.json()["project_uuid"]

        # Start from the standing notice, then edit the draft.
        copied = await call(
            http,
            "POST",
            f"/projects/{puuid}/notices/copy",
            template="/projects/{project_uuid}/notices/copy",
            session=world.dpo,
            expect=(200, 201),
            json={"source_notice_uuid": world.notice_uuid},
        )
        nuuid = copied.json()["notice_uuid"]
        edited = await call(
            http,
            "PUT",
            f"/notices/{nuuid}",
            template="/notices/{notice_uuid}",
            session=world.dpo,
            json={"dpo_contact": "privacy@example.org", "note": "Copied for the second study."},
        )
        assert edited.json()["dpo_contact"] == "privacy@example.org"

        # The document route: a dry run first, then the import that replaces the draft.
        document = (FIXTURES / "notice_filled.docx").read_bytes()
        checked = await call(
            http,
            "POST",
            f"/projects/{puuid}/notices/import/validate",
            template="/projects/{project_uuid}/notices/import/validate",
            session=world.dpo,
            files={
                "document": (
                    "notice.docx",
                    document,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert checked.json()["ok"] is True, checked.json()
        assert checked.json()["replaces_draft"], "the dry run names the draft it would replace"
        imported = await call(
            http,
            "POST",
            f"/projects/{puuid}/notices/import",
            template="/projects/{project_uuid}/notices/import",
            session=world.dpo,
            expect=(200, 201),
            files={
                "document": (
                    "notice.docx",
                    document,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        nuuid = imported.json()["notice_uuid"]

        # Publication: the purposes it brought have to be activated and the text approved.
        await call(
            http,
            "POST",
            f"/notices/{nuuid}/purposes/activate",
            template="/notices/{notice_uuid}/purposes/activate",
            session=world.dpo,
            expect=(200, 204),
            check_sealed=False,
        )
        languages = await call(
            http,
            "GET",
            f"/notices/{nuuid}/languages",
            template="/notices/{notice_uuid}/languages",
            session=world.dpo,
        )
        for lang in languages.json():
            await call(
                http,
                "POST",
                f"/notices/{nuuid}/languages/{lang['language_code']}/approve",
                template="/notices/{notice_uuid}/languages/{code}/approve",
                session=world.dpo,
                expect=(200, 204),
            )
        published = await call(
            http,
            "POST",
            f"/notices/{nuuid}/publish",
            template="/notices/{notice_uuid}/publish",
            session=world.dpo,
        )
        assert published.json()["status"] == "published"


class TestClosingTheProject:
    async def test_the_world_closes_last(self, http: httpx.AsyncClient, world: World) -> None:
        closed = await call(
            http,
            "POST",
            f"/projects/{world.project_uuid}/close",
            template="/projects/{project_uuid}/close",
            session=world.dpo,
            json={"to": "closed", "reason": "The study is over."},
        )
        assert closed.json()["to"] == "closed"


def test_sealed_contract_names_only_columns_that_exist() -> None:
    """A typo in `SEALED` would silently check nothing.

    Every name in the contract is a sealed column, or a join of one: a
    person's name (`*_name`), email (`*_email`), mobile (`*_mobile`) or
    contact (`*_contact`) read through a foreign key.
    """
    from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS

    columns = {c for cols in ENCRYPTED_FIELDS.values() for c in cols}
    joined = {
        f
        for f in SEALED
        if f.endswith(("_name", "_email", "_mobile", "_contact")) and f.split("_")[0]
    }
    unknown = SEALED - columns - joined
    assert not unknown, unknown
