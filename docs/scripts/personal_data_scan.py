#!/usr/bin/env python3
"""Rebuild the endpoint tables in `docs/domain/personal-data.md`.

Three artefacts the repository already keeps current are joined here:

* `backend/api/openapi.json` - every operation and every field of every request
  and response schema, resolved through `$ref` so a field nested several models
  deep is still found;
* `api_access_control/endpoint_permissions.json` - the guard on each route and
  the permission matrix's answer per role;
* `database_schema/schema_inventory.json` - every table and column, used only to
  cross-check that a column carrying personal data has a field name this script
  knows about.

What it cannot do on its own is decide that a *new* field name is personal. So
it does the next best thing: anything that looks like a person's data by shape
and is not in one of the lists below is reported as UNCLASSIFIED and the script
exits non-zero. Teach it the field, or record why the field is not personal, and
the document stays true.

    python3 docs/scripts/personal_data_scan.py            # the tables
    python3 docs/scripts/personal_data_scan.py --check    # only the warnings
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------- the lists
#
# A field is personal data if it says something about a natural person. The
# categories are the ones the document is organised by; a field may only be in
# one, and where it could be in two the more sensitive wins.

IDENTITY = {
    "full_name", "submitted_name", "nominee_name", "responder_name",
    "responder_user_name", "actor_name", "author_name", "changed_by_name",
    "confirmed_by_name", "created_by_name", "dco_name", "decided_by_name",
    "delegate_name", "delegator_name", "exported_by_name", "imported_by_name",
    "overridden_by_name", "owner_name", "principal_name", "reviewer_name",
    "subject_name", "updated_by_name", "uploaded_by_name", "verified_by_name",
    "username",
}
CONTACT = {
    "email", "secondary_email", "mobile", "contact", "submitted_contact",
    "responder_contact", "nominee_email", "nominee_mobile", "nominee_contact",
    "subject_email", "subject_mobile", "delegate_email", "delegator_email",
    "dpo_contact", "login", "hint",
    # Not a contact, but the state of one: NULL means it signs nobody in.
    "email_verified_at", "mobile_verified_at", "secondary_email_verified_at",
}
DEMOGRAPHIC = {
    "dob", "is_minor", "person_type", "organization_id", "role", "user_role",
    "account_role", "actor_role", "owner_role", "delegate_role",
    "delegator_role", "from_type", "to_type", "subject_role",
}
DEVICE = {
    "ip_address", "user_agent", "last_seen_at", "session_expires_at", "seen_at",
    "office_read_at", "holder_read_at",
}
CREDENTIAL = {
    "password", "current_password", "new_password", "code", "email_code",
    "mobile_code", "url_path", "accept_token", "mfa_required", "mfa_verified",
    # Columns rather than fields: none of these appears in any response schema,
    # and the point of listing them is that the document says where they live.
    "password_hash", "token", "token_sealed", "accept_token_hash",
}
ACCOUNT_REF = {
    "user_uuid", "subject_uuid", "actor_uuid", "delegate_uuid",
    "delegate_user_uuid", "delegator_uuid", "delegator_user_uuid",
    "owner_user_uuid", "responder_user_uuid", "reviewer_uuid",
    "uploaded_by_uuid", "imported_by_uuid", "changed_by_uuid",
    "nominee_user_uuid", "nominee_user_id",
}
FREE_TEXT = {
    "request_text", "response_text", "remedy_text", "verification_note",
    "refusal_reason", "return_summary", "sent_back_reason", "instruction",
    "brief", "body", "contact_log", "reason", "evidence", "decision_reason",
}
FILE = {
    "file_name", "file_uuid", "files", "response_files", "evidence_name",
    "evidence_hash", "proof", "proof_file_hash", "storage_ref", "document",
    "manifest", "sample", "return_evidence_name", "return_evidence_hash",
    "response_file_hash", "trigger_evidence_hash", "content_type", "size_bytes",
    "download_available", "download_expires_at",
}
CONSENT = {
    "consent_uuid", "consent_status", "consent_at", "consent_purposes",
    "consent_notice_code", "consent_notice_version", "consent_project",
    "consent_project_uuid", "consent_withdrawn", "granted", "grants",
    "granted_count", "is_withdrawal", "served_at", "affirmative_action_at",
    "action_type", "disposition", "bystander_count", "subject_count",
    "other_subjects", "mapped_asset_count", "has_unmapped_subjects",
    "refused_count", "consents", "withdrawals", "registrations",
}

CATEGORIES = [
    ("identity", IDENTITY), ("contact", CONTACT), ("demographic", DEMOGRAPHIC),
    ("device", DEVICE), ("credential", CREDENTIAL), ("account-ref", ACCOUNT_REF),
    ("free-text", FREE_TEXT), ("file", FILE), ("consent-record", CONSENT),
]

#: Field names that look personal and are not. Each one is a decision, so each
#: one is written down: a reviewer who disagrees can see what was decided.
NOT_PERSONAL = {
    "name": "a purpose, a source, a site or a template - never a person",
    "legal_name": "a processor is an organisation",
    "note": "an instruction to whoever collects, and never served to a principal",
    "description": "what a purpose or a project is for",
    "summary": "a count of things, or the office's own note on a ticket return",
    "message": "an acknowledgement sentence in a response envelope",
    "detail": "the audit row's own structured detail, listed under audit",
    "channel": "email or SMS, not an address",
    "channels": "which mediums a template has",
    "medium": "email or SMS",
    "mediums": "which mediums are available",
    "label": "the name of a team or a holder, not a person",
    "location": "where a collection site is",
    "site_label": "the name of a site",
    "subject": "the subject line of a message template",
    "reference": "the public reference of a request",
    "contract_ref": "a contract identifier",
    "agent_ref": "a field agent's reference, set by the source",
    "source_asset_ref": "the source's own identifier for an asset",
    "project_name": "what a study is called",
    "internal_project_name": "the same study's internal code",
    "processor_name": "an organisation",
    "source_name": "a data source",
}

#: Shapes that suggest a person. Anything matching and unclassified is reported.
SUSPICIOUS = re.compile(
    r"(name|email|mobile|phone|contact|address|dob|birth|gender|guardian"
    r"|nominee|person|password|passwd|otp|token|ip_|user_agent)", re.I
)


def category(field: str) -> str | None:
    for name, members in CATEGORIES:
        if field in members:
            return name
    return None


# ----------------------------------------------------------------- the join
def load() -> tuple[dict, list, dict]:
    spec = json.loads((ROOT / "backend/api/openapi.json").read_text())
    perms = json.loads((ROOT / "api_access_control/endpoint_permissions.json").read_text())
    schema = json.loads((ROOT / "database_schema/schema_inventory.json").read_text())
    return spec, perms["endpoints"], schema


def fields_of(node: object, schemas: dict, seen: frozenset[str] = frozenset(), depth: int = 0) -> set[str]:
    """Every property name reachable from a schema node, through every $ref."""
    out: set[str] = set()
    if depth > 8 or not isinstance(node, dict):
        return out
    if "$ref" in node:
        name = node["$ref"].split("/")[-1]
        if name in seen:
            return out
        return fields_of(schemas.get(name, {}), schemas, seen | {name}, depth + 1)
    for key in ("anyOf", "oneOf", "allOf"):
        for sub in node.get(key, []):
            out |= fields_of(sub, schemas, seen, depth + 1)
    if "items" in node:
        out |= fields_of(node["items"], schemas, seen, depth + 1)
    extra = node.get("additionalProperties")
    if isinstance(extra, dict):
        out |= fields_of(extra, schemas, seen, depth + 1)
    for prop, sub in (node.get("properties") or {}).items():
        out.add(prop)
        out |= fields_of(sub, schemas, seen, depth + 1)
    return out


def operations(spec: dict) -> dict[tuple[str, str], tuple[set[str], set[str]]]:
    schemas = spec["components"]["schemas"]
    found = {}
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            incoming: set[str] = set()
            for media in (op.get("requestBody", {}).get("content") or {}).values():
                incoming |= fields_of(media.get("schema", {}), schemas)
            for param in op.get("parameters") or []:
                incoming.add(param["name"])
            outgoing: set[str] = set()
            for code, response in (op.get("responses") or {}).items():
                if code.startswith("2"):
                    for media in (response.get("content") or {}).values():
                        outgoing |= fields_of(media.get("schema", {}), schemas)
            found[(method.upper(), path)] = (incoming, outgoing)
    return found


def rows(spec: dict, endpoints: list) -> list[dict]:
    ops = operations(spec)
    out = []
    for e in endpoints:
        key = (e["method"], e["path"])
        if key not in ops:            # health and root, which have no schema
            continue
        incoming, outgoing = ops[key]
        # A language rendition is addressed by `{code}`, which is a language and
        # not a one-time code. The only place the name means something else.
        if "/languages/" in e["path"]:
            incoming = incoming - {"code"}
        cin = sorted({f for f in incoming if category(f)})
        cout = sorted({f for f in outgoing if category(f)})
        if cin or cout:
            out.append({**{k: e[k] for k in ("module", "method", "path", "gate",
                                             "authentication", "anonymous")},
                        "access": e["access"], "in": cin, "out": cout})
    return out


# ------------------------------------------------------------- the warnings
def unclassified(spec: dict, schema: dict) -> list[str]:
    """Field and column names that look personal and are in neither list."""
    problems = []
    seen = set()
    for model in spec["components"]["schemas"].values():
        seen |= set(model.get("properties") or {})
    for column in schema["columns"]:
        seen.add(column["name"])
    for field in sorted(seen):
        if category(field) or field in NOT_PERSONAL:
            continue
        if SUSPICIOUS.search(field):
            problems.append(field)
    return problems


# ---------------------------------------------------------------- rendering
SHORT = {"dpo": "DPO", "admin": "Admin", "dco": "DCO", "dco_admin": "DCO Admin",
         "rco": "RCO", "rnd_user": "R&D", "data_subject": "Principal"}
VALUE = {"ALL": "every row", "SCOPED": "rows in scope", "OWN": "own rows",
         "COND": "conditional"}
ORDER = ["auth", "me", "public consent", "public information", "rights", "tickets",
         "consent", "exchange", "users", "delegations", "projects", "notices",
         "registry", "messages", "audit", "dashboard"]
TITLE = {
    "auth": "Authentication — `/auth/*`",
    "me": "The data principal's own records — `/me/*`",
    "public consent": "The consent link — `/c/{token}/*`",
    "public information": "The public rights surface — `/rights/*`",
    "rights": "Rights requests, the office's side — `/requests/*`",
    "tickets": "Tickets a holder answers — `/tickets/*`",
    "consent": "Consents and links, the office's side",
    "exchange": "Exports, imports, collections and assets",
    "users": "The staff register — `/users/*`",
    "delegations": "Delegation — `/delegations/*`",
    "projects": "Projects, approvals and sites",
    "notices": "Notices",
    "registry": "Purposes, processors and sources",
    "messages": "Message templates — `/messages/*`",
    "audit": "The audit trail — `/audit/*`",
    "dashboard": "Dashboard",
}


def who(row: dict) -> str:
    if row["anonymous"] == "YES":
        return "**public** — no session"
    if row["anonymous"] == "COND":
        return "**public** — the request carries its own credential (password, link token, one-time code)"
    grants = {k: v for k, v in row["access"].items() if v != "NO"}
    if not grants:
        return "any signed-in session"
    if len(grants) == 7 and set(grants.values()) == {"OWN"}:
        return "any signed-in session, own record"
    if len(grants) == 7 and set(grants.values()) == {"COND"}:
        return "any signed-in session, conditionally"
    return ", ".join(f"{SHORT[k]} {VALUE.get(v, v.lower())}" for k, v in grants.items())


def tables(found: list[dict]) -> str:
    grouped = defaultdict(list)
    for row in found:
        grouped[row["module"]].append(row)
    lines = []
    for module in ORDER:
        group = sorted(grouped[module], key=lambda r: (r["path"], r["method"]))
        plural = "s" if len(group) != 1 else ""
        lines += [f"\n### {TITLE[module]}\n",
                  f"{len(group)} operation{plural} carry personal data.\n",
                  "| Method | Endpoint | Who may call it | Personal data in | Personal data out |",
                  "|---|---|---|---|---|"]
        for row in group:
            cin = ", ".join(f"`{f}`" for f in row["in"]) or "—"
            cout = ", ".join(f"`{f}`" for f in row["out"]) or "—"
            lines.append(f"| {row['method']} | `{row['path']}` | {who(row)} | {cin} | {cout} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only report unclassified fields")
    args = parser.parse_args()

    spec, endpoints, schema = load()
    found = rows(spec, endpoints)
    if not args.check:
        print(tables(found))

    total = sum(1 for path, item in spec["paths"].items()
                for method in item if method in ("get", "post", "put", "patch", "delete"))
    public = sum(1 for r in found if r["anonymous"] != "NO")
    print(f"\n<!-- {len(found)} of {total} operations carry personal data; "
          f"{public} of them need no session. -->", file=sys.stderr if args.check else sys.stdout)

    problems = unclassified(spec, schema)
    if problems:
        print("\nUNCLASSIFIED — these look personal and are in neither list:", file=sys.stderr)
        for field in problems:
            print(f"  {field}", file=sys.stderr)
        print("\nAdd each to a category in this file, or to NOT_PERSONAL with the "
              "reason it is not.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
