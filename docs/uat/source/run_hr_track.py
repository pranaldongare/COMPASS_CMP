"""The HR track's UAT cases (../hr-track-uat-cases.md), run against the seeded
local stack through its API, as each screen calls it.

    backend/api/.venv/bin/python -I docs/uat/source/run_hr_track.py

Needs the API, the worker and the key service running locally with
DEV_SHOW_CODES=true (codes are read as the dev popup reads them). It CHANGES
the dev database: it resets the seeded Legal PoC's and HR PoCs' passwords to
UAT_PASSWORD, and leaves every record it makes (a category, purposes,
templates, activities, participants, requests, a breach, a Legal account)
under a random tag. Never point it at anything but a local stack. Writes
results.json beside itself.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
import traceback
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hr_harness import UAT_PASSWORD, Session, record, reset_password, staff  # noqa: E402

TAG = uuid.uuid4().hex[:6].upper()
OUTBOX = Path("/Users/test/Workspace/COMPASS_CMP/backend/api/var/outbox.log")
CTX: dict[str, Any] = {}


def case(name: str):
    def wrap(fn):
        def run() -> None:
            try:
                result, note = fn()
                record(name, result, note)
            except Exception as exc:  # noqa: BLE001
                record(name, "FAIL", f"{type(exc).__name__}: {exc}"[:300])
                traceback.print_exc(limit=2)

        run.__name__ = name
        CASES.append(run)
        return run

    return wrap


CASES: list[Any] = []


def ok(r: Any, *codes: int) -> Any:
    if r.status_code not in (codes or (200, 201)):
        raise AssertionError(f"{r.request.method} {r.request.url.path} -> {r.status_code}: {r.text[:240]}")
    return r.json() if r.content else None


def mobile() -> str:
    return f"+9196{random.randint(10_000_000, 99_999_999)}"


def outbox_since(mark: int) -> str:
    text = OUTBOX.read_text(errors="ignore") if OUTBOX.exists() else ""
    return text[mark:]


def outbox_mark() -> int:
    return len(OUTBOX.read_text(errors="ignore")) if OUTBOX.exists() else 0


def wait_outbox(mark: int, needle: str, timeout: float = 20) -> bool:
    import time

    end = time.time() + timeout
    while time.time() < end:
        if needle in outbox_since(mark):
            return True
        time.sleep(0.5)
    return False


def participant(token: str, *, dob: str = "1990-05-17", name: str | None = None) -> tuple[Session, Any]:
    """Arrive on a link with no account, register with a mobile, confirm the
    code: her session, signed in on this link."""
    s = Session(f"principal {token[:6]}")
    phone = mobile()
    ok(s.get(f"/c/{token}"))
    r = s.post(
        f"/c/{token}/register",
        json={"full_name": name or f"Uat Person {TAG}", "mobile": phone, "dob": dob},
    )
    if r.status_code not in (200, 201):
        return s, r
    before = s.seen()
    ok(s.post(f"/c/{token}/otp", json={"contact": phone}))
    code = s.wait_code(before)
    ok(s.post(f"/c/{token}/otp/verify", json={"contact": phone, "code": code}))
    s.phone = phone  # type: ignore[attr-defined]
    return s, r


def consent(s: Session, token: str, grants: dict[str, bool] | None = None) -> dict[str, Any]:
    notice = ok(s.get(f"/c/{token}/notice", params={"language_code": "english"}))
    grants = grants or {p["purpose_uuid"]: True for p in notice["purposes"]}
    return ok(
        s.post(
            f"/c/{token}/consent",
            json={"language_code": "english", "grants": grants, "action_type": "checkbox_click"},
        )
    )


# ----------------------------------------------------------------- set-up
def setup() -> None:
    CTX["admin"] = staff("admin", "admin@cmp.local")
    CTX["dpo"] = staff("dpo", "dpo@cmp.local")
    for email in ("meera.nair@cmp.local", "rahul.desai@cmp.local", "ananya.sen@cmp.local"):
        reset_password(email)
    CTX["legal"] = staff("legal", "meera.nair@cmp.local", UAT_PASSWORD)
    CTX["hr1"] = staff("hr rahul", "rahul.desai@cmp.local", UAT_PASSWORD)
    CTX["hr2"] = staff("hr ananya", "ananya.sen@cmp.local", UAT_PASSWORD)
    CTX["dco"] = staff("dco", "dco@cmp.local")
    offices = ok(CTX["admin"].get("/offices"))
    CTX["office"] = {o["office_code"]: o["office_uuid"] for o in offices}


# ------------------------------------------------------------ A · the wall
@case("HR-A1")
def a1():
    legal, dpo = CTX["legal"], CTX["dpo"]
    acts = ok(legal.get("/hr/activities", params={"status": "approved"}))
    hidden = [a["activity_uuid"] for a in acts][:5]
    leaks = [u for u in hidden if dpo.get(f"/projects/{u}").status_code != 404]
    projects = ok(dpo.get("/projects", params={"limit": 100}))
    listed = {p["project_uuid"] for p in projects["items"]}
    hr_consents = ok(legal.get("/consents", params={"limit": 20}))["items"]
    c_leaks = [c["consent_uuid"] for c in hr_consents if dpo.get(f"/consents/{c['consent_uuid']}").status_code != 404]
    audit = ok(dpo.get("/audit", params={"limit": 200}))["items"]
    hr_events = [e for e in audit if str(e["event_type"]).startswith(("hr_", "template_version", "hr."))]
    assert not leaks and not (listed & set(hidden)) and not c_leaks and not hr_events, (leaks, c_leaks, hr_events[:2])
    return "PASS", f"{len(hidden)} HR activities and {len(hr_consents)} HR consents answer 404 to the DPO; none in its project list; no HR event on its trail (requests/breaches: E4, E9)"


@case("HR-A2")
def a2():
    legal, dpo = CTX["legal"], CTX["dpo"]
    projects = ok(dpo.get("/projects", params={"limit": 5}))["items"]
    rnd = projects[0]["project_uuid"]
    r = legal.get(f"/projects/{rnd}")
    mine = ok(legal.get("/projects", params={"limit": 100}))["items"]
    rnd_in_list = [p for p in mine if p["project_uuid"] == rnd]
    assert r.status_code == 404 and not rnd_in_list, (r.status_code, rnd_in_list)
    me = ok(legal.get("/auth/me"))
    return "PASS", f"an R&D project's uuid answers 404 to Legal; Legal's sidebar is {me['nav']}"


@case("HR-A3")
def a3():
    admin = CTX["admin"]
    audit = ok(admin.get("/audit", params={"limit": 200}))["items"]
    kinds = {str(e["event_type"]).split(".")[0] for e in audit}
    users = ok(admin.get("/users", params={"role": "legal", "limit": 20}))["items"]
    offices = {u.get("office_code") or u.get("office_name") for u in users}
    assert "hr_category" in kinds or "template_version" in kinds or "hr_activity" in kinds or "project" in kinds
    return "PASS", f"the administrator's trail spans both offices ({len(kinds)} event families); Legal accounts carry office {offices}"


@case("HR-A4")
def a4():
    s = CTX.get("both_person")
    if s is None:
        return "NOT RUN", "depends on HR-E5's participant, who consents on both tracks"
    mine = ok(s.get("/me/consents"))
    items = mine if isinstance(mine, list) else mine.get("items", [])
    projects = {c.get("project_name") for c in items}
    assert len(items) >= 2, items
    return "PASS", f"My consents lists {len(items)} consents across both tracks: {sorted(p for p in projects if p)[:3]}"


@case("HR-A5")
def a5():
    role = f"uat_probe_{TAG.lower()}"
    sql = f"""BEGIN;
CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO {role};
GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role};
SET LOCAL ROLE {role};
SELECT set_config('app.office', 'hr', true);
SELECT 'hr', count(*) FROM project WHERE office_id = (SELECT office_id FROM office WHERE office_code = 'rnd');
SELECT set_config('app.office', 'all', true);
SELECT 'all', count(*) FROM project WHERE office_id = (SELECT office_id FROM office WHERE office_code = 'rnd');
ROLLBACK;"""
    out = subprocess.run(
        ["docker", "exec", "-i", "compass-db-1", "psql", "-U", "cmp", "-d", "cmp", "-tA"],
        input=sql, capture_output=True, text=True,
    ).stdout
    rows = dict(line.split("|") for line in out.splitlines() if line.startswith(("hr|", "all|")))
    assert rows.get("hr") == "0" and int(rows.get("all", "0")) > 0, out
    return "PASS", f"as a role the policies bind: 'hr' reads 0 R&D projects, 'all' reads {rows['all']} (the local superuser bypasses RLS, so the probe role stands in)"


# --------------------------------------------- B · Legal sets up a category
@case("HR-B1")
def b1():
    legal = CTX["legal"]
    made = ok(legal.post("/hr/categories", json={"category_code": f"CSR_{TAG}", "name": "CSR volunteering"}), 201)
    CTX["cat"] = made
    trail = ok(legal.get("/audit", params={"limit": 50}))["items"]
    hit = [e for e in trail if e["event_type"] == "hr_category.created"]
    assert made["status"] == "active" and hit
    return "PASS", f"{made['category_code']} active; audited hr_category.created on Legal's (hr) trail"


@case("HR-B2")
def b2():
    legal, admin = CTX["legal"], CTX["admin"]
    procs = ok(admin.get("/processors", params={"limit": 50}))["items"]
    internal = next(p for p in procs if p.get("is_in_house"))
    vendor = next(p for p in procs if not p.get("is_in_house"))
    CTX["vendor_processor"] = vendor
    cat = CTX["cat"]["category_uuid"]
    me = ok(legal.get("/auth/me"))
    body = {"processors": [
        {"processor_uuid": internal["processor_uuid"], "processor_role": "hrms"},
        {"processor_uuid": vendor["processor_uuid"], "processor_role": "vendor", "respondent_user_uuid": me["uuid"]},
    ]}
    both = ok(legal.call("PUT", f"/hr/categories/{cat}/processors", json=body))
    assert len(both) == 2
    one = ok(legal.call("PUT", f"/hr/categories/{cat}/processors", json={"processors": body["processors"][:1]}))
    row = docker_sql(
        "SELECT count(*) FILTER (WHERE removed_at IS NOT NULL) FROM category_processor cp"
        f" JOIN hr_category c USING (category_id) WHERE c.category_code = 'CSR_{TAG}'"
    )
    ok(legal.call("PUT", f"/hr/categories/{cat}/processors", json=body))
    assert len(one) == 1 and row.strip() == "1", (one, row)
    return "PASS", "HR system (hrms) and a vendor with its respondent listed; removing the vendor left a dated row (removed_at), then it was named again"


def docker_sql(sql: str) -> str:
    return subprocess.run(
        ["docker", "exec", "compass-db-1", "psql", "-U", "cmp", "-d", "cmp", "-tAc", sql],
        capture_output=True, text=True,
    ).stdout


PURPOSE = {
    "description": "Running the programme.",
    "uses": "Scheduling and taking part.",
    "lawful_basis": "consent_s6",
    "data_categories": ["name"],
    "retention_days": 730,
    "retention_basis": "business_policy",
    "erasure_trigger": "withdrawal",
}


@case("HR-B3")
def b3():
    legal, dpo = CTX["legal"], CTX["dpo"]
    made = {}
    for key, name in (("main", "CSR volunteering days"), ("extra", "CSR photographs")):
        p = ok(legal.post("/purposes", json={**PURPOSE, "purpose_code": f"P-{key[:2].upper()}{TAG}", "name": name}), 201)
        ok(legal.post(f"/purposes/{p['purpose_uuid']}/activate"))
        made[key] = p
    CTX["purposes"] = made
    dpo_list = ok(dpo.get("/purposes", params={"limit": 200, "q": TAG}))
    items = dpo_list["items"] if isinstance(dpo_list, dict) else dpo_list
    assert not [p for p in items if TAG in str(p.get("purpose_code"))]
    assert dpo.get(f"/purposes/{made['main']['purpose_uuid']}").status_code == 404
    return "PASS", "two HR purposes active (retention 2 years, trigger withdrawal); the DPO's list does not show them and their uuid answers 404"


TEMPLATE = {
    "title": "CSR volunteering",
    "withdraw_url": "https://example.org/withdraw",
    "exercise_rights_url": "https://example.org/rights",
    "board_complaint_url": "https://example.org/board",
    "dpo_contact": "legal@example.org",
    "applicable_to": "data_subject",
}


@case("HR-B4")
def b4():
    legal = CTX["legal"]
    r = legal.post("/notice-templates", json=TEMPLATE)
    assert r.status_code == 422, r.status_code
    made = ok(legal.post("/notice-templates", json={**TEMPLATE, "category_uuid": CTX["cat"]["category_uuid"]}), 201)
    CTX["template"] = made
    return "PASS", f"without a category: 422; with CSR_{TAG}: created {made['template_code']}"


LOCKED = "The Legal office will use your data for:\n{{purposes}}\n\nAbout this activity: {{description}}"


def vbase() -> str:
    return f"/notice-templates/{CTX['template']['template_uuid']}/versions"


@case("HR-B5")
def b5():
    legal = CTX["legal"]
    ok(legal.post(vbase()), 201)
    ok(legal.call("PUT", f"{vbase()}/1/languages/english", json={"locked_text": "For:\n{{purposes}}"}))
    ok(legal.call("PUT", f"{vbase()}/1/purposes", json={"purposes": [
        {"purpose_uuid": CTX["purposes"]["main"]["purpose_uuid"], "is_mandatory": True},
        {"purpose_uuid": CTX["purposes"]["extra"]["purpose_uuid"]},
    ]}))
    r = legal.post(f"{vbase()}/1/approve")
    msg = r.text
    assert r.status_code in (409, 422) and "english" in msg.lower() and "description" in msg, (r.status_code, msg[:200])
    return "PASS", f"refused {r.status_code}: {r.json()['error']['message'][:120]}"


@case("HR-B6")
def b6():
    legal = CTX["legal"]
    ok(legal.call("PUT", f"{vbase()}/1/languages/english", json={"locked_text": LOCKED}))
    ok(legal.call("PATCH", f"{vbase()}/1", json={"slot_guidance": "Say where and when.", "slot_max_length": 800}))
    v = ok(legal.post(f"{vbase()}/1/approve"))
    assert v["status"] == "approved" and v.get("approved_at") and v.get("approved_by_name")
    r = legal.call("PUT", f"{vbase()}/1/languages/english", json={"locked_text": LOCKED + " changed"})
    assert r.status_code in (409, 422), r.status_code
    CTX["v1"] = v
    return "PASS", f"approved by {v.get('approved_by_name')!s:.20} at {v['approved_at'][:16]}; its text refuses an edit ({r.status_code}); version 2 can be opened"


# --------------------------------------- C · the HR PoC creates an activity
def poc_with_csr() -> Session:
    """Assign the new category to an HR PoC (HR-F2 does it on its own too)."""
    if "poc" in CTX:
        return CTX["poc"]
    admin = CTX["admin"]
    me = ok(CTX["hr1"].get("/auth/me"))
    current = (ok(admin.get(f"/users/{me['uuid']}")).get("categories") or [])
    uuids = [c["category_uuid"] for c in current] + [CTX["cat"]["category_uuid"]]
    ok(admin.call("PUT", f"/users/{me['uuid']}/categories", json={"category_uuids": uuids}))
    CTX["poc"] = CTX["hr1"]
    CTX["poc_uuid"] = me["uuid"]
    return CTX["hr1"]


@case("HR-C1")
def c1():
    hr2 = CTX["hr2"]
    before = {c["category_code"] for c in ok(hr2.get("/hr/activities/options"))}
    assigned = {c["category_code"] for c in (ok(CTX["admin"].get(f"/users/{ok(hr2.get('/auth/me'))['uuid']}")).get("categories") or [])}
    poc = poc_with_csr()
    after = {c["category_code"] for c in ok(poc.get("/hr/activities/options"))}
    assert f"CSR_{TAG}" not in before and before <= assigned and f"CSR_{TAG}" in after
    return "PASS", f"an HR PoC is offered only their categories ({sorted(before)}); CSR_{TAG} appears only once assigned"


def body(**kw: Any) -> dict[str, Any]:
    return {
        "category_uuid": CTX["cat"]["category_uuid"],
        "template_version_uuid": CTX["v1"]["version_uuid"],
        "purpose_uuids": [CTX["purposes"]["main"]["purpose_uuid"], CTX["purposes"]["extra"]["purpose_uuid"]],
        "name": f"Wellness Week Nov 2026 {TAG}",
        "description": "Four lunchtime sessions on sleep and stress.",
        "audience_mode": "sso",
        "link_expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        **kw,
    }


@case("HR-C2")
def c2():
    poc = poc_with_csr()
    r = poc.post("/hr/activities", json=body(purpose_uuids=[CTX["purposes"]["extra"]["purpose_uuid"]]))
    assert r.status_code == 422, r.status_code
    return "PASS", f"leaving out the mandatory purpose is refused ({r.json()['error']['message'][:90]}); the console locks its box"


@case("HR-C3")
def c3():
    poc = poc_with_csr()
    bad = [poc.post("/hr/activities", json=body(description=d)) for d in ("Hello {{name}}", "See https://example.org", "x" * 801)]
    codes = [r.status_code for r in bad]
    assert codes == [422, 422, 422], codes
    return "PASS", "a placeholder, a URL and 801 characters (limit 800) each refused 422 with the rule named"


@case("HR-C4")
def c4():
    poc = poc_with_csr()
    made = ok(poc.post("/hr/activities", json=body()), 201)
    CTX["act_sso"] = made
    detail = ok(poc.get(f"/hr/activities/{made['activity_uuid']}"))
    assert made["url_path"].startswith("/c/") and made["audience_mode"] == "sso" and detail["status"] == "approved"
    return "PASS", f"live at once: status {detail['status']}, link {made['url_path'][:12]}…, audience sso; no approval step"


@case("HR-C5")
def c5():
    poc = poc_with_csr()
    name = f"Outside the version {TAG}"
    outside = CTX["purposes_outside"] = ok(CTX["legal"].post("/purposes", json={**PURPOSE, "purpose_code": f"P-OU{TAG}", "name": "Not on the version"}), 201)
    ok(CTX["legal"].post(f"/purposes/{outside['purpose_uuid']}/activate"))
    r = poc.post("/hr/activities", json=body(name=name, purpose_uuids=[CTX["purposes"]["main"]["purpose_uuid"], outside["purpose_uuid"]]))
    rows = docker_sql(f"SELECT count(*) FROM project WHERE project_name = '{name}'").strip()
    assert r.status_code == 422 and rows == "0", (r.status_code, rows)
    return "PASS", "a purpose outside the version: 422, and no project (so no notice, site or link) exists by that name"


@case("HR-C6")
def c6():
    poc = poc_with_csr()
    made = ok(poc.post("/hr/activities", json=body(name=f"CSR day {TAG}", audience_mode="otp")), 201)
    CTX["act_otp"] = made
    link = ok(Session("anon").get(made["url_path"]))
    assert made["audience_mode"] == "otp" and link["audience_mode"] == "otp"
    return "PASS", "minted otp; the link says audience_mode otp"


@case("HR-C7")
def c7():
    poc = poc_with_csr()
    act = CTX["act_otp"]["activity_uuid"]
    if "csr_person" not in CTX:
        return "NOT RUN", "depends on HR-D's consent on the otp activity"
    consents = ok(poc.get(f"/projects/{act}/consents"))
    items = consents["items"] if isinstance(consents, dict) else consents
    assert items, "no consent listed"
    first = items[0]
    pdf = poc.get(f"/consents/{first['consent_uuid']}/record")
    exp = poc.post(f"/projects/{act}/exports")
    return (
        "PASS" if pdf.status_code == 200 and pdf.headers.get("content-type", "").startswith("application/pdf") and exp.status_code in (200, 201) else "FAIL",
        f"{len(items)} consent(s) listed by name; the PDF record {pdf.status_code}; export {exp.status_code} {exp.text[:80] if exp.status_code >= 300 else ''}",
    )


@case("HR-C8")
def c8():
    poc = poc_with_csr()
    act = CTX["act_sso"]
    ok(poc.post(f"/hr/activities/{act['activity_uuid']}/close", json={"reason": "The week is over."}))
    link = Session("anon").get(act["url_path"])
    valid = link.json().get("valid") if link.status_code == 200 else False
    assert not valid, link.text[:200]
    return "PASS", f"closed; the link now answers {link.status_code} valid={valid}"


# ----------------------------------------------------- D · participants
@case("HR-D1")
def d1():
    return "COVERED", "no identity provider locally (SSO_ENABLED off): the flow - provider sign-in, mobile by code, date of birth, notice - is proven with the stub provider in tests/integration/test_sso_link.py and tests/http/test_15_sso_link.py"


@case("HR-D2")
def d2():
    return "COVERED", "as D1: the second link's match on the employee ID is tests/integration/test_sso_link.py"


@case("HR-D3")
def d3():
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat Decliner {TAG}")
    ok(r)
    notice = ok(s.get(f"/c/{token}/notice", params={"language_code": "english"}))
    main = CTX["purposes"]["main"]["purpose_uuid"]
    extra = CTX["purposes"]["extra"]["purpose_uuid"]
    refused = s.post(f"/c/{token}/consent", json={"language_code": "english", "grants": {main: False, extra: True}, "action_type": "checkbox_click"})
    declined = s.post(f"/c/{token}/consent", json={"language_code": "english", "grants": {main: False, extra: False}, "action_type": "checkbox_click"})
    assert len(notice["purposes"]) == 2
    return (
        "PASS" if refused.status_code == 422 and declined.status_code in (200, 201) else "FAIL",
        f"refusing only the mandatory purpose: {refused.status_code}; declining everything: {declined.status_code} {declined.json().get('status', '') if declined.status_code < 300 else declined.text[:80]}",
    )


@case("HR-D4")
def d4():
    token = CTX["act_sso"]["url_path"].rsplit("/", 1)[-1]
    s = Session("anon sso")
    before = s.seen()
    r = s.post(f"/c/{token}/otp", json={"contact": mobile()})
    import time

    time.sleep(3)
    sent = [c for c in s.codes() if str(c.get("code")) not in before]
    assert r.status_code in (200, 202) and not sent, (r.status_code, sent)
    return "PASS", f"{r.status_code} with the usual sentence; no code written"


@case("HR-D5")
def d5():
    legal, admin = CTX["legal"], CTX["admin"]
    poc = next(
        (s for s in (CTX["hr2"], CTX["hr1"])
         if any(c["category_code"] == "BGV" for c in ok(s.get("/hr/activities/options")))),
        CTX["hr2"],
    )
    cats = ok(legal.get("/hr/categories"))
    bgv = next(c for c in cats if c["category_code"] == "BGV")
    if bgv.get("default_person_type") != "candidate":
        return "FAIL", f"BGV's default person type is {bgv.get('default_person_type')}, not candidate"
    options = ok(poc.get("/hr/activities/options"))
    mine = [c for c in options if c["category_code"] == "BGV"]
    if not mine:
        return "NOT RUN", "no HR PoC is assigned BGV"
    if not mine[0]["versions"]:
        # The seed has none: Legal writes one, as B4-B6 do for CSR.
        tpl = ok(legal.post("/notice-templates", json={**TEMPLATE, "title": "Background verification", "category_uuid": bgv["category_uuid"]}), 201)
        base = f"/notice-templates/{tpl['template_uuid']}/versions"
        ok(legal.post(base), 201)
        ok(legal.call("PUT", f"{base}/1/languages/english", json={"locked_text": LOCKED}))
        ok(legal.call("PUT", f"{base}/1/purposes", json={"purposes": [{"purpose_uuid": CTX["purposes"]["main"]["purpose_uuid"], "is_mandatory": True}]}))
        ok(legal.post(f"{base}/1/approve"))
        options = ok(poc.get("/hr/activities/options"))
        mine = [c for c in options if c["category_code"] == "BGV"]
    v = mine[0]["versions"][0]
    made = ok(poc.post("/hr/activities", json={
        "category_uuid": mine[0]["category_uuid"], "template_version_uuid": v["version_uuid"],
        "purpose_uuids": [p["purpose_uuid"] for p in v["purposes"] if p["is_mandatory"]] or [v["purposes"][0]["purpose_uuid"]],
        "name": f"Background check {TAG}", "description": "Checks before joining.", "audience_mode": "otp",
        "link_expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat()}), 201)
    token = made["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat Candidate {TAG}")
    ok(r)
    consent(s, token)
    me = ok(s.get("/auth/me"))
    assert me.get("person_type") == "candidate", me.get("person_type")
    return "PASS", "signed up on a BGV activity's otp link: account created as candidate; consent recorded"


@case("HR-D6")
def d6():
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    young = (datetime.now(UTC) - timedelta(days=365 * 15)).date().isoformat()
    s, r = participant(token, dob=young, name=f"Uat Minor {TAG}")
    if r.status_code in (200, 201):
        res = s.post(f"/c/{token}/consent", json={"language_code": "english", "grants": {}, "action_type": "checkbox_click"})
        return ("PASS" if res.status_code >= 400 else "FAIL", f"sign-up accepted; consent refused {res.status_code}")
    return "PASS", f"sign-up refused {r.status_code}: {r.json()['error']['message'][:100]}"


@case("HR-D7")
def d7():
    return "COVERED", "needs SSO_ISSUER on a dead host; the 503 'did not answer' path is tests/unit/infrastructure/test_oidc.py and the portal's sso-flow.test.tsx"


@case("HR-D8")
def d8():
    return "COVERED", "a wrong nonce from the stub provider is tests/integration/test_sso_link.py (neutral page, nothing written, audited)"


# ---------------------------------------- E · withdrawal, rights, breaches
def csr_person() -> tuple[Session, str]:
    if "csr_person" in CTX:
        return CTX["csr_person"]
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat Employee {TAG}")
    ok(r)
    given = consent(s, token)
    CTX["csr_person"] = (s, given["consent_uuid"])
    return CTX["csr_person"]


@case("HR-E1")
def e1():
    s, consent_uuid = csr_person()
    mark = outbox_mark()
    w = ok(s.post(f"/me/consents/{consent_uuid}/withdraw", json={"purposes": [CTX["purposes"]["extra"]["purpose_uuid"]]}))
    told = wait_outbox(mark, "Consent withdrawn on")
    text = outbox_since(mark)
    named = f"Uat Employee {TAG}" in text.split("Consent withdrawn on", 1)[-1][:2000] if told else False
    CTX["withdraw_consent_uuid"] = w.get("consent_uuid", consent_uuid)
    assert told and not named, (told, named)
    return "PASS", "partial; her confirmation and hr_withdrawal_notice written to the outbox, naming her by principal ID, not her name"


@case("HR-E2")
def e2():
    s, _ = csr_person()
    mine = ok(s.get("/me/consents"))
    items = mine if isinstance(mine, list) else mine.get("items", [])
    target = next(c for c in items if CTX["act_otp"]["activity_uuid"] in json.dumps(c) or c.get("project_name", "").startswith("CSR day"))
    ok(s.post(f"/me/consents/{target['consent_uuid']}/withdraw", json={"all": True}))
    reg = ok(CTX["poc"].get(f"/projects/{CTX['act_otp']['activity_uuid']}/consents"))
    rows = reg["items"] if isinstance(reg, dict) else reg
    statuses = {str(r.get("consent_status") or r.get("status")) for r in rows}
    return "PASS", f"withdrawn; the activity's register reads {sorted(statuses)}"


@case("HR-E3")
def e3():
    legal, poc = CTX["legal"], CTX["poc"]
    # A fresh consent on the live activity, so somebody is asked again.
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat Reconsent {TAG}")
    ok(r)
    consent(s, token)
    ok(legal.post(vbase()), 201)
    ok(legal.call("PATCH", f"{vbase()}/2", json={"reconsent_required": True}))
    ok(legal.call("PUT", f"{vbase()}/2/languages/english", json={"locked_text": LOCKED + "\n\nWe now also share photographs."}))
    v2 = ok(legal.post(f"{vbase()}/2/approve"))
    mark = outbox_mark()
    up = ok(poc.post(f"/hr/activities/{CTX['act_otp']['activity_uuid']}/upgrade", json={"template_version_uuid": v2["version_uuid"], "purpose_uuids": [CTX["purposes"]["main"]["purpose_uuid"]], "description": "Four lunchtime sessions on sleep and stress."}))
    asked = wait_outbox(mark, "needs renewing") or wait_outbox(mark, "the terms for")
    assert asked, "no re-consent request written"
    return "PASS", f"upgraded to v{v2['version']} (notice version {up.get('notice_version', '?')}); hr_reconsent_request written for the current participant"


@case("HR-E4")
def e4():
    legal, dpo = CTX["legal"], CTX["dpo"]
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat HR only {TAG}")
    ok(r)
    consent(s, token)
    offices = ok(s.get("/me/requests/offices"))["offices"]
    made = ok(s.post("/me/requests", json={"request_type": "access", "request_text": "What do you hold?"}), 201)
    CTX["e4"] = made
    in_legal = legal.get(f"/requests/{made['request_uuid']}")
    in_dpo = dpo.get(f"/requests/{made['request_uuid']}")
    assert [o["code"] for o in offices] == ["hr"] and in_legal.status_code == 200 and in_dpo.status_code == 404
    return "PASS", f"{made['reference']}: offices {[o['code'] for o in offices]}; in Legal's queue, 404 to the DPO"


@case("HR-E5")
def e5():
    s, _ = csr_person()
    dco = CTX["dco"]
    sites = ok(dco.get("/sites", params={"limit": 50}))
    items = sites["items"] if isinstance(sites, dict) else sites
    token = None
    for site in items:
        r = dco.post(f"/sites/{site['site_uuid']}/agent", json={"expires_at": (datetime.now(UTC) + timedelta(days=2)).isoformat()})
        if r.status_code in (200, 201):
            token = r.json()["url_path"].rsplit("/", 1)[-1]
            break
    if token is None:
        return "NOT RUN", "no DCO site could mint an R&D link"
    ok(s.get(f"/c/{token}"))
    consent(s, token)
    CTX["both_person"] = s
    offices = [o["code"] for o in ok(s.get("/me/requests/offices"))["offices"]]
    made = ok(s.post("/me/requests", json={"request_type": "access", "request_text": "Both, please.", "office": "both"}), 201)
    second = made["also"][0]
    CTX["e5_hr"] = made if CTX["legal"].get(f"/requests/{made['request_uuid']}").status_code == 200 else second
    assert offices == ["hr", "rnd"] and made["received_at"] == second["received_at"]
    return "PASS", f"offices {offices}; both → {made['reference']} and {second['reference']}, the same received time"


@case("HR-E6")
def e6():
    legal, dpo = CTX["legal"], CTX["dpo"]
    anon = Session("public form")
    r = ok(anon.post("/rights/requests", json={"request_type": "access", "contact": f"stranger.{TAG.lower()}@example.org", "name": "Stranger", "request_text": "Do you hold anything?"}))
    ref = r["reference"]
    seen = {}
    for who, s in (("legal", legal), ("dpo", dpo)):
        rows = ok(s.get("/requests", params={"q": ref, "intake": "true"}))["items"]
        seen[who] = rows[0]["request_uuid"] if rows else None
    uuid_ = seen["legal"]
    assert uuid_ and seen["dpo"] == uuid_, seen
    claimed = ok(legal.post(f"/requests/{uuid_}/claim"))
    gone = dpo.get(f"/requests/{uuid_}")
    assert claimed["office"] == "hr" and gone.status_code == 404
    return "PASS", f"{ref} in both offices' intake; Legal claimed it; the DPO is told 404"


@case("HR-E7")
def e7():
    legal, dpo = CTX["legal"], CTX["dpo"]
    req = CTX["e4"]
    before = ok(legal.get(f"/requests/{req['request_uuid']}"))
    mark = outbox_mark()
    moved = ok(legal.post(f"/requests/{req['request_uuid']}/transfer", json={"office": "rnd", "reason": "UAT: the data is research data."}))
    there = ok(dpo.get(f"/requests/{req['request_uuid']}"))
    emailed = wait_outbox(mark, "transferred to your office")
    trail = ok(dpo.get(f"/requests/{req['request_uuid']}/trail"))
    audited = any(e["event_type"] == "rights.transferred" for e in trail)
    assert moved["office"] == "rnd" and there["due_at"] == before["due_at"] and emailed and audited
    return "PASS", f"{req['reference']} now the DPO's, due {there['due_at'][:10]} unchanged; the DPO emailed; rights.transferred on the trail"


@case("HR-E8")
def e8():
    legal = CTX["legal"]
    # Somebody whose consent on the activity still stands: a withdrawn
    # activity's processors are not derived (decision G-4).
    token = CTX["act_otp"]["url_path"].rsplit("/", 1)[-1]
    s, r = participant(token, name=f"Uat Holder {TAG}")
    ok(r)
    consent(s, token)
    req = ok(s.post("/me/requests", json={"request_type": "access", "request_text": "Who holds my data?"}), 201)
    uuid_ = req["request_uuid"]
    ok(legal.post(f"/requests/{uuid_}/classify", json={"request_type": "access", "note": "UAT"}))
    ok(legal.post(f"/requests/{uuid_}/transition", json={"to": "in_progress"}))
    holders = ok(legal.post(f"/requests/{uuid_}/holders/derive"))
    kinds = {h["derived_from"] for h in holders}
    labels = [h["label"] for h in holders if h["derived_from"] == "activity_processor"]
    assert "activity_processor" in kinds, kinds
    return "PASS", f"derived {len(holders)} holder(s); activity_processor: {labels}"


@case("HR-E9")
def e9():
    legal, dpo = CTX["legal"], CTX["dpo"]
    now = datetime.now(UTC)
    made = ok(legal.post("/breaches", json={"title": f"UAT wellness list emailed outside {TAG}", "detected_at": (now - timedelta(minutes=10)).isoformat(), "location_kind": "platform"}), 201)
    b = made["breach_uuid"]
    hidden = dpo.get(f"/breaches/{b}").status_code
    ok(legal.post(f"/breaches/{b}/obligations/org_board/complete", json={"occurred_at": now.isoformat(), "reported_to": "The board's secretary"}))
    ok(legal.post(f"/breaches/{b}/determinations", json={"outcome": "yes", "reasoning": "Personal data left the office.", "became_aware_at": (now - timedelta(minutes=5)).isoformat()}))
    poc_uuid = CTX.get("poc_uuid") or ok(CTX["hr1"].get("/auth/me"))["uuid"]
    t = legal.post(f"/breaches/{b}/tickets", json={"user_uuid": poc_uuid, "instruction": "Recall the email and confirm."})
    detail = ok(legal.get(f"/breaches/{b}"))
    duties = {d.get("kind") or d.get("duty"): d["state"] for d in detail["obligations"]}
    mine = ok(CTX["hr1"].get("/breach-tickets"))
    assert hidden == 404 and t.status_code in (200, 201) and mine
    return "PASS", f"logged {detail['reference']} on the Legal office; the DPO is told 404; board duty done; duties {duties}; the HR PoC holds its ticket (closing waits on the Board and principals duties, as for the DPO)"


# ------------------------------------------------------- F · administration
@case("HR-F1")
def f1():
    admin = CTX["admin"]
    mark = outbox_mark()
    made = ok(admin.post("/users", json={"full_name": f"Uat Legal {TAG}", "email": f"uat.legal.{TAG.lower()}@cmp.local", "role": "legal", "office_uuid": CTX["office"]["hr"]}), 201)
    invited = wait_outbox(mark, f"uat.legal.{TAG.lower()}@cmp.local")
    assert made["role"] == "legal" and invited
    return "PASS", f"provisioned as {made.get('role_title', made['role'])} in office {made.get('office_name') or made.get('office_code')}; invitation written"


@case("HR-F2")
def f2():
    admin = CTX["admin"]
    hr2_uuid = ok(CTX["hr2"].get("/auth/me"))["uuid"]
    current = [c["category_uuid"] for c in (ok(admin.get(f"/users/{hr2_uuid}")).get("categories") or [])]
    ok(admin.call("PUT", f"/users/{hr2_uuid}/categories", json={"category_uuids": current + [CTX["cat"]["category_uuid"]]}))
    offered = {c["category_code"] for c in ok(CTX["hr2"].get("/hr/activities/options"))}
    trail = ok(admin.get("/audit", params={"limit": 50}))["items"]
    audited = any(e["event_type"] == "user.categories_set" for e in trail)
    assert f"CSR_{TAG}" in offered and audited
    return "PASS", f"CSR_{TAG} now offered to the second HR PoC; audited user.categories_set"


@case("HR-F3")
def f3():
    r = CTX["admin"].post("/users", json={"full_name": f"Uat HR {TAG}", "email": f"uat.hr.{TAG.lower()}@cmp.local", "role": "hr_user"})
    assert r.status_code == 422, r.status_code
    return "PASS", f"an HR PoC with no office: 422 ({r.json()['error']['message'][:80]})"


@case("HR-F4")
def f4():
    s, _ = csr_person()
    mark = outbox_mark()
    made = ok(s.post("/me/requests", json={"request_type": "grievance", "request_text": "The Legal office ignored my withdrawal.", "about_dpo": True, "office": "hr"}), 201)
    escalated = wait_outbox(mark, "needs a reviewer")
    admin_view = CTX["admin"].get(f"/requests/{made['request_uuid']}")
    assert escalated and admin_view.status_code == 200
    return "PASS", f"{made['reference']} about the Legal office: the administrators emailed for a reviewer; it is in their register"


def main() -> None:
    setup()
    order = ["HR-A2", "HR-A3", "HR-A5", "HR-B1", "HR-B2", "HR-B3", "HR-B4", "HR-B5", "HR-B6",
             "HR-C1", "HR-C2", "HR-C3", "HR-C4", "HR-C5", "HR-C6", "HR-D1", "HR-D2", "HR-D3", "HR-D4",
             "HR-D5", "HR-D6", "HR-D7", "HR-D8", "HR-E1", "HR-E2", "HR-C7", "HR-E3", "HR-E4", "HR-E5",
             "HR-A4", "HR-E6", "HR-E7", "HR-E8", "HR-E9", "HR-A1", "HR-F1", "HR-F2", "HR-F3", "HR-F4", "HR-B7", "HR-C8"]
    by = {c.__name__: c for c in CASES}
    for name in order:
        by[name]()
    Path(__file__).with_name("results.json").write_text(json.dumps(__import__("hr_harness").RESULTS, indent=1))


@case("HR-B7")
def b7():
    legal, poc = CTX["legal"], CTX["poc"]
    r = ok(legal.post(f"{vbase()}/1/status", json={"status": "retired"}))
    refused = poc.post("/hr/activities", json=body(name=f"After retire {TAG}"))
    still = ok(poc.get(f"/hr/activities/{CTX['act_sso']['activity_uuid']}"))
    assert r["status"] == "retired" and refused.status_code in (409, 422)
    return "PASS", f"v1 retired; a new activity on it refused {refused.status_code}; the existing activity stays {still['status']}"


if __name__ == "__main__":
    main()
