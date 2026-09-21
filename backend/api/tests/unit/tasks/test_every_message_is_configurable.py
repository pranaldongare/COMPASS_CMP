"""Nothing sends a message except through a junction the office can edit.

Reads the source. Three things must hold, and each failing names the file:

1. Only `cmp.infrastructure.messaging` touches a transport. A task or a
   service that built its own email would be a message the console cannot
   list, cannot reword, and nobody would know existed.
2. Every `deliver(...)` call names a `Message` member as its first argument,
   so the junction is static and the list in the console is complete by
   construction.
3. Every `Message` member is delivered somewhere. A junction with no sender
   is either dead or a message somebody forgot to wire, and the office would
   be editing words that never go out.
"""

from __future__ import annotations

import ast
import pathlib

import cmp
from cmp.core.messages import Message

SRC = pathlib.Path(cmp.__file__).parent
TRANSPORT_NAMES = {"build_email_transport", "build_sms_transport"}
ALLOWED_TRANSPORT_USERS = {
    SRC / "infrastructure" / "messaging" / "__init__.py",
    # Assembly: names the configured transports in the startup log, sends nothing.
    SRC / "bootstrap" / "container.py",
}


def _modules() -> list[tuple[pathlib.Path, ast.Module]]:
    out = []
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        out.append((path, ast.parse(path.read_text(encoding="utf-8"))))
    return out


def test_only_the_messaging_layer_touches_a_transport() -> None:
    offenders: list[str] = []
    for path, tree in _modules():
        if path in ALLOWED_TRANSPORT_USERS or path.parts[-3:-1] in (
            ("infrastructure", "email"),
            ("infrastructure", "sms"),
        ):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in TRANSPORT_NAMES:
                offenders.append(str(path.relative_to(SRC)))
                break
            if isinstance(node, ast.Attribute) and node.attr in TRANSPORT_NAMES:
                offenders.append(str(path.relative_to(SRC)))
                break
    assert not offenders, f"these build a transport directly, bypassing the catalogue: {offenders}"


def _deliver_calls() -> list[tuple[pathlib.Path, ast.Call]]:
    calls = []
    for path, tree in _modules():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "deliver"
            ):
                calls.append((path, node))
    return calls


def test_every_delivery_names_a_junction_statically() -> None:
    calls = _deliver_calls()
    assert calls, "no deliver() calls found - the scan is broken"
    bad = []
    for path, call in calls:
        first = call.args[0] if call.args else None
        ok = (
            isinstance(first, ast.Attribute)
            and isinstance(first.value, ast.Name)
            and first.value.id == "Message"
            and first.attr in Message.__members__
        )
        if not ok:
            bad.append(f"{path.relative_to(SRC)}:{call.lineno}")
    assert not bad, f"deliver() must be called with a Message member first: {bad}"


def test_every_junction_is_delivered_by_some_task() -> None:
    used = {
        call.args[0].attr  # type: ignore[union-attr]
        for _, call in _deliver_calls()
        if call.args and isinstance(call.args[0], ast.Attribute)
    }
    unused = sorted(set(Message.__members__) - used)
    assert not unused, f"junctions nothing sends (dead, or a task forgot to wire them): {unused}"
