"""Rights requests, end to end, over HTTP - the office's side and the person's.

Three journeys. A public access request that the office verifies, routes to a
holder, has answered on a ticket, and responds to with a file, which the person
then downloads signed in. An erasure the office refuses, and a grievance about
that, escalated to an administrator who decides it. And a nominee: named,
accepting through the token, raising a request on a death, seeing it through.

Every response passed `call()`: sealed fields sealed, no contact in the clear,
the endpoint recorded.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory, fresh, fresh_email, fresh_mobile, last_code
from tests.http.contract import call
from tests.http.world import World, build

VERIFY = "cmp.notifications.send_rights_verification_code"
NOMINATION_CODE = "cmp.notifications.send_nomination_code"
INVITATION = "cmp.notifications.send_nomination_invitation"
RIGHTS = "/requests/{request_uuid}"
HOLDER = "/requests/{request_uuid}/holders/{holder_uuid}"


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


async def _public_request(http: httpx.AsyncClient, queued: Any, contact: str, text: str) -> str:
    """A stranger's request from the public form, verified by code. Returns the uuid."""
    made = await call(
        http,
        "POST",
        "/rights/requests",
        expect=(200, 201),
        json={
            "request_type": "access",
            "contact": contact,
            "name": "Walker Public",
            "request_text": text,
        },
    )
    reference = made.json()["reference"]
    code = last_code(queued, VERIFY, position=1)
    await call(http, "POST", "/rights/requests/verify", json={"reference": reference, "code": code})
    return reference


