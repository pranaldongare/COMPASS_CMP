"""Create the first administrator.

The bootstrap problem: provisioning accounts requires an admin, and a fresh
deployment has none. This is the one way to make the first one, and it is
deliberately a script rather than an endpoint — an endpoint that creates
administrators is an endpoint somebody will eventually reach.

    uv run python scripts/create_admin.py --email you@org.example --name "Your Name"

The password is read from the `CMP_ADMIN_PASSWORD` environment variable, or
prompted for. It is never a command-line argument: arguments appear in shell
history, in `ps` output, and in a container's process list.

Refuses to create a second administrator. Once one exists, the rest are
provisioned through the API, where the act is audited and attributable — which
is the point.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

sys.path.insert(0, "src")

MIN_PASSWORD_LENGTH = 12


async def create(email: str, full_name: str, password: str) -> int:
    from cmp.core.security import hash_password
    from cmp.db.pool import close_pool, open_pool, transaction
    from cmp.db.repositories import users as user_repo
    from cmp.domain.audit import service as audit

    await open_pool()
    try:
        async with transaction() as conn:
            cur = await conn.execute("SELECT count(*) AS n FROM auth_user WHERE role = 'admin'")
            if (await cur.fetchone())["n"] > 0:
                sys.stderr.write(
                    "An administrator already exists.\n\n"
                    "Provision further accounts through the API, where the act is "
                    "audited and attributable to whoever performed it. That is the "
                    "reason this script refuses.\n"
                )
                return 1

            # Through the repository: the email is sealed and indexed on the
            # way in, as every account's is (0028). Plain SQL here wrote it in
            # the clear, which the database has refused since.
            if await user_repo.by_email(conn, email) is not None:
                sys.stderr.write(f"An account already exists for {email}.\n")
                return 1
            row = await user_repo.create(
                conn,
                full_name=full_name,
                email=email,
                role="admin",
                username=email.split("@")[0],
                person_type="employee",
                status="active",
                password_hash=hash_password(password),
            )

            # Audited like any other provisioning, with a null actor - nobody was
            # signed in, and recording a fictional actor would be worse than
            # recording none. The detail says how it happened. Through the
            # audit service, so the row joins the hash chain.
            await audit.record(
                conn,
                event=audit.Event.USER_CREATED,
                entity_type="auth_user",
                entity_id=int(row["id"]),
                subject_user_id=int(row["id"]),
                actor_user_id=None,
                detail={"role": "admin", "via": "scripts/create_admin.py", "bootstrap": True},
            )

        sys.stdout.write(f"Administrator created: {email}  ({row['uuid']})\n")
        return 0
    finally:
        await close_pool()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the first administrator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="full name, as it should appear")
    args = parser.parse_args()

    password = os.environ.get("CMP_ADMIN_PASSWORD") or getpass.getpass(
        f"Password for {args.email} (min {MIN_PASSWORD_LENGTH} chars): "
    )

    if len(password) < MIN_PASSWORD_LENGTH:
        sys.stderr.write(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.\n"
            "Length beats composition rules — a passphrase you can remember beats "
            "a short one you write down.\n"
        )
        return 1

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    return asyncio.run(create(args.email, args.name, password))


if __name__ == "__main__":
    raise SystemExit(main())
