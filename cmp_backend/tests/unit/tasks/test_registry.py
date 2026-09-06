"""Every task the code defines is one the worker will run.

The Celery app discovers tasks by importing the four task packages, and each
package imports its modules by hand. A module left out of that list is a task
the API can queue by name and the worker answers with "unregistered task" - the
message is dropped, the error is in a worker log nobody is watching, and the
request that queued it already returned 200. That is how a nomination's
acceptance link went nowhere.

So this reads the source: every `@shared_task(name=...)` under `cmp.tasks` has
to be in the app's registry after the packages are imported.
"""

from __future__ import annotations

import ast
import pathlib

import cmp.tasks
from cmp.tasks.app import celery_app

TASKS = pathlib.Path(cmp.tasks.__file__).parent


def _declared_names() -> dict[str, str]:
    """`name=` of every shared_task decorator, keyed by task name -> file."""
    found: dict[str, str] = {}
    for path in sorted(TASKS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                target = deco.func
                is_shared = (isinstance(target, ast.Name) and target.id == "shared_task") or (
                    isinstance(target, ast.Attribute) and target.attr == "shared_task"
                )
                if not is_shared:
                    continue
                for kw in deco.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        found[str(kw.value.value)] = str(path.relative_to(TASKS))
    return found


def test_every_declared_task_is_registered_with_the_app() -> None:
    declared = _declared_names()
    assert declared, "no @shared_task declarations found - the scan is broken"
    missing = {name: file for name, file in declared.items() if name not in celery_app.tasks}
    assert not missing, (
        "tasks the worker would reject as unregistered (import the module in its "
        f"package __init__): {missing}"
    )


def test_every_exactly_routed_task_exists() -> None:
    """A route naming a task that does not exist is a typo nobody will see.

    Wildcard routes are left alone: `cmp.exports.*` reserves a queue for a
    family that has no members yet, and that is a plan rather than a mistake.
    """
    for pattern in celery_app.conf.task_routes:
        if not pattern.endswith("*"):
            assert pattern in celery_app.tasks, pattern


def test_every_scheduled_task_exists() -> None:
    for entry in celery_app.conf.beat_schedule.values():
        assert entry["task"] in celery_app.tasks, entry["task"]
