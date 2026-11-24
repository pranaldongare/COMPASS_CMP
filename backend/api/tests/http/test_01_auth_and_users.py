"""Authentication, the staff register, delegation, the dashboard - over HTTP.

Every response passes through `call()`, which checks that each sealed field it
carries is ciphertext and records the endpoint in the ledger. The assertions
here are about what the endpoint *does*; the rules about what it must not leak
are applied to all of them alike.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.conftest import plain
from tests.http.conftest import SessionFactory, fresh, fresh_email, fresh_mobile, last_code
from tests.http.contract import call

REGISTRATION = "cmp.notifications.send_registration_code"
LOGIN = "cmp.notifications.send_login_code"
MFA = "cmp.notifications.send_mfa_code"
RESET = "cmp.notifications.send_password_reset"
CONFIRM = "cmp.notifications.send_contact_confirmation"
PASSWORD = "HttpSuite!2026"


class TestPublicRegistrationAndCodeSignIn:
    async def test_a_person_registers_verifies_and_signs_in_by_code(
        self, http: httpx.AsyncClient, queued: Any, committed: Any
    ) -> None:
        mobile, email = fresh_mobile(), fresh_email("reg")

        # Register: the row is written sealed, the codes go to the contacts typed.
        await call(
            http,
            "POST",
            "/auth/register",
            expect=(200, 201, 202),
            json={
                "full_name": "Http Registrant",
                "mobile": mobile,
                "email": email,
                "dob": "1990-05-04",
            },
        )
        codes = [args for name, args in queued if name == REGISTRATION]
        by_contact = {str(plain(a[1])): str(a[2]) for a in codes}
        assert mobile in by_contact and email in by_contact, "a code to each contact typed"

        await call(
            http,
            "POST",
            "/auth/register/verify",
            expect=(200, 201),
            json={
                "mobile": mobile,
                "mobile_code": by_contact[mobile],
                "email_code": by_contact[email],
            },
        )

        # What the database holds for her.
        from cmp.db.sql import fetch_one

        row = await fetch_one(
            committed,
            "SELECT full_name, email, mobile, dob, minor_until, email_hash FROM auth_user "
            "WHERE email_hash = %s",
            (
                __import__("cmp.infrastructure.dkms.blind", fromlist=["index_of"]).index_of(
                    "email", email
                ),
            ),
        )
        assert row is not None, "found by the blind index of the address typed"
        for column in ("full_name", "email", "mobile", "dob"):
            assert str(row[column]).startswith("SE::"), f"{column} stored sealed"
        assert str(row["minor_until"]) == "2008-05-04", "the s.9 date, in the clear"
        assert plain(row["dob"]) == "1990-05-04"

        # Sign in by code, with the address in the clear as she would type it.
        await call(http, "POST", "/auth/otp/request", json={"contact": email})
        code = last_code(queued, LOGIN)
        verified = await call(
            http, "POST", "/auth/otp/verify", json={"contact": email, "code": code}
        )
        cookies = dict(verified.cookies)
        assert cookies, "a session cookie came back"

        me = await call(http, "GET", "/auth/me", cookies=cookies)
        body = me.json()
        assert body["role"] == "data_subject"
        assert body["full_name"].startswith("SE::") and body["email"].startswith("SE::")
        assert body["is_minor"] is False, "decided on minor_until, not on the sealed date"

        sessions = await call(http, "GET", "/auth/sessions", cookies=cookies)
        assert any(s.get("ip_address") for s in sessions.json()), "her own sessions, with addresses"

    async def test_an_unknown_contact_is_told_there_is_no_account(
        self, http: httpx.AsyncClient, queued: Any
    ) -> None:
        """Since 2026-11-16 (the product owner's decision); the portal sends
        the person to register. It was the same sentence as for anybody."""
        unknown = await http.post("/auth/otp/request", json={"contact": fresh_email("nobody")})
        assert unknown.status_code == 404, unknown.text
        assert unknown.json()["error"]["code"] == "account_not_found"
        assert unknown.json()["error"]["field"] == "contact"
        assert not [n for n, _ in queued if n == LOGIN], "and nothing was sent"


class TestStaffSignInAndPasswords:
    async def test_a_sign_in_waiting_for_its_code_can_be_abandoned(
        self, http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, committed: Any
    ) -> None:
        """2026-11-24: the code step's "Start over" and "Forgotten your
        password?" end the partial session, or the sign-in page sends its holder
        back to the code step and the reset is out of reach."""
        dco = await session_for("dco")
        login = plain(dco.user["email"])
        first = await call(http, "POST", "/auth/login", json={"login": login, "password": PASSWORD})
        assert first.json()["mfa_required"] is True
        partial = dict(first.cookies)
        csrf = {"X-CSRF-Token": partial["cmp_csrf"]}
        # The code sent is on the trail, with its flow, for the health
        # figures' "Codes sent" (2026-11-24); the code itself is not.
        cur = await committed.execute(
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'auth.otp_requested' AND entity_id = %s
                ORDER BY log_id DESC LIMIT 1""",
            (dco.user["id"],),
        )
        sent = await cur.fetchone()
        assert sent is not None and sent["detail_json"]["flow"] == "staff_sign_in"
        assert "code" not in sent["detail_json"]

        await call(http, "POST", "/auth/logout", cookies=partial, headers=csrf)
        # The half-finished sign-in is gone: its code step no longer answers.
        await call(
            http,
            "POST",
            "/auth/mfa/verify",
            cookies=partial,
            headers=csrf,
            json={"code": last_code(queued, MFA)},
            expect=401,
        )

    async def test_login_mfa_and_password_change(
        self, http: httpx.AsyncClient, session_for: SessionFactory, queued: Any
    ) -> None:
        dco = await session_for("dco")
        login = plain(dco.user["email"])

        first = await call(http, "POST", "/auth/login", json={"login": login, "password": PASSWORD})
        assert first.json()["mfa_required"] is True
        partial = dict(first.cookies)
        code = last_code(queued, MFA)
        # The partial session already carries a CSRF cookie; a write echoes it.
        full = await call(
            http,
            "POST",
            "/auth/mfa/verify",
            cookies=partial,
            headers={"X-CSRF-Token": partial["cmp_csrf"]},
            json={"code": code},
        )
        cookies = {**partial, **dict(full.cookies)}
        csrf = cookies["cmp_csrf"]

        await call(
            http,
            "POST",
            "/auth/password/change",
            cookies=cookies,
            headers={"X-CSRF-Token": csrf},
            expect=(200, 204),
            json={"current_password": PASSWORD, "new_password": "HttpSuite!2027"},
        )
        # And the new password is what signs in now.
        await call(http, "POST", "/auth/login", json={"login": login, "password": "HttpSuite!2027"})

    async def test_password_reset_by_code(
        self, http: httpx.AsyncClient, session_for: SessionFactory, queued: Any
    ) -> None:
        rco = await session_for("rco")
        email = plain(rco.user["email"])
        await call(http, "POST", "/auth/password/reset/request", json={"email": email})
        code = last_code(queued, RESET)
        await call(
            http,
            "POST",
            "/auth/password/reset/confirm",
            expect=(200, 204),
            json={"email": email, "code": code, "new_password": "HttpSuite!Reset1"},
        )
        await call(
            http, "POST", "/auth/login", json={"login": email, "password": "HttpSuite!Reset1"}
        )


