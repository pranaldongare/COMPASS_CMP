"""Installing the middleware stack.

Two groups, registered in this order: Starlette's own (host allow-listing,
CORS, compression), then ours - `cmp.api.middleware.install` registers the four
that need application knowledge: correlation id, security headers, body limit,
access log.

Starlette runs middleware in reverse registration order, so a request enters
ours first and Starlette's after: RequestContext, SecurityHeaders, BodyLimit,
AccessLog, then GZip, CORS, TrustedHost. A request for a host we do not serve
is therefore given a request id and an access-log line before it is refused -
the opposite of what this module once said it did. Harmless (nothing is
allocated beyond the id), but noted in docs/backend/06-known-gaps.md.

CORS carries credentials because the session cookie has to travel, and exposes
the handful of headers a browser client legitimately reads — without
`expose_headers` a fetch() cannot see `X-Request-ID`, which is the string a user
would otherwise be quoting in a support ticket.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cmp.api import middleware as api_middleware
from cmp.core.config import settings
from cmp.core.constants import (
    CONTENT_HASH_HEADER,
    EXPORT_GENERATED_HEADER,
    RECORDED_HASH_HEADER,
    REQUEST_ID_HEADER,
    RESPONSE_TIME_HEADER,
)
from cmp.infrastructure import devcodes


def install(app: FastAPI) -> None:
    if settings.trusted_hosts and "*" not in settings.trusted_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,  # the session cookie must travel
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            settings.csrf_header_name,
            REQUEST_ID_HEADER,
            # Development only: which tab a one-time code is shown in.
            *([devcodes.CLIENT_HEADER] if devcodes.enabled() else []),
        ],
        expose_headers=[
            REQUEST_ID_HEADER,
            RESPONSE_TIME_HEADER,
            "Retry-After",
            "Content-Disposition",
            EXPORT_GENERATED_HEADER,
            RECORDED_HASH_HEADER,
            CONTENT_HASH_HEADER,
        ],
        max_age=600,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    api_middleware.install(app)
