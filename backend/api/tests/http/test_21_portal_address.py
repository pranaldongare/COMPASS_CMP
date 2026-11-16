"""The portal's address over HTTP (0072).

The administrator alone reads and sets it. Everybody signed in is told the
address in use by `GET /auth/me`, and the public link for reporting a breach
starts with it at once. The address is cleared again at the end: this suite
commits, and the next run starts from "the configured one".
"""

from __future__ import annotations

import httpx

from cmp.core import portal_address as held
from cmp.core.config import settings
from tests.http.conftest import SessionFactory
from tests.http.contract import call

ADDRESS = "/portal-address"
SET_TO = "http://10.20.30.40:3001"


async def test_the_administrator_sets_it_and_links_follow(
    http: httpx.AsyncClient, session_for: SessionFactory
) -> None:
    admin = await session_for("admin")
    dpo = await session_for("dpo")
    dco = await session_for("dco")
    configured = settings.public_base_url.rstrip("/")
    held.forget()
    try:
        for who in (dpo, dco):
            await call(http, "GET", ADDRESS, session=who, expect=403)
            await call(http, "PUT", ADDRESS, session=who, expect=403, json={"portal_url": SET_TO})

        before = (await call(http, "GET", ADDRESS, session=admin)).json()
        assert before["portal_url"] is None and before["in_use"] == configured

        refused = await call(
            http, "PUT", ADDRESS, session=admin, expect=422, json={"portal_url": "10.20.30.40"}
        )
        assert refused.json()["error"]["field"] == "portal_url"

        saved = (
            await call(http, "PUT", ADDRESS, session=admin, json={"portal_url": SET_TO + "/"})
        ).json()
        assert saved["portal_url"] == saved["in_use"] == SET_TO
        assert saved["configured_url"] == configured

        # Whoever copies a consent link is told where it starts...
        me = (await call(http, "GET", "/auth/me", session=dco)).json()
        assert me["portal_url"] == SET_TO
        # ...and the public reporting link starts there too.
        breach = (await call(http, "GET", "/breach-settings", session=dpo)).json()
        assert breach["report_link"] == f"{SET_TO}/report-incident"
    finally:
        cleared = (
            await call(http, "PUT", ADDRESS, session=admin, json={"portal_url": None})
        ).json()
        assert cleared["portal_url"] is None and cleared["in_use"] == configured
        held.forget()
