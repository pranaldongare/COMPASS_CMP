"""Async connection pool and the unit of work.

Repositories never open a connection. They receive one, already inside the
transaction the service opened. That is what makes "publish a notice" one atomic
operation instead of four writes that can half-succeed.

Session-level `statement_timeout` and `lock_timeout` are set on every checkout.
A query with no timeout is a query that can hold a lock until the pool starves.

The office (ADR 0032). Every connection `connection()` and `transaction()` hand
out first says which office it reads - `app.office`, the request context's
office code or `all` - and has it reset before it goes back, so the setting
never reaches the next request that draws the connection. PostgreSQL's
row-level security does the rest (`docs/architecture/offices-and-tenancy.md`).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from cmp.core import after_commit
from cmp.core.config import settings
from cmp.core.context import current_context
from cmp.core.errors import CmpError, ServiceUnavailable
from cmp.core.logging import get_logger

log = get_logger("cmp.db")

_pool: AsyncConnectionPool | None = None

_SESSION_SETUP: Final = (
    f"SET statement_timeout = {settings.db_statement_timeout_ms}; "
    f"SET lock_timeout = {settings.db_lock_timeout_ms}; "
    "SET idle_in_transaction_session_timeout = 30000; "
    "SET TIME ZONE 'UTC';"
)


#: What `app.office` holds for a caller who works across both offices.
ALL_OFFICES: Final = "all"


async def _configure(conn: psycopg.AsyncConnection[Any]) -> None:
    conn.row_factory = dict_row
    await conn.execute(_SESSION_SETUP)
    await conn.commit()


async def _forget_office(conn: psycopg.AsyncConnection[Any]) -> None:
    """On the way back to the pool: the office goes with the request that set it.

    Here, on the request's own task, rather than as the pool's `reset`
    callback: `psycopg_pool` runs that callback on a worker task of the event
    loop that opened the pool, and a connection whose reset never runs never
    returns. The next checkout sets the office again in any case; this is so
    that a connection drawn some other way - a script, a test - finds none.

    A connection that cannot take the statement is a broken one, which the
    pool discards rather than hands out; the error of the request that broke it
    is the one worth raising.
    """
    if conn.broken or conn.closed:
        return
    try:
        await conn.set_autocommit(True)
        await conn.execute("RESET app.office")
    except psycopg.Error as exc:
        log.warning("db.office_not_reset", error=str(exc))


async def _apply_office(conn: psycopg.AsyncConnection[Any]) -> None:
    """Say which office this connection reads, before anything else runs on it.

    Session-level (`false`), because `connection()` is autocommit and a
    transaction-local setting would end with the statement that set it.
    """
    office = current_context().office or ALL_OFFICES
    await conn.execute("SELECT set_config('app.office', %s, false)", (office,))


async def _probe() -> None:
    """One direct connection before the pool opens.

    The pool retries in the background and reports `PoolTimeout`, which names the
    symptom and hides the cause - a wrong password, an unreachable host and an
    incompatible event loop all look identical. A single probe surfaces the real
    exception, once, at startup.
    """
    try:
        conn = await psycopg.AsyncConnection.connect(settings.dsn, connect_timeout=5)
        await conn.close()
    except psycopg.InterfaceError as exc:
        if "ProactorEventLoop" in str(exc):
            raise RuntimeError(
                "psycopg cannot use Windows' ProactorEventLoop. Start the API with "
                "`python -m cmp` (which sets WindowsSelectorEventLoopPolicy) rather "
                "than invoking uvicorn directly."
            ) from exc
        raise
    except psycopg.OperationalError as exc:
        raise ServiceUnavailable(
            f"Cannot reach PostgreSQL at {settings.postgres_host}:{settings.postgres_port} "
            f"as {settings.postgres_user}/{settings.postgres_db}: {exc}"
        ) from exc


async def open_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    await _probe()
    _pool = AsyncConnectionPool(
        conninfo=settings.dsn,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        timeout=settings.db_pool_timeout_s,
        max_lifetime=30 * 60,
        max_idle=5 * 60,
        configure=_configure,
        open=False,
        name="cmp-pg",
    )
    await _pool.open(wait=True, timeout=settings.db_pool_timeout_s)
    log.info("db.pool.open", min_size=_pool.min_size, max_size=_pool.max_size)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        log.info("db.pool.closed")
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:  # pragma: no cover - programming error, not a runtime path
        raise RuntimeError("Connection pool is not open. Call open_pool() in the lifespan.")
    return _pool


@asynccontextmanager
async def connection() -> AsyncIterator[psycopg.AsyncConnection[Any]]:
    """A read connection. Autocommit - no transaction is held open for a SELECT."""
    try:
        async with get_pool().connection() as conn:
            await conn.set_autocommit(True)
            await _apply_office(conn)
            try:
                yield conn
            finally:
                await _forget_office(conn)
    except psycopg.OperationalError as exc:
        log.error("db.unavailable", error=str(exc))
        raise ServiceUnavailable("Database is unavailable") from exc


@asynccontextmanager
async def transaction() -> AsyncIterator[psycopg.AsyncConnection[Any]]:
    """A write unit of work. Commits on clean exit, rolls back on any exception.

    Keep the body short: a transaction that awaits an HTTP call holds a row lock
    for the duration of somebody else's outage.

    An error marked `with_evidence` is the one exception that commits: the
    transaction ends cleanly, and the error is raised once it has.
    """
    kept: CmpError | None = None
    try:
        async with get_pool().connection() as conn:
            await conn.set_autocommit(True)
            await _apply_office(conn)
            await conn.set_autocommit(False)
            try:
                # Side effects a service defers run once the transaction below
                # has committed, and are dropped if it rolled back.
                with after_commit.unit_of_work():
                    async with conn.transaction():
                        try:
                            yield conn
                        except CmpError as exc:
                            if not exc.keeps_evidence:
                                raise
                            kept = exc
            finally:
                await _forget_office(conn)
    except psycopg.OperationalError as exc:
        log.error("db.unavailable", error=str(exc))
        raise ServiceUnavailable("Database is unavailable") from exc
    if kept is not None:
        raise kept


async def healthcheck() -> bool:
    """Readiness: can we reach the database at all?"""
    try:
        async with connection() as conn:
            cur = await conn.execute("SELECT 1 AS ok")
            row = await cur.fetchone()
            return bool(row and row["ok"] == 1)
    except Exception:
        return False


async def schema_version() -> str | None:
    """Readiness also asks whether migrations are current."""
    try:
        async with connection() as conn:
            cur = await conn.execute("SELECT version_num FROM alembic_version LIMIT 1")
            row = await cur.fetchone()
            return str(row["version_num"]) if row else None
    except Exception:
        return None


async def policies_bind() -> bool:
    """Whether the database user is one row-level security applies to.

    No policy binds a superuser or a role with BYPASSRLS, however the tables
    are set: the wall between the offices (ADR 0032) would stand in the schema
    and stop nothing.
    """
    async with connection() as conn:
        cur = await conn.execute(
            "SELECT rolsuper OR rolbypassrls AS bypasses FROM pg_roles WHERE rolname = current_user"
        )
        row = await cur.fetchone()
        return not (row and row["bypasses"])


async def assert_policies_bind() -> None:
    """Refuse to serve, outside local and test, as a user the policies cannot bind.

    Locally the database container's own superuser is the user, and the
    enforcement tests prove the wall under a role of their own instead.
    """
    if settings.environment in ("local", "test"):
        return
    if not await policies_bind():
        raise RuntimeError(
            f"The database user {settings.postgres_user!r} is a superuser or holds BYPASSRLS, "
            "so the office policies would not apply (ADR 0032). Run the API as a role "
            "without either."
        )
