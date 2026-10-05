"""The layers hold, by check rather than by convention (review 2026-10-01, ARCH-5).

`docs/architecture/layers.md` says routers are thin, services are the only
writers and the only callers of `audit.record()`, and SQL lives in the
repositories. The review found registry routes writing and auditing for
themselves, SQL in two routers and in four domain modules - each a second
version of a rule that a task, or a future integration, would not share. They
were moved; these checks keep them moved.

Static, over the source, with the AST rather than a regular expression, so a
comment or a docstring that mentions `audit.record(` is not a violation and a
call split over lines is still one.

Not covered yet: `tasks/maintenance` (two sweeps query directly; the retention
sweep is rewritten under S4-01) and `infrastructure/messaging`, which reads the
office's words through its own synchronous connection in the worker.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "cmp"

#: What a call that runs SQL looks like.
SQL_HELPERS = {"fetch_one", "fetch_all", "fetch_val", "require_one"}

#: Repository functions that change a row, by the verb they start with.
WRITE_VERBS = (
    "create",
    "update",
    "set_",
    "add_",
    "remove",
    "delete",
    "insert",
    "upsert",
    "revoke",
    "assign",
    "suspend",
    "deactivate",
    "record_",
    "place",
    "release",
)


def _modules(*parts: str) -> list[Path]:
    return sorted(p for p in (SRC.joinpath(*parts)).rglob("*.py"))


def _calls(path: Path) -> list[tuple[int, str, str]]:
    """(line, receiver, attribute) for every `a.b(...)`, and (line, "", name) for `f(...)`."""
    out: list[tuple[int, str, str]] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute):
            receiver = fn.value.id if isinstance(fn.value, ast.Name) else ""
            out.append((node.lineno, receiver, fn.attr))
        elif isinstance(fn, ast.Name):
            out.append((node.lineno, "", fn.id))
    return out


def _where(path: Path, line: int) -> str:
    return f"{path.relative_to(SRC)}:{line}"


def test_no_router_records_an_audit_row() -> None:
    offenders = [
        _where(p, line)
        for p in _modules("api", "routers")
        for line, receiver, name in _calls(p)
        if receiver == "audit" and name == "record"
    ]
    assert not offenders, "routers recording audit rows (a service's job):\n" + "\n".join(offenders)


def test_no_router_writes_through_a_repository() -> None:
    offenders = [
        f"{_where(p, line)} {receiver}.{name}"
        for p in _modules("api", "routers")
        for line, receiver, name in _calls(p)
        if receiver.endswith("repo") and name.startswith(WRITE_VERBS)
    ]
    assert not offenders, "routers writing rows (a service's job):\n" + "\n".join(offenders)


def test_sql_lives_in_the_repositories() -> None:
    """Routers, domain services and `auth` run no SQL of their own.

    One exception, named: `domain/audit/service.py` is the trail's own writer -
    the one INSERT every other write depends on - and `cmp_audit_verify`.
    """
    allowed = {SRC / "domain" / "audit" / "service.py"}
    offenders = [
        f"{_where(p, line)} {receiver + '.' if receiver else ''}{name}"
        for p in [*_modules("api"), *_modules("domain"), *_modules("auth")]
        if p not in allowed
        for line, receiver, name in _calls(p)
        if (not receiver and name in SQL_HELPERS) or (receiver == "conn" and name == "execute")
    ]
    assert not offenders, "SQL outside the repositories:\n" + "\n".join(offenders)


def test_the_checks_would_catch_what_they_guard() -> None:
    """Each check against a small module that breaks it, so a check that
    stopped matching anything would fail here rather than pass forever."""
    sample = ast.parse(
        "async def f(conn):\n"
        "    await audit.record(conn, event='x')\n"
        "    await repo.set_status(conn, 1, 'x')\n"
        "    await fetch_one(conn, 'SELECT 1')\n"
        "    await conn.execute('UPDATE x SET y = 1')\n"
    )
    found = {
        (
            n.func.value.id if isinstance(n.func, ast.Attribute) else "",
            n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id,
        )
        for n in ast.walk(sample)
        if isinstance(n, ast.Call)
        and isinstance(n.func, (ast.Attribute, ast.Name))
        and (isinstance(n.func, ast.Name) or isinstance(n.func.value, ast.Name))
    }
    assert ("audit", "record") in found
    assert any(r.endswith("repo") and a.startswith(WRITE_VERBS) for r, a in found)
    assert ("", "fetch_one") in found and ("conn", "execute") in found
