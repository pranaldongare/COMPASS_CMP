"""What every response has to satisfy, and the ledger that says every endpoint was asked.

Two rules, applied to every response the suite receives:

1. **A sealed field is served sealed.** For every field name in `SEALED` found
   anywhere in the body - at any depth, in any list - the value is `None` or
   begins `SE::`. A plaintext name, address or request text in a response is a
   failure, wherever it sits.
2. **A plaintext contact never appears where a sealed one belongs.** The same
   walk checks that no value under a sealed field name looks like an email or a
   mobile in the clear. Rule 1 catches the field; this catches the shape.

And one rule about the suite itself: **every endpoint in the PII list is
called.** `LEDGER` records each (method, path template) the suite touches, and
`test_every_pii_endpoint_was_exercised` in `test_zz_coverage.py` compares it
against the list the documentation is generated from. An endpoint added to the
API and not to this suite fails the build, which is the only way "every
endpoint" stays true.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS

ROOT = Path(__file__).resolve().parents[4]  # tests/http/<file> -> backend/api -> repo

#: Every column the repositories seal, by name - and the names the API gives
#: them when it joins them onto another row. A field in a response under any
#: of these names is a sealed value.
SEALED: frozenset[str] = frozenset(
    # `name` is sealed on processor_respondent alone and is the name of a
    # purpose, a queue, a source and a template everywhere else; it is checked
    # where the respondent is read rather than by field name.
    ({column for columns in ENCRYPTED_FIELDS.values() for column in columns} - {"name"})
    | {
        # joined names of people, from auth_user.full_name
        "created_by_name",
        "dco_name",
        "actor_name",
        "subject_name",
        "author_name",
        "changed_by_name",
        "confirmed_by_name",
        "decided_by_name",
        "placed_by_name",
        "listed_by_name",
        "lifted_by_name",
        "released_by_name",
        "delegate_name",
        "delegator_name",
        "exported_by_name",
        "imported_by_name",
        "overridden_by_name",
        "owner_name",
        "principal_name",
        "reviewer_name",
        "updated_by_name",
        "uploaded_by_name",
        "verified_by_name",
        "responder_user_name",
        # joined contacts
        "delegate_email",
        "delegator_email",
        "subject_email",
        "subject_mobile",
        "nominee_contact",
        "responder_user_email",
    }
)

#: Fields that are personal but legitimately plaintext in a response: the
#: caller's own contact hint, masked contacts, and what the caller typed back.
ALLOWED_PLAIN: frozenset[str] = frozenset({"masked", "hint", "login", "contact", "code"})

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE = re.compile(r"^\+?\d[\d \-]{7,}\d$")

#: Public, token-gated endpoints serve plaintext by design: their page has no
#: session to decrypt with, and the token was the authorisation. Listed so the
#: rule can exempt them rather than be weakened for everybody.
PUBLIC_PLAINTEXT_PATHS: frozenset[str] = frozenset(
    {
        "/rights/nominations/{token}",
    }
)

#: One field on one endpoint that shares a name with a sealed column and is not
#: one: a session's address lives in Redis for hours, is the caller's own, and
#: is shown to nobody else. Sealing it to have the portal open it would be
#: ceremony. Written down here so the exemption is a decision, not a gap.
PLAIN_BY_DESIGN: frozenset[tuple[str, str]] = frozenset(
    {
        ("/auth/sessions", "ip_address"),
        # The trail cannot be rewritten. Rows from before ADR 0015 carry a
        # `reason`, and the three feeds that show the trail show them. Nothing
        # written since carries one - test_no_reason_is_written_to_the_trail
        # holds that - so this exemption covers history and nothing else.
        ("/dashboard", "reason"),
        ("/audit", "reason"),
        ("/audit/{log_uuid}", "reason"),
        # The words of a message template are the office's, with `{variables}`
        # where a person's details go at send time. They share a name with a
        # ticket message's body and nothing else.
        *(
            (path, field)
            for path in (
                "/messages",
                "/messages/{key}",
                "/messages/{key}/{channel}",
                "/messages/{key}/{channel}/preview",
            )
            for field in ("body", "subject")
        ),
    }
)


def _walk(node: Any, path: str, out: list[tuple[str, str, Any]]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k in SEALED:
                out.append((f"{path}.{k}", k, v))
            _walk(v, f"{path}.{k}", out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]", out)


def assert_sealed(body: Any, *, where: str, endpoint: str = "") -> None:
    """Every sealed field in this body is ciphertext. Raise naming the first that is not."""
    found: list[tuple[str, str, Any]] = []
    _walk(body, "$", found)
    for path, field, value in found:
        if (endpoint, field) in PLAIN_BY_DESIGN:
            continue
        assert value.startswith("SE::"), (
            f"{where}: {path} is a sealed field served in the clear: {value[:40]!r}"
        )


#: Keys that are not sealed columns but may carry an address in a structure
#: served as it is stored - a contact log's `to`. Whatever their value, it may
#: not look like a contact.
ADDRESS_SHAPED: frozenset[str] = frozenset({"to"})


def assert_no_plaintext_contacts(body: Any, *, where: str) -> None:
    """No string under a sealed contact name looks like an address or a number."""
    found: list[tuple[str, str, Any]] = []
    _walk(body, "$", found)
    _walk_keys(body, "$", ADDRESS_SHAPED, found)
    for path, field, value in found:
        if field in ALLOWED_PLAIN:
            continue
        assert not EMAIL.match(value), f"{where}: {path} carries a plaintext email"
        assert not MOBILE.match(value), f"{where}: {path} carries a plaintext mobile"


def _walk_keys(node: Any, path: str, keys: frozenset[str], out: list[tuple[str, str, Any]]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and k in keys:
                out.append((f"{path}.{k}", k, v))
            _walk_keys(v, f"{path}.{k}", keys, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_keys(v, f"{path}[{i}]", keys, out)


# ------------------------------------------------------------------ the ledger
LEDGER: set[tuple[str, str]] = set()
#: The subset of the ledger whose responses carried at least one sealed field.
TOUCHED_SEALED: set[tuple[str, str]] = set()
#: A copy of the ledger on disk, for reading after a run (`docs/tools`), not
#: for the coverage test, which reads the in-process set so a stale file from
#: an earlier run can never make a missing endpoint look covered.
_LEDGER_FILE = Path(__file__).with_name(".ledger.json")


def _template(request: httpx.Request, template: str | None) -> str:
    return template or request.url.path


async def call(
    http: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    template: str | None = None,
    session: Any = None,
    expect: int | tuple[int, ...] = 200,
    check_sealed: bool = True,
    **kwargs: Any,
) -> httpx.Response:
    """One request, recorded in the ledger, its response checked against the rules.

    `template` is the OpenAPI path with its `{params}`, so the ledger can be
    compared with the documented list; it defaults to the concrete path for
    endpoints without parameters.
    """
    # Cookies travel as a header rather than httpx's per-request `cookies=`,
    # which is deprecated for being ambiguous about persistence - and this
    # suite wants none: each request says exactly who it is.
    jar: dict[str, str] = dict(kwargs.pop("cookies", {}) or {})
    headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
    if session is not None:
        jar.update(session.cookies)
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            headers.update(session.headers)
    if jar:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in jar.items())
    response = await http.request(method, path, headers=headers, **kwargs)
    key = (method.upper(), template or path)
    LEDGER.add(key)
    _persist()

    wanted = (expect,) if isinstance(expect, int) else expect
    assert response.status_code in wanted, (
        f"{method} {path} -> {response.status_code}, wanted {wanted}: {response.text[:300]}"
    )
    if check_sealed and (template or path) not in PUBLIC_PLAINTEXT_PATHS:
        ctype = response.headers.get("content-type", "")
        if ctype.startswith("application/json") and response.content:
            body = response.json()
            where = f"{method} {template or path}"
            assert_sealed(body, where=where, endpoint=template or path)
            assert_no_plaintext_contacts(body, where=where)
            found: list[tuple[str, str, Any]] = []
            _walk(body, "$", found)
            if any(v.startswith("SE::") for _, _, v in found):
                TOUCHED_SEALED.add(key)
    return response


def _persist() -> None:
    """The ledger survives across test files: pytest imports each module once,
    but the coverage test runs last and needs everything before it."""
    _LEDGER_FILE.write_text(json.dumps(sorted(LEDGER)))


def load_ledger() -> set[tuple[str, str]]:
    if _LEDGER_FILE.exists():
        return {tuple(x) for x in json.loads(_LEDGER_FILE.read_text())}
    return set(LEDGER)


def reset_ledger() -> None:
    LEDGER.clear()
    if _LEDGER_FILE.exists():
        _LEDGER_FILE.unlink()


def documented_pii_endpoints() -> set[tuple[str, str]]:
    """The endpoints the documentation lists as carrying personal data."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("scan", ROOT / "docs/tools/personal-data-scan.py")
    scan = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(scan)
    openapi, endpoints, _ = scan.load()
    return {(r["method"], r["path"]) for r in scan.rows(openapi, endpoints)}
