"""Side effects that must wait for the commit.

A service that queues a notification while its transaction is still open is
making a promise it has not kept yet: the worker can pick the message up
before the row it describes is visible, and the message goes out even if the
commit then fails. The fix is not to move the queueing into the router - that
scatters it - but to let the service say "after this commits, do that", and
have the unit of work honour it.

`unit_of_work()` is entered by `cmp.db.pool.transaction()` around the database
transaction. Anything registered with `defer()` inside it runs once the
transaction has committed, in order, and is dropped if it rolled back. Outside
any unit of work `defer()` declines, and the caller does the work immediately -
which is what a script or a test that opened its own connection expects.

This is the cheap half of a transactional outbox: it closes "acted before
commit" and "sent despite rollback". It does not survive a broker outage at
the moment of flushing; those failures are logged at error, which is the same
guarantee `dispatch_optional` always gave. A durable outbox table is the next
step if that gap matters, and is recorded as such in the decisions.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar

from cmp.core.logging import get_logger

log = get_logger("cmp.after_commit")

Hook = Callable[[], object]

_pending: ContextVar[list[Hook] | None] = ContextVar("cmp_after_commit", default=None)


@contextmanager
def unit_of_work() -> Generator[None]:
    """Collect deferred work for the duration of a transaction.

    Nested units share the outermost one: a service that opens a transaction
    inside another does not flush its hooks until the outer commit, because
    until then nothing it wrote is committed either.
    """
    if _pending.get() is not None:
        yield
        return

    token = _pending.set([])
    try:
        yield
    except BaseException:
        dropped = _pending.get() or []
        _pending.reset(token)
        if dropped:
            log.info("after_commit.dropped", hooks=len(dropped))
        raise
    else:
        hooks = _pending.get() or []
        _pending.reset(token)
        for hook in hooks:
            try:
                hook()
            except Exception as exc:  # one failed side effect must not stop the rest
                log.error("after_commit.hook_failed", error=str(exc), exc_info=True)


def defer(hook: Hook) -> bool:
    """Register `hook` to run after the enclosing transaction commits.

    Returns False when there is no enclosing unit of work, in which case the
    caller should run the hook itself.
    """
    pending = _pending.get()
    if pending is None:
        return False
    pending.append(hook)
    return True


def in_unit_of_work() -> bool:
    return _pending.get() is not None
