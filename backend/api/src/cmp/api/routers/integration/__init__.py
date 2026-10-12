"""Endpoints for other systems inside the organisation, not for people.

No session and no cookie: a service presents its own identity on every call.
Reachable on the internal network only - the console's and the portal's `/api`
proxies do not forward `/api/integration` (next.config.ts in each app).
"""

from cmp.api.routers.integration.databank import router as databank_router

__all__ = ["databank_router"]
