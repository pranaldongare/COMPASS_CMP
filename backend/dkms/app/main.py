"""The DKMS service.

Separate from the platform API on purpose. It holds one secret and does one
thing with it, so it can be deployed, restarted, audited and reasoned about on
its own - and the platform API, which holds the database, does not also hold
the key that would make the database readable.

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    python3 -m app.main            # or: uvicorn app.main:app --port 8100
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.routes import router
from app.config import get_settings
from app.dkms.base import DkmsProvider
from app.dkms.local import LocalAesProvider
from app.engine import BulkEngine

log = structlog.get_logger("dkms")


def build_provider() -> DkmsProvider:
    """The local scheme, or the vendor SDK if this deployment names one."""
    settings = get_settings()
    if settings.provider == "sdk":
        from app.dkms.sdk import load

        return load(settings.sdk_module, settings.sdk_factory)
    return LocalAesProvider(
        settings.master_key_bytes,
        version=settings.key_version,
        previous=settings.previous_key_bytes,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.assert_shippable()
    provider = build_provider()
    app.state.engine = BulkEngine(
        provider, workers=settings.workers, chunk_size=settings.chunk_size
    )
    app.state.max_records = settings.max_records
    log.info(
        "dkms.ready",
        provider=provider.name,
        workers=settings.workers,
        chunk_size=settings.chunk_size,
        environment=settings.environment,
    )
    try:
        yield
    finally:
        app.state.engine.shutdown()
        log.info("dkms.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="COMPASS DKMS",
        version="1.0.0",
        summary="Bulk field encryption and decryption for personal data",
        description=(
            "Two operations over a batch of records and a mapping of field "
            "names to data types. The fields named are encrypted or decrypted; "
            "everything else passes through unchanged."
        ),
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("app.main:app", host=s.host, port=s.port, reload=s.environment == "local")
