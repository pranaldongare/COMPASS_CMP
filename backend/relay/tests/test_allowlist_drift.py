"""The allow-list against the two things it was copied from.

`allowlist.PUBLIC_ROUTES` was read off the portal's API calls by hand, and
nothing tied the two together: the HR track's SSO steps were new portal calls,
answered 404 through the relay, with every suite green. These tests read the
portal's source and the API's OpenAPI document from this repository:

* every call the portal makes matches a row, or a development row;
* every row is an operation the API has.

A call whose path is not written out where it is made must be named here: in
`HELPERS` when a helper builds it, in `PASS_THROUGH` when the call only passes
on a path its own caller wrote (and that caller is scanned). Skipped when the
relay is checked out without the rest of the repository.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from cmp_relay.allowlist import DEV_ROUTES, PUBLIC_ROUTES, RouteTable

REPO = Path(__file__).resolve().parents[3]
PORTAL = REPO / "frontend" / "portal" / "src"
OPENAPI = REPO / "backend" / "api" / "openapi.json"

pytestmark = pytest.mark.skipif(
    not (PORTAL.is_dir() and OPENAPI.is_file()),
    reason="needs the portal's source and the API's openapi.json beside the relay",
)

#: Paths built by a helper: (file under src/, the expression) -> what it builds.
HELPERS: dict[tuple[str, str], str] = {
    ("features/holder-ticket/api.ts", "base(token)"): "/holder-tickets/{token}",
}

#: Calls that only pass on a path written by their caller, which is scanned.
PASS_THROUGH: frozenset[tuple[str, str]] = frozenset(
    {
        ("lib/api/client.ts", "url"),  # apiGet and the rest, over the axios instance
        ("lib/query/options.ts", "url"),  # useApiMutation: its callers name the path
    }
)

#: The helpers whose callers `_CALL` reads. A new helper that takes a path must
#: be added to `_CALL` and here, or its callers are never checked.
SCANNED_HELPERS = frozenset(
    {"apiGet", "apiPost", "apiPut", "apiPatch", "apiDelete", "apiDownload", "useApiMutation"}
)
#: Where the helpers live.
HELPER_FILES = ("lib/api", "lib/query")
#: A function or arrow whose first parameter is a path.
_TAKES_A_PATH = re.compile(
    r"export\s+(?:async\s+)?(?:function\s+(?P<fn>\w+)|const\s+(?P<const>\w+)\s*=\s*(?:async\s*)?)"
    r"\s*(?:<(?:[^<>]|<[^<>]*>)*>)?\s*\(\s*(?:url|path|endpoint|route)\b"
)

#: The ways the portal calls the API: the api* helpers, the axios instance
#: itself, and useApiMutation (a POST unless its second argument is "put").
_CALL = re.compile(
    r"\b(?:api(?P<api>Get|Post|Put|Patch|Delete|Download)"
    r"|http\.(?P<http>get|post|put|patch|delete)"
    r"|(?P<mutation>useApiMutation))"
    r"\s*(?:<(?:[^<>]|<[^<>]*>)*>)?\s*\(\s*"
)
_DEFINITION = re.compile(r"function\s+$")


@dataclass(frozen=True)
class Call:
    file: str
    line: int
    method: str
    #: The path as written: a literal, or the expression when it is not one.
    written: str
    literal: bool


def _argument(text: str, start: int) -> tuple[str, bool, int]:
    """The first argument at `start`: (its text, whether it is a string or
    template literal, where it ends)."""
    opener = text[start]
    if opener in "\"'":
        end = text.index(opener, start + 1)
        return text[start + 1 : end], True, end + 1
    if opener == "`":
        i, depth = start + 1, 0
        while True:
            if depth == 0 and text[i] == "`":
                return text[start + 1 : i], True, i + 1
            if text.startswith("${", i):
                depth += 1
                i += 2
                continue
            if depth and text[i] == "}":
                depth -= 1
            elif depth and text[i] == "{":
                depth += 1
            i += 1
    i, depth = start, 0
    while depth or text[i] not in ",)":
        depth += {"(": 1, ")": -1}.get(text[i], 0)
        i += 1
    return text[start:i].strip(), False, i


def _calls() -> list[Call]:
    found: list[Call] = []
    for path in sorted(PORTAL.rglob("*.ts*")):
        file = path.relative_to(PORTAL).as_posix()
        if ".test." in file or file.startswith("test/"):
            continue
        text = path.read_text(encoding="utf-8")
        for m in _CALL.finditer(text):
            if _DEFINITION.search(text[: m.start()][-40:]):
                continue  # the helper's own definition, not a call
            written, literal, end = _argument(text, m.end())
            if m["api"] == "Download":
                # A download with a body is a POST (the records by ID).
                method = "POST" if re.match(r"\s*,\s*[^)\s]", text[end:]) else "GET"
            elif m["api"]:
                method = m["api"].upper()
            elif m["http"]:
                method = m["http"].upper()
            else:
                method = "PUT" if re.match(r"\s*,\s*[\"']put[\"']", text[end:]) else "POST"
            line = text.count("\n", 0, m.start()) + 1
            found.append(Call(file, line, method, written, literal))
    return found


def _path(call: Call) -> str:
    """A concrete path for the call: helpers expanded, every other `${...}`
    and `{x}` a sample segment, the query string dropped."""
    written = call.written if call.literal else "${" + call.written + "}"

    def expand(m: re.Match[str]) -> str:
        return HELPERS.get((call.file, m[1].strip()), "x1")

    path = re.sub(r"\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", expand, written)
    path = re.sub(r"\{[a-z_]+\}", "x1", path)
    return path.split("?", 1)[0]


CALLS = _calls() if PORTAL.is_dir() else []


def test_the_scan_finds_the_portals_calls() -> None:
    # A broken pattern would find nothing and pass everything below (80 calls
    # on 2026-10-30).
    assert len(CALLS) > 50
    assert {c.method for c in CALLS} == {"GET", "POST", "PUT", "PATCH", "DELETE"}


def test_every_call_the_portal_makes_crosses_the_relay() -> None:
    routes = RouteTable(allow_dev_routes=True)
    missing = []
    for call in CALLS:
        if not call.literal and (call.file, call.written) in PASS_THROUGH:
            continue
        where = f"{call.file}:{call.line} {call.method}"
        if not call.literal and (call.file, call.written) not in HELPERS:
            missing.append(f"{where} {call.written!r} (not a literal)")
        elif routes.match(call.method, _path(call)) is None:
            missing.append(f"{where} {_path(call)}")
    assert not missing, "portal calls with no row in allowlist.PUBLIC_ROUTES:\n" + "\n".join(
        missing
    )


def test_every_helper_that_takes_a_path_is_scanned() -> None:
    # PASS_THROUGH lets a helper's body pass on `url`; that is only safe while
    # the helper's own callers are read. A helper copied from apiPost under a
    # new name would otherwise hide every call made through it.
    unknown = []
    for folder in HELPER_FILES:
        for path in sorted((PORTAL / folder).rglob("*.ts*")):
            if ".test." in path.name:
                continue
            for m in _TAKES_A_PATH.finditer(path.read_text(encoding="utf-8")):
                name = m["fn"] or m["const"]
                if name not in SCANNED_HELPERS:
                    unknown.append(f"{path.relative_to(PORTAL).as_posix()}: {name}")
    assert not unknown, "helpers taking a path that this test does not read:\n" + "\n".join(unknown)
    assert {"apiGet", "apiPost", "apiDownload", "useApiMutation"} <= _helpers_found()


def _helpers_found() -> set[str]:
    found: set[str] = set()
    for folder in HELPER_FILES:
        for path in (PORTAL / folder).rglob("*.ts*"):
            for m in _TAKES_A_PATH.finditer(path.read_text(encoding="utf-8")):
                found.add(m["fn"] or m["const"])
    return found


def test_every_named_exception_is_still_used() -> None:
    used = {(c.file, c.written) for c in CALLS if not c.literal}
    used |= {
        (c.file, expr)
        for c in CALLS
        if c.literal
        for expr in re.findall(r"\$\{([^}]*\)?)\}", c.written)
    }
    stale = (set(HELPERS) | PASS_THROUGH) - used
    assert not stale, f"named here but no longer in the portal: {sorted(stale)}"


def _operations() -> dict[str, set[str]]:
    paths = json.loads(OPENAPI.read_text(encoding="utf-8"))["paths"]
    return {re.sub(r"\{[^}]+\}", "{}", p): {m.upper() for m in ops} for p, ops in paths.items()}


@pytest.mark.parametrize(("method", "template"), PUBLIC_ROUTES)
def test_every_row_is_an_operation_the_api_has(method: str, template: str) -> None:
    operations = _operations()
    shape = re.sub(r"\{[^}]+\}", "{}", template)
    assert method in operations.get(shape, set()), f"{method} {template} is not in openapi.json"


@pytest.mark.parametrize(("method", "template"), DEV_ROUTES)
def test_a_dev_row_is_absent_from_the_document_or_right(method: str, template: str) -> None:
    # Development routes are mounted only in local and test, so the committed
    # document may leave them out; when it has one, the method must agree.
    operations = _operations()
    if template in operations:
        assert method in operations[template]
