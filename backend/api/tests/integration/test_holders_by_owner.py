"""Who holds her data, when no record names a processor (0069, 2026-11-12).

"Find who holds the data" read an export, an asset and an activity's category
processors, and for a person whose project had none of them yet it found
nobody: the list was empty, with her consents on record. Every consent is
given against a project or an activity, and somebody answers for each. So:

* a project no record names a processor for is a DCO Admin's to answer - the
  role that routes its collection - and never the project's own Data
  Collection Owner (the product owner's decision). One DCO Admin is named;
  several are a choice the office makes when it confirms the holder;
* an activity is its HR PoC's (test_hr_withdrawal_notice);
* a project a record does name a processor for is left to that processor;
* a consent with nobody to ask is listed, not dropped, for the office to
  place by hand - and only once the records have been read.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import holdings
from cmp.db.repositories import rights as repo
from cmp.domain.consent import service as consent_service
from cmp.domain.rights import service
from tests.conftest import hashed
from tests.integration.test_rights_flows import (
    _consent,
    _export_with_her,
    _portal_request,
    _started,
)

pytestmark = pytest.mark.integration

DPO = Role.DPO


async def _request(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    return await _started(conn, seeded, await _portal_request(conn, seeded, "access"))


async def _only_dco_admin(conn: Any, seeded: dict[str, Any]) -> int:
    """Leave the seeded DCO Admin the only one: the database these tests share
    keeps the accounts other suites made."""
    mine = int(seeded["users"]["dco_admin"]["id"])
    await conn.execute(
        "UPDATE auth_user SET status = 'deactivated' WHERE role = 'dco_admin' AND id <> %s",
        (mine,),
    )
    return mine


async def test_a_project_no_record_covers_is_the_one_dco_admin_s(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    dco_admin = await _only_dco_admin(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    assert row["holders_derived_at"] is None
    assert await service.unowned_consents(conn, row) == [], "nothing is said before reading"

    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert holder["derived_from"] == "project_owner"
    assert holder["label"] == "Test Project · DCO Admin"
    assert holder["processor_id"] is None
    assert holder["project_uuid"] == seeded["project"]["project_uuid"]
    assert holder["is_activity"] is False
    assert holder["responder_user_id"] == dco_admin and holder["channel"] == "portal"
    assert holder["responder_user_id"] != int(seeded["users"]["dco"]["id"]), (
        "the project's own Data Collection Owner is not the one asked"
    )
    assert holder["confirmed_at"] is None, "found is not confirmed - the office does that"
    assert holder["evidence"] == {
        "project": str(seeded["project"]["project_uuid"]),
        "is_activity": False,
        "consents": [str(consent["consent_uuid"])],
    }

    row = await service.reload(conn, row)
    assert row["holders_derived_at"] is not None
    assert await service.unowned_consents(conn, row) == []

    # Reading twice refreshes the holder; it does not add a second.
    again = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert [h["holder_uuid"] for h in again] == [holder["holder_uuid"]]


async def test_with_several_dco_admins_the_office_chooses_as_it_confirms(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    extra = await conn.execute(
        """INSERT INTO auth_user (full_name, email, email_hash, role, status, password_hash,
                                  office_id)
           SELECT 'Second DCO Admin', 'dcoadmin2@test.local', %s, 'dco_admin', 'active', 'x',
                  office_id
             FROM auth_user WHERE id = %s
           RETURNING id""",
        (hashed("email", "dcoadmin2@test.local"), seeded["users"]["dco_admin"]["id"]),
    )
    await extra.fetchone()
    await _consent(conn, seeded)
    row = await _request(conn, seeded)

    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert holder["label"] == "Test Project · DCO Admin"
    assert holder["responder_user_id"] is None and holder["channel"] == "email"
    assert await service.unowned_consents(conn, await service.reload(conn, row)) == []

    # Nobody chosen, nobody to send to.
    with pytest.raises(ValidationFailed):
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
        )
    # Not the project's own owner, nor anybody who is not a DCO Admin.
    with pytest.raises(ValidationFailed) as refused:
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
            responder_user_uuid=str(seeded["users"]["dco"]["uuid"]),
        )
    assert refused.value.field == "responder_user_uuid"

    chosen = await service.confirm_holder(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name=None,
        responder_contact=None,
        role=DPO,
        actor_id=dpo,
        responder_user_uuid=str(seeded["users"]["dco_admin"]["uuid"]),
    )
    assert chosen["responder_user_id"] == int(seeded["users"]["dco_admin"]["id"])
    assert chosen["channel"] == "portal" and chosen["confirmed_at"] is not None


async def test_a_project_a_record_names_a_processor_for_is_left_to_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    consent = await _consent(conn, seeded)
    await _export_with_her(conn, seeded, consent["consent_id"])
    row = await _request(conn, seeded)
    holders = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert [(h["label"], h["derived_from"]) for h in holders] == [
        ("Test Processor Ltd", "export_line")
    ]
    assert await service.unowned_consents(conn, await service.reload(conn, row)) == []

    # A processor's holder is answered by its respondents, not a chosen account.
    with pytest.raises(ValidationFailed):
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holders[0]["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
            responder_user_uuid=str(seeded["users"]["dco_admin"]["uuid"]),
        )


async def test_a_consent_with_nobody_to_ask_is_listed_not_dropped(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    dco_admin = await _only_dco_admin(conn, seeded)
    consent = await _consent(conn, seeded)
    # The office's last DCO Admin has left.
    await conn.execute("UPDATE auth_user SET status = 'deactivated' WHERE id = %s", (dco_admin,))
    row = await _request(conn, seeded)
    assert await service.derive_holders(conn, row, role=DPO, actor_id=dpo) == []

    row = await service.reload(conn, row)
    [unowned] = await service.unowned_consents(conn, row)
    assert unowned["consent_uuid"] == str(consent["consent_uuid"])
    assert unowned["project_name"] == "Test Project" and unowned["is_activity"] is False
    assert unowned["notice_code"] and unowned["notice_version"] == 1
    assert unowned["withdrawal"] is False

    # A DCO Admin since, and the office looks again: found, and no longer listed.
    await conn.execute("UPDATE auth_user SET status = 'active' WHERE id = %s", (dco_admin,))
    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert holder["derived_from"] == "project_owner"
    assert await service.unowned_consents(conn, await service.reload(conn, row)) == []


async def _declined(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    """A consent artefact on which she agreed to nothing."""
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): False},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def test_a_declined_consent_and_another_office_s_project_name_nobody(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """She agreed to nothing under it, so nothing was collected; and a
    request is one office's, so the other's projects are not read."""
    me = int(seeded["subject"]["id"])
    found = await conn.execute(
        "SELECT office_id FROM project WHERE project_id = %s", (seeded["project"]["project_id"],)
    )
    office = int((await found.fetchone())["office_id"])
    await _declined(conn, seeded)
    assert await holdings.owners_of_person(conn, me, office_id=office) == []

    await _consent(conn, seeded)
    [owned] = await holdings.owners_of_person(conn, me, office_id=office)
    assert owned["candidates"] >= 1
    assert len(owned["consents"]) == 2, "once she has agreed, the refusal before it is hers too"
    other = await conn.execute("SELECT office_id FROM office WHERE office_code = 'hr'")
    assert (
        await holdings.owners_of_person(
            conn, me, office_id=int((await other.fetchone())["office_id"])
        )
        == []
    )


async def test_the_dco_admin_s_ticket_opens_with_her_consents_in_that_project(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    dco_admin = await _only_dco_admin(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    await service.confirm_holder(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name=None,
        responder_contact=None,
        role=DPO,
        actor_id=dpo,
    )
    await service.issue_tickets(conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo)
    sent = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert sent is not None
    assert sent["ticket_status"] == "issued" and sent["channel"] == "portal"
    assert sent["responder_user_id"] == dco_admin
    assert [c["consent_uuid"] for c in sent["brief"]["consents"]] == [str(consent["consent_uuid"])]
    assert sent["brief"]["consents"][0]["project"] == "Test Project"
