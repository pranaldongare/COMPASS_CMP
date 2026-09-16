"""What a task broadcasts about itself.

Celery puts a repr of every argument into the `task-sent` and `task-received`
events, and anything watching those events renders it - Flower shows args and
kwargs on its task page, verbatim. The arguments here are one-time codes and
personal contacts: `send_login_code(uuid, contact, code)` is a live credential
and a mobile number, published to a stream that has none of the controls the
rest of the platform has, and kept for as long as the events are.

So `cmp.tasks.dispatch` overrides the repr. The worker still receives the real
arguments, because it has to run the task; what changes is what is said *about*
the message to everyone listening.

These tests exist because the redaction is invisible when it works. Nothing
fails, no page looks different, and the only way to notice it has been dropped
is to go and read a monitoring UI at the moment a sign-in code goes out.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.tasks.dispatch import _withheld, dispatch_optional, dispatch_required

#: The kind of thing these tasks are actually called with.
CODE = "482913"
CONTACT = "+919000000001"
EMAIL = "someone@example.org"


class FakeTask:
    """A task that records how it was queued instead of queueing."""

    def __init__(self, name: str = "cmp.notifications.send_login_code") -> None:
        self.name = name
        self.calls: list[dict[str, Any]] = []

    def apply_async(self, **options: Any) -> Any:
        self.calls.append(options)
        return type("Result", (), {"id": "fake-task-id"})()


class TestWhatIsWithheld:
    def test_no_argument_value_survives(self) -> None:
        shown = _withheld(("a-uuid", CONTACT, CODE), {"extra": EMAIL})
        rendered = " ".join(shown.values())
        for secret in (CODE, CONTACT, EMAIL, "a-uuid"):
            assert secret not in rendered

    def test_the_shape_does_survive(self) -> None:
        """Enough to see that a task was called with what it expects. A page
        that says nothing at all invites somebody to turn this off to debug."""
        shown = _withheld((1, 2, 3), {"a": 1})
        assert "3" in shown["argsrepr"]
        assert "1" in shown["kwargsrepr"]

    def test_no_arguments_is_not_a_special_case(self) -> None:
        shown = _withheld((), {})
        assert "0" in shown["argsrepr"] and "0" in shown["kwargsrepr"]


class TestEveryDispatchRedacts:
    @pytest.mark.parametrize("dispatch", [dispatch_required, dispatch_optional])
    def test_the_repr_is_overridden_on_the_way_out(self, dispatch: Any) -> None:
        """Both helpers, because they are separate call sites and a fix applied
        to one of them looks complete."""
        task = FakeTask()
        dispatch(task, "a-uuid", CONTACT, CODE)

        assert len(task.calls) == 1, "the task was not queued"
        options = task.calls[0]
        assert "argsrepr" in options and "kwargsrepr" in options
        assert CODE not in options["argsrepr"]
        assert CONTACT not in options["argsrepr"]

    @pytest.mark.parametrize("dispatch", [dispatch_required, dispatch_optional])
    def test_the_worker_still_gets_the_real_arguments(self, dispatch: Any) -> None:
        """The point that would be easy to get wrong in the other direction: a
        redaction that reached the message body would be a sign-in code the
        worker cannot send."""
        task = FakeTask()
        dispatch(task, "a-uuid", CONTACT, CODE)

        assert task.calls[0]["args"] == ("a-uuid", CONTACT, CODE)