class TestTheStaffRegister:
    async def test_the_administrator_runs_the_register(
        self, http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, committed: Any
    ) -> None:
        admin = await session_for("admin")
        dpo = await session_for("dpo")
        email, org = fresh_email("staff"), fresh("EMP-")
        offices = (await call(http, "GET", "/offices", session=admin)).json()
        rnd = next(o["office_uuid"] for o in offices if o["office_code"] == "rnd")

        # Every role but the administrator works in one office (ADR 0032).
        await call(
            http,
            "POST",
            "/users",
            session=admin,
            expect=422,
            json={"full_name": "Http Staffer", "email": email, "role": "rco"},
        )
        created = await call(
            http,
            "POST",
            "/users",
            session=admin,
            expect=201,
            json={
                "full_name": "Http Staffer",
                "email": email,
                "role": "rco",
                "organization_id": org,
                "mobile": fresh_mobile(),
                "office_uuid": rnd,
            },
        )
        user = created.json()
        uid = user["uuid"]
        assert user["office_uuid"] == rnd
        assert user["full_name"].startswith("SE::") and user["email"].startswith("SE::")
        # The invitation went to the address in the clear - opened at sending.
        assert (
            plain(last_code(queued, "cmp.notifications.send_staff_invitation", position=1)) == email
        )

        listing = await call(http, "GET", "/users", session=admin, params={"q": email})
        assert [u["uuid"] for u in listing.json()["items"]] == [uid], "found by exact contact"
        listing = await call(http, "GET", "/users", session=admin, params={"q": org})
        assert [u["uuid"] for u in listing.json()["items"]] == [uid], "and by employee id"

        await call(http, "GET", "/users/staff", session=dpo)
        await call(http, "GET", "/users/collection-owners", session=dpo)
        one = await call(http, "GET", f"/users/{uid}", template="/users/{user_uuid}", session=admin)
        assert one.json()["uuid"] == uid

        patched = await call(
            http,
            "PATCH",
            f"/users/{uid}",
            template="/users/{user_uuid}",
            session=admin,
            json={"full_name": "Http Staffer Renamed", "mobile": fresh_mobile()},
        )
        assert plain(patched.json()["full_name"]) == "Http Staffer Renamed"

        await call(
            http,
            "POST",
            f"/users/{uid}/role",
            template="/users/{user_uuid}/role",
            session=admin,
            expect=(200, 204),
            json={"role": "dco", "reason": "moved teams"},
        )
        await call(
            http,
            "GET",
            f"/users/{uid}/person-type-history",
            template="/users/{user_uuid}/person-type-history",
            session=admin,
        )
        await call(
            http,
            "POST",
            f"/users/{uid}/mfa/reset",
            template="/users/{user_uuid}/mfa/reset",
            session=admin,
            expect=(200, 204),
        )
        await call(
            http,
            "DELETE",
            f"/users/{uid}/sessions",
            template="/users/{user_uuid}/sessions",
            session=admin,
            expect=(200, 204),
        )
        # Invite again: allowed only while pending, which this account is.
        await call(
            http,
            "POST",
            f"/users/{uid}/invite",
            template="/users/{user_uuid}/invite",
            session=admin,
            expect=(200, 202, 204, 409),
        )
        await call(
            http,
            "POST",
            f"/users/{uid}/deactivate",
            template="/users/{user_uuid}/deactivate",
            session=admin,
            expect=(200, 204),
        )
        await call(
            http,
            "POST",
            f"/users/{uid}/reactivate",
            template="/users/{user_uuid}/reactivate",
            session=admin,
            expect=(200, 204),
        )


