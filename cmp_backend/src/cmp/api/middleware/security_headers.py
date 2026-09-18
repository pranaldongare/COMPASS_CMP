"""Response headers that constrain what a browser will do with our output.

Applied on the way out, to everything. A header set on some responses and not
others is a header an attacker will find the gap in.

The CSP is the one worth reading. This API serves JSON to a separate origin, so
it needs no script, style or image sources at all — `default-src 'none'` is
both the tightest possible policy and, here, the correct one.

The interactive docs are the exception, and for a long time that was a sentence
in this docstring rather than anything the code did: `/docs` is a *document*,
which loads Swagger UI from a CDN and runs an inline script to start it, and
`default-src 'none'` blocked every part of that. The page rendered empty with
four violations in the console, on every host including localhost. So the
exception is now real, and narrow — those paths only, the sources that page
actually needs, and nothing else. The docs do not exist in production at all
(`docs_url=None`), so this widens nothing there.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Final

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from cmp.core.config import settings

Next = Callable[[Request], Awaitable[Response]]


#: The interactive documentation, which is served only outside production.
#: `/openapi.json` is not here: it is JSON, and the strict policy suits it.
_DOCS_PATHS: Final = ("/docs", "/redoc")

#: What the Swagger and ReDoc pages actually load. `'unsafe-inline'` covers the
#: bootstrap script FastAPI writes into the page; its hash changes with the
#: title and the OpenAPI URL, so pinning one would break on the next rename and
#: leave somebody with the same empty page and no clue why.
_DOCS_CSP: Final = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers that cost nothing and close whole classes of attack.

    The API serves JSON, not documents, so the CSP is maximally restrictive: it
    is here to neuter a response that somehow renders, not to permit anything.
    """

    async def dispatch(self, request: Request, call_next: Next) -> Response:
        response = await call_next(request)
        headers = response.headers

        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        is_docs = request.url.path.rstrip("/") in _DOCS_PATHS
        headers.setdefault(
            "Content-Security-Policy",
            _DOCS_CSP
            if is_docs
            else "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        # An authenticated response is never a cacheable one. A shared cache that
        # keeps one user's project list and serves it to the next is a data
        # breach with a 200 status code.
        if request.url.path.startswith(("/auth", "/me", "/c/")) or "cookie" in request.headers:
            headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate, private")
            headers.setdefault("Pragma", "no-cache")

        if settings.is_production:
            headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload"
            )
        return response
