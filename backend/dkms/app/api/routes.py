"""The two endpoints, and the two that let you check on them."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dkms.types import DataType
from app.engine import BulkEngine, BulkFailed
from app.schemas import BulkRequest, BulkResponse

router = APIRouter()


def engine_of(request: Request) -> BulkEngine:
    return request.app.state.engine  # type: ignore[no-any-return]


Engine = Annotated[BulkEngine, Depends(engine_of)]


def _guard(body: BulkRequest, engine: BulkEngine, limit: int) -> None:
    if len(body.data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"{len(body.data)} records in one call; the limit is {limit}",
        )


@router.post(
    "/bulk_encrypt",
    response_model=BulkResponse,
    summary="Bulk encrypt data with parallel thread-pool processing",
)
async def encrypt_bulk(body: BulkRequest, request: Request, engine: Engine) -> BulkResponse:
    """Encrypt the fields named in `key`; everything else passes through.

    `method` chooses the form: `string` returns the `SE::` prefix, `bytes`
    returns base64. A value that is already ciphertext is left alone unless
    `skip_encrypted` is false, because encrypting twice is a data loss that
    decrypting once does not undo.
    """
    _guard(body, engine, request.app.state.max_records)
    try:
        return await engine.run(body, encrypting=True)
    except BulkFailed as failed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "encryption failed",
                "errors": [e.model_dump(mode="json") for e in failed.errors],
            },
        ) from failed


@router.post(
    "/bulk_decrypt",
    response_model=BulkResponse,
    summary="Bulk decrypt data with parallel thread-pool processing",
)
async def decrypt_bulk(body: BulkRequest, request: Request, engine: Engine) -> BulkResponse:
    """The inverse, with the same mapping and the same `method`.

    The data type in `key` has to be the one the value was written under. It is
    bound into the ciphertext, so asking for the wrong one is refused rather
    than answered with rubbish.
    """
    _guard(body, engine, request.app.state.max_records)
    try:
        return await engine.run(body, encrypting=False)
    except BulkFailed as failed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "decryption failed",
                "errors": [e.model_dump(mode="json") for e in failed.errors],
            },
        ) from failed


# The paths this service first answered on. Kept, hidden from the reference,
# so anything written against them keeps working; `/bulk_encrypt` and
# `/bulk_decrypt` are the names.
router.add_api_route(
    "/encrypt/bulk",
    encrypt_bulk,
    methods=["POST"],
    response_model=BulkResponse,
    include_in_schema=False,
)
router.add_api_route(
    "/decrypt/bulk",
    decrypt_bulk,
    methods=["POST"],
    response_model=BulkResponse,
    include_in_schema=False,
)


@router.get("/types", summary="The data types this service accepts")
async def data_types() -> dict[str, list[str]]:
    """What may appear on the right-hand side of `key`."""
    return {"types": [t.value for t in DataType]}


@router.get("/health", summary="Is it up, and what is it running on")
async def health(request: Request, engine: Engine) -> dict[str, object]:
    return {
        "status": "ok",
        "provider": engine.provider_name,
        "workers": engine.workers,
        "max_records": request.app.state.max_records,
    }