class TestAnAccessRequestThroughTheOffice:
    async def test_from_the_public_form_to_the_downloaded_response(
        self, http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
    ) -> None:
        dpo = world.dpo
        text = f"Please tell me everything you hold about me {fresh()}"
        reference = await _public_request(http, queued, world.principal_email, text)

        # The office finds it: by reference, and by the exact contact through the index.
        listed = await call(http, "GET", "/requests", session=dpo, params={"q": reference})
        row = next(r for r in listed.json()["items"] if r["reference"] == reference)
        assert row["submitted_contact"].startswith("SE::"), "sealed in the list"
        by_contact = await call(
            http, "GET", "/requests", session=dpo, params={"q": world.principal_email}
        )
        assert any(r["reference"] == reference for r in by_contact.json()["items"])
        ruuid = row["request_uuid"]

        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=dpo)
        assert plain(one.json()["request_text"]) == text
        assert one.json()["verification_status"] == "verified"

        await call(
            http,
            "POST",
            f"/requests/{ruuid}/acknowledge",
            template=RIGHTS + "/acknowledge",
            session=dpo,
            expect=(200, 204, 409),
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/classify",
            template=RIGHTS + "/classify",
            session=dpo,
            json={"request_type": "access", "note": "As stated."},
        )

        await call(
            http,
            "POST",
            f"/requests/{ruuid}/transition",
            template=RIGHTS + "/transition",
            session=dpo,
            json={"to": "in_progress"},
        )

        # Holders: derived from the records that name her, plus one the records
        # missed, added by hand with a person to write to.
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/derive",
            template=RIGHTS + "/holders/derive",
            session=dpo,
            expect=(200, 201),
        )
        added = await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders",
            template=RIGHTS + "/holders",
            session=dpo,
            expect=(200, 201),
            json={
                "label": "Acme archive",
                "responder_name": "Priya at Acme",
                "responder_contact": fresh_email("priya"),
            },
        )
        holders = (
            added.json()
            if isinstance(added.json(), list)
            else added.json().get("holders", [added.json()])
        )
        holder = next(h for h in holders if h.get("label") == "Acme archive")
        huuid = holder["holder_uuid"]
        assert holder["responder_name"].startswith("SE::") and holder[
            "responder_contact"
        ].startswith("SE::")

        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/confirm",
            template=HOLDER + "/confirm",
            session=dpo,
            expect=(200, 204),
            json={},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/tickets",
            template=RIGHTS + "/tickets",
            session=dpo,
            expect=(200, 201),
            json={"instruction": "Send everything you hold on her."},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/thread",
            template=HOLDER + "/thread",
            session=dpo,
            expect=(200, 201),
            data={"body": "Anything on the archive tapes too, please."},
        )
        thread = await call(
            http,
            "GET",
            f"/requests/{ruuid}/holders/{huuid}/thread",
            template=HOLDER + "/thread",
            session=dpo,
        )
        assert all(m["body"].startswith("SE::") for m in thread.json()["messages"])
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/remind",
            template=HOLDER + "/remind",
            session=dpo,
            expect=(200, 204),
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/contact",
            template=HOLDER + "/contact",
            session=dpo,
            expect=(200, 201, 204),
            json={"kind": "note", "note": "Phoned; they are on it.", "send": False},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/escalate",
            template=HOLDER + "/escalate",
            session=dpo,
            expect=(200, 204, 409),
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/reassign",
            template=HOLDER + "/reassign",
            session=dpo,
            expect=(200, 204),
            json={"responder_name": "Rahul at Acme", "responder_contact": fresh_email("rahul")},
        )

        # The holder answers from the office's side, is sent back once, answers again.
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/return",
            template=HOLDER + "/return",
            session=dpo,
            expect=(200, 204),
            data={"summary": "Two tapes, three consents. Nothing else."},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/send-back",
            template=HOLDER + "/send-back",
            session=dpo,
            expect=(200, 204),
            json={"reason": "Say which tapes."},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/return",
            template=HOLDER + "/return",
            session=dpo,
            expect=(200, 204),
            data={"summary": "Tapes 12 and 14."},
        )

        # The last ticket back moved the request to collating on its own.
        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=dpo)
        assert one.json()["status"] == "collating"

        # The response, with a file; then the person reads it signed in.
        responded = await call(
            http,
            "POST",
            f"/requests/{ruuid}/respond",
            template=RIGHTS + "/respond",
            session=dpo,
            expect=(200, 201),
            data={"outcome": "complete", "response_text": "Attached is everything we hold."},
            files={"files": ("extract.csv", b"consent,purpose\n1,gait\n", "text/csv")},
        )
        assert responded.json()["status"] == "closed"
        detail = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=dpo)
        files = detail.json()["response_files"]
        assert files and files[0]["file_name"].startswith("SE::")
        fuuid = files[0]["file_uuid"]
        await call(
            http,
            "GET",
            f"/requests/{ruuid}/files/{fuuid}",
            template=RIGHTS + "/files/{file_uuid}",
            session=dpo,
            check_sealed=False,
        )

        mine = await call(http, "GET", "/me/requests", session=world.principal)
        hers = next(r for r in mine.json() if r["reference"] == reference)
        assert hers["response_text"].startswith("SE::")
        await call(
            http,
            "GET",
            f"/me/requests/{ruuid}",
            template="/me/requests/{request_uuid}",
            session=world.principal,
        )
        await call(
            http,
            "GET",
            f"/me/requests/{ruuid}/files/{fuuid}",
            template="/me/requests/{request_uuid}/files/{file_uuid}",
            session=world.principal,
            check_sealed=False,
        )
        await call(
            http,
            "GET",
            f"/requests/{ruuid}/linked/trail",
            template=RIGHTS + "/linked/trail",
            session=dpo,
            expect=(200, 404),
        )


