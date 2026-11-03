"""The relay's parts stay apart: what runs on AWS, what runs inside, what both run.

The bridge and the collector are installed on different hosts, either side of a
boundary nothing crosses inward, each with `common` beside it and nothing else.
Here every part is installed at once, so a bridge module importing a collector
module, or the collector importing a library only the bridge's host has, would
pass every other test and fail only on the host. These read the source instead.
"""

from __future__ import annotations

import ast
import re
import sys
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

RELAY = Path(__file__).resolve().parents[2]

#: Each part, and the other parts its code and tests may import.
MAY_IMPORT: dict[str, frozenset[str]] = {
    "common": frozenset(),
    "bridge": frozenset({"common"}),
    "collector": frozenset({"common"}),
    "dev": frozenset({"common", "bridge", "collector"}),
}


def _modules(part: str) -> set[str]:
    return {path.stem for path in (RELAY / part / "src" / "cmp_relay").glob("*.py")}


def _owner() -> dict[str, str]:
    return {module: part for part in MAY_IMPORT for module in _modules(part)}


def _imports(path: Path) -> tuple[set[str], set[str]]:
    """The `cmp_relay` modules a file imports, and the other top-level names."""
    ours: set[str] = set()
    theirs: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            top, _, rest = node.module.partition(".")
            if top != "cmp_relay":
                theirs.add(top)
            elif rest:
                ours.add(rest.split(".")[0])
            else:
                ours.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top, _, rest = alias.name.partition(".")
                if top != "cmp_relay":
                    theirs.add(top)
                elif rest:
                    ours.add(rest.split(".")[0])
    return ours, theirs - set(sys.stdlib_module_names) - {"__future__"}


def _requirements(part: str) -> set[str]:
    path = RELAY / part / "requirements.txt"
    if not path.is_file():
        return set()
    names = set()
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(_normal(re.split(r"[=<>!~;\[\s]", line, maxsplit=1)[0]))
    return names


def _normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_every_module_is_in_exactly_one_part() -> None:
    seen: dict[str, str] = {}
    for part in MAY_IMPORT:
        for module in _modules(part):
            assert module not in seen, f"cmp_relay.{module} is in both {seen[module]} and {part}"
            seen[module] = part
    # A namespace package: an __init__.py in one part would hide the others'.
    assert not list(RELAY.glob("*/src/cmp_relay/__init__.py"))


@pytest.mark.parametrize("part", sorted(MAY_IMPORT))
def test_a_part_imports_only_itself_and_what_it_may(part: str) -> None:
    owner = _owner()
    allowed = MAY_IMPORT[part] | {part}
    files = [*(RELAY / part / "src").rglob("*.py"), *(RELAY / part / "tests").rglob("*.py")]
    assert files
    for path in files:
        for module in _imports(path)[0]:
            where = path.relative_to(RELAY)
            assert module in owner, f"{where} imports cmp_relay.{module}, which no part has"
            assert owner[module] in allowed, (
                f"{where} imports cmp_relay.{module}, which is {owner[module]}'s"
            )


@pytest.mark.parametrize("part", sorted(MAY_IMPORT))
def test_what_a_part_imports_is_installed_with_it(part: str) -> None:
    have = _requirements(part).union(*(_requirements(other) for other in MAY_IMPORT[part]))
    distributions = packages_distributions()
    for path in (RELAY / part / "src").rglob("*.py"):
        for name in _imports(path)[1]:
            provided_by = {_normal(d) for d in distributions.get(name, [name])}
            assert provided_by & have, (
                f"{path.relative_to(RELAY)} imports {name}, which is not in the "
                f"requirements of {part} or of what it is installed with"
            )


@pytest.mark.parametrize(
    ("part", "never"),
    [("bridge", {"httpx", "httpcore", "certifi"}), ("collector", {"starlette", "uvicorn"})],
)
def test_neither_side_carries_the_other_sides_libraries(part: str, never: set[str]) -> None:
    assert not (_requirements(part) | _requirements("common")) & never