class TestDelegationAndDashboard:
    async def test_cover_is_arranged_and_listed(
        self, http: httpx.AsyncClient, session_for: SessionFactory
    ) -> None:
        dco = await session_for("dco")
        cover = await session_for("dco")
        # The form's list: a DCO sees the other DCO, sealed, and not herself.
        offered = await call(http, "GET", "/delegations/candidates", session=dco)
        uuids = [c["uuid"] for c in offered.json()]
        assert cover.uuid in uuids and dco.uuid not in uuids
        made = await call(
            http,
            "POST",
            "/delegations",
            session=dco,
            expect=201,
            json={
                "delegate_user_uuid": cover.uuid,
                "reason": "Away for the week",
            },
        )
        if made.json().get("reason"):
            assert made.json()["reason"].startswith("SE::")
        await call(http, "GET", "/delegations", session=await session_for("admin"))
        await call(http, "GET", "/delegations/mine", session=dco)
        held = await call(http, "GET", "/delegations/held", session=cover)
        assert any(d["delegator_uuid"] == dco.uuid for d in held.json()), "she holds his cover"

    async def test_every_role_has_a_dashboard(
        self, http: httpx.AsyncClient, session_for: SessionFactory
    ) -> None:
        for role in ("dpo", "admin", "dco", "dco_admin", "rco", "rnd_user"):
            s = await session_for(role)
            body = (await call(http, "GET", "/dashboard", session=s)).json()
            assert body["role"] == role