class TestErasureRefusedAndTheGrievance:
    async def test_refusal_grievance_and_review(
        self, http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
    ) -> None:
        dpo, admin = world.dpo, world.admin
        # Raised by her, signed in, about the consent she gave.
        made = await call(
            http,
            "POST",
            "/me/requests",
            session=world.principal,
            expect=(200, 201),
            json={
                "request_type": "erasure",
                "request_text": "Erase the walking video.",
                "consent_uuid": world.consent_uuid,
            },
        )
        ruuid = made.json()["request_uuid"]
        assert made.json()["request_text"].startswith("SE::")

        # Verification by hand, the scope derived, one item decided and applied.
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/verification/manual",
            template=RIGHTS + "/verification/manual",
            session=dpo,
            expect=(200, 204, 409),
            json={"note": "Signed in; identity is the session."},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/intent",
            template=RIGHTS + "/intent",
            session=dpo,
            expect=(200, 204, 409),
        )
        derived = await call(
            http,
            "POST",
            f"/requests/{ruuid}/scope/derive",
            template=RIGHTS + "/scope/derive",
            session=dpo,
            expect=(200, 201),
        )
        items = (
            derived.json() if isinstance(derived.json(), list) else derived.json().get("items", [])
        )
        if items:
            iuuid = items[0]["item_uuid"]
            await call(
                http,
                "PUT",
                f"/requests/{ruuid}/scope/{iuuid}",
                template=RIGHTS + "/scope/{item_uuid}",
                session=dpo,
                expect=(200, 204),
                json={
                    "decision": "retain",
                    "basis": "Retention floor under the purpose.",
                    "retain_until": "2027-09-01",
                },
            )
            await call(
                http,
                "POST",
                f"/requests/{ruuid}/scope/{iuuid}/apply",
                template=RIGHTS + "/scope/{item_uuid}/apply",
                session=dpo,
                expect=(200, 204, 409),
            )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/transition",
            template=RIGHTS + "/transition",
            session=dpo,
            expect=(200, 204, 409),
            json={"to": "in_progress"},
        )
        refused = await call(
            http,
            "POST",
            f"/requests/{ruuid}/refuse",
            template=RIGHTS + "/refuse",
            session=dpo,
            json={"reason": "The retention floor has not passed."},
        )
        assert refused.json()["refusal_reason"].startswith("SE::")

        # She disputes; the grievance is about the DPO, so an administrator reviews it.
        disputed = await call(
            http,
            "POST",
            f"/me/requests/{ruuid}/dispute",
            template="/me/requests/{request_uuid}/dispute",
            session=world.principal,
            expect=(200, 201),
            json={"text": "The floor is wrong.", "about_dpo": True},
        )
        guuid = disputed.json()["request_uuid"]
        await call(
            http,
            "POST",
            f"/requests/{guuid}/escalate",
            template=RIGHTS + "/escalate",
            session=dpo,
            expect=(200, 204, 409),
        )
        await call(
            http,
            "POST",
            f"/requests/{guuid}/reviewer",
            template=RIGHTS + "/reviewer",
            session=admin,
            expect=(200, 204),
            json={"reviewer_uuid": admin.uuid},
        )
        await call(
            http,
            "POST",
            f"/requests/{guuid}/classify",
            template=RIGHTS + "/classify",
            session=admin,
            json={"request_type": "grievance"},
        )
        await call(
            http,
            "POST",
            f"/requests/{guuid}/transition",
            template=RIGHTS + "/transition",
            session=admin,
            json={"to": "in_progress"},
        )
        decided = await call(
            http,
            "POST",
            f"/requests/{guuid}/decide",
            template=RIGHTS + "/decide",
            session=admin,
            json={"upheld": False, "response_text": "The floor stands.", "remedy_text": None},
        )
        assert decided.json()["request"]["response_text"].startswith("SE::")

    async def test_a_request_the_office_records_itself_and_closes_as_a_withdrawal(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        dpo = world.dpo
        made = await call(
            http,
            "POST",
            "/requests",
            session=dpo,
            expect=(200, 201),
            json={
                "request_type": "erasure",
                "contact": world.principal_email,
                "name": "Principal",
                "request_text": "Stop using my video.",
                "subject_uuid": world.principal.uuid,
            },
        )
        ruuid = made.json()["request_uuid"]
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/verification/code",
            template=RIGHTS + "/verification/code",
            session=dpo,
            expect=(200, 202, 204),
        )
        code = last_code(queued, VERIFY, position=1)
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/verification/confirm",
            template=RIGHTS + "/verification/confirm",
            session=dpo,
            expect=(200, 204),
            json={"code": code},
        )
        # She meant withdrawal: recorded as one.
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/withdrawal",
            template=RIGHTS + "/withdrawal",
            session=dpo,
            expect=(200, 204),
            json={"note": "She confirmed she meant to withdraw."},
        )

    async def test_a_request_whose_verification_fails(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        made = await call(
            http,
            "POST",
            "/requests",
            session=world.dpo,
            expect=(200, 201),
            json={
                "request_type": "access",
                "contact": fresh_email("stranger"),
                "request_text": "Who am I to you?",
            },
        )
        await call(
            http,
            "POST",
            f"/requests/{made.json()['request_uuid']}/verification/fail",
            template=RIGHTS + "/verification/fail",
            session=world.dpo,
            expect=(200, 204),
            json={"note": "No such person anywhere."},
        )


class TestTicketsFromTheHoldersSide:
    async def test_a_staff_respondent_answers_on_the_portal(
        self, http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
    ) -> None:
        dpo = world.dpo
        # A holder whose respondent is one of our own accounts, so the ticket is theirs.
        team = await session_for("dco")
        text = f"Access request for the ticket test {fresh()}"
        reference = await _public_request(http, queued, world.principal_email, text)
        row = next(
            r
            for r in (
                await call(http, "GET", "/requests", session=dpo, params={"q": reference})
            ).json()["items"]
            if r["reference"] == reference
        )
        ruuid = row["request_uuid"]
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/classify",
            template=RIGHTS + "/classify",
            session=dpo,
            json={"request_type": "access"},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/transition",
            template=RIGHTS + "/transition",
            session=dpo,
            json={"to": "in_progress"},
        )
        respondent = await call(
            http,
            "POST",
            f"/processors/{world.processor_uuid}/respondents",
            template="/processors/{processor_uuid}/respondents",
            session=dpo,
            expect=(200, 201),
            json={"user_uuid": team.uuid},
        )
        added = await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders",
            template=RIGHTS + "/holders",
            session=dpo,
            expect=(200, 201),
            json={"label": "Our own team", "processor_uuid": world.processor_uuid},
        )
        holders = (
            added.json()
            if isinstance(added.json(), list)
            else added.json().get("holders", [added.json()])
        )
        huuid = next(h for h in holders if h.get("label") == "Our own team")["holder_uuid"]
        rows = respondent.json() if isinstance(respondent.json(), list) else [respondent.json()]
        ours = next(r for r in rows if r.get("user_uuid") == team.uuid)
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{huuid}/confirm",
            template=HOLDER + "/confirm",
            session=dpo,
            expect=(200, 204),
            json={"respondent_uuid": ours["respondent_uuid"]},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/tickets",
            template=RIGHTS + "/tickets",
            session=dpo,
            expect=(200, 201),
            json={"instruction": "Tell us what your team holds."},
        )

        # A second holder, added in error, whose ticket the office withdraws.
        again = await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders",
            template=RIGHTS + "/holders",
            session=dpo,
            expect=(200, 201),
            json={
                "label": "Withdrawn one",
                "responder_name": "Nobody",
                "responder_contact": fresh_email("nobody"),
            },
        )
        holders = (
            again.json()
            if isinstance(again.json(), list)
            else again.json().get("holders", [again.json()])
        )
        gone = next(h for h in holders if h.get("label") == "Withdrawn one")["holder_uuid"]
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{gone}/confirm",
            template=HOLDER + "/confirm",
            session=dpo,
            expect=(200, 204),
            json={},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/tickets",
            template=RIGHTS + "/tickets",
            session=dpo,
            expect=(200, 201),
            json={},
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/{gone}/withdraw",
            template=HOLDER + "/withdraw",
            session=dpo,
            expect=(200, 204),
            json={"reason": "Added in error."},
        )

        # Their side.
        mine = await call(http, "GET", "/tickets", session=team)
        ticket = next(t for t in mine.json() if t["holder_uuid"] == huuid)
        assert ticket["instruction"].startswith("SE::")
        await call(
            http, "GET", f"/tickets/{huuid}", template="/tickets/{holder_uuid}", session=team
        )
        await call(
            http,
            "POST",
            f"/tickets/{huuid}/messages",
            template="/tickets/{holder_uuid}/messages",
            session=team,
            expect=(200, 201),
            data={"body": "We hold two files. Sending the list."},
        )
        await call(
            http,
            "POST",
            f"/tickets/{huuid}/return",
            template="/tickets/{holder_uuid}/return",
            session=team,
            expect=(200, 204),
            data={"summary": "Two files, both from March."},
            files={"evidence": ("list.txt", b"a.mp4\nb.mp4\n", "text/plain")},
        )


class TestANominee:
    async def test_named_accepting_and_acting_on_a_death(
        self, http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
    ) -> None:
        # She names him; the invitation carries the token.
        mobile, email = fresh_mobile(), fresh_email("nominee")
        made = await call(
            http,
            "POST",
            "/me/nominations",
            session=world.principal,
            expect=(200, 201),
            json={
                "nominee_name": "Arjun Nominee",
                "nominee_mobile": mobile,
                "nominee_email": email,
                "rights": ["access", "erasure"],
            },
        )
        nuuid = made.json()["nomination_uuid"]
        url = next(str(a[2]) for n, a in reversed(queued) if n == INVITATION)
        token = url.rsplit("nomination=", 1)[-1].rsplit("/", 1)[-1]

        view = await call(
            http, "GET", f"/rights/nominations/{token}", template="/rights/nominations/{token}"
        )
        assert "Arjun" in view.json()["nominee_name"], (
            "the public page, token-gated, reads names in the clear"
        )
        await call(
            http,
            "POST",
            f"/rights/nominations/{token}/code",
            template="/rights/nominations/{token}/code",
            expect=(200, 202),
            json={"medium": "mobile"},
        )
        code = last_code(queued, NOMINATION_CODE, position=1)
        await call(
            http,
            "POST",
            f"/rights/nominations/{token}/accept",
            template="/rights/nominations/{token}/accept",
            expect=(200, 204),
            json={"code": code},
        )

        # He acts: a death, evidenced, and an access request in her name.
        await call(
            http,
            "POST",
            "/rights/nominee/start",
            json={"nomination_uuid": nuuid, "contact": mobile},
        )
        code = last_code(queued, "cmp.notifications.send_rights_verification_code", position=1)
        raised = await call(
            http,
            "POST",
            "/rights/nominee/requests",
            expect=(200, 201),
            data={
                "nomination_uuid": nuuid,
                "code": code,
                "request_type": "access",
                "request_text": "Everything you held about my late mother.",
                "trigger_event": "death",
            },
            files={"evidence": ("certificate.pdf", b"%PDF-1.4 certificate", "application/pdf")},
        )
        reference = raised.json()["reference"]
        listed = await call(http, "GET", "/requests", session=world.dpo, params={"q": reference})
        row = next(r for r in listed.json()["items"] if r["reference"] == reference)
        ruuid = row["request_uuid"]
        detail = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
        assert detail.json()["nominee_contact"].startswith("SE::")
        assert plain(detail.json()["nominee_name"]) == "Arjun Nominee"
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/event",
            template=RIGHTS + "/event",
            session=world.dpo,
            expect=(200, 204),
            json={"evidenced": True, "note": "Certificate seen."},
        )
        await call(
            http,
            "GET",
            f"/requests/{ruuid}/event/evidence",
            template=RIGHTS + "/event/evidence",
            session=world.dpo,
            check_sealed=False,
            expect=(200, 404),
        )

    async def test_a_second_nominee_declines(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        # A different principal, so the first nomination stays in force.
        other = await world_principal(http, world, queued)
        await call(
            http,
            "POST",
            "/me/nominations",
            session=other,
            expect=(200, 201),
            json={
                "nominee_name": "Declining Nominee",
                "nominee_mobile": fresh_mobile(),
                "rights": ["access"],
            },
        )
        url = next(str(a[2]) for n, a in reversed(queued) if n == INVITATION)
        token = url.rsplit("/", 1)[-1]
        await call(
            http,
            "POST",
            f"/rights/nominations/{token}/code",
            template="/rights/nominations/{token}/code",
            expect=(200, 202),
            json={"medium": "mobile"},
        )
        code = last_code(queued, NOMINATION_CODE, position=1)
        await call(
            http,
            "POST",
            f"/rights/nominations/{token}/decline",
            template="/rights/nominations/{token}/decline",
            expect=(200, 204),
            json={"code": code},
        )


async def world_principal(http: httpx.AsyncClient, world: World, queued: Any) -> Any:
    """Another data principal, registered through the same link."""
    from tests.http.conftest import Session  # noqa: F401
    from tests.http.world import CONSENT_CODE

    mobile = fresh_mobile()
    await call(
        http,
        "POST",
        f"/c/{world.link_token}/register",
        template="/c/{token}/register",
        expect=(200, 201),
        json={"full_name": f"Second {fresh()}", "mobile": mobile, "dob": "1988-11-02"},
    )
    await call(
        http,
        "POST",
        f"/c/{world.link_token}/otp",
        template="/c/{token}/otp",
        json={"contact": mobile},
    )
    code = last_code(queued, CONSENT_CODE, position=1)
    verified = await call(
        http,
        "POST",
        f"/c/{world.link_token}/otp/verify",
        template="/c/{token}/otp/verify",
        json={"contact": mobile, "code": code},
    )
    cookies = dict(verified.cookies)

    class _S:
        def __init__(self) -> None:
            self.cookies = cookies
            self.headers = {"X-CSRF-Token": cookies.get("cmp_csrf", "")}
            self.user = {"uuid": ""}
            self.uuid = ""

    return _S()
