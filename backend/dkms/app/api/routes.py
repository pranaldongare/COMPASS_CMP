"""The five endpoints, and the two that let you check on them.

Encrypt, decrypt and hash act on batches of records. The two search
endpoints act on one term and return what to look for: this service holds
keys, not rows, so it can say what a query needs and cannot run it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dkms.searchable import MIN_TERM
from app.dkms.types import DataType
from app.engine import AutoDecryptFailed, AutoDecryptUnsupported, BulkEngine, BulkFailed
from app.schemas import (
    AutoDecryptRequest,
    AutoDecryptResponse,
    BulkRequest,
    BulkResponse,
    HashRequest,
    HashResponse,
    NgramSearchRequest,
    NgramSearchResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


def engine_of(request: Request) -> BulkEngine:
    return request.app.state.engine  # type: ignore[no-any-return]


Engine = Annotated[BulkEngine, Depends(engine_of)]


def _guard(body: BulkRequest | HashRequest, engine: BulkEngine, limit: int) -> None:
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


@router.post(
    "/auto_decrypt",
    response_model=AutoDecryptResponse,
    summary="Decrypt values without naming their types",
)
async def auto_decrypt(
    body: AutoDecryptRequest, request: Request, engine: Engine
) -> AutoDecryptResponse:
    """Open each value under the type its own envelope names.

    For a caller that holds ciphertext and not the column it came from - the
    address a message goes to, a name joined from another table. The deployed
    key service answers on the same path in the same shape; this one does so
    that the platform can be run against either.
    """
    if len(body.payload) > request.app.state.max_records:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"{len(body.payload)} values in one call; "
                f"the limit is {request.app.state.max_records}"
            ),
        )
    try:
        return AutoDecryptResponse(data=engine.auto_decrypt(body.payload))
    except AutoDecryptUnsupported as unsupported:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"the {unsupported} provider cannot read a value's type off its envelope",
        ) from unsupported
    except AutoDecryptFailed as failed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "decryption failed", "keys": failed.keys},
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


@router.post(
    "/bulk_hash",
    response_model=HashResponse,
    summary="Bulk hash data for exact and substring lookup",
)
async def hash_bulk(body: HashRequest, request: Request, engine: Engine) -> HashResponse:
    """Replace the fields named in `key` with their hash.

    What a caller stores beside the ciphertext so that a sealed column can
    still be looked up. The hash is deterministic and keyed: equal values
    give equal hashes, and nobody without the key can go the other way.

    `with_ngrams` adds `<field>_ngrams`, the hashed character runs that make
    substring search possible. Ask for those only where somebody genuinely
    searches by part of a value: a set of runs leaks letter statistics that a
    single hash does not.

    Usually not needed on its own - `/bulk_encrypt` with `with_hash` returns
    the ciphertext and the hash together, which is the one moment both forms
    exist.
    """
    _guard(body, engine, request.app.state.max_records)
    return engine.hash(body)


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="What to look for: exact match on a sealed column",
)
async def search(body: SearchRequest, engine: Engine) -> SearchResponse:
    """The hash of one term, for `WHERE <field>_hash = …`.

    The whole value, as the person would give it: a complete address, a
    complete number. Half an address hashes to something no row holds -
    that is what `/search_ngram` is for.
    """
    normalised, digest = engine.search(body.type, body.term)
    return SearchResponse(
        term_normalised=normalised,
        hash=digest,
        sql="<field>_hash = :hash",
    )


@router.post(
    "/search_ngram",
    response_model=NgramSearchResponse,
    summary="What to look for: substring match on a sealed column",
)
async def search_ngram(body: NgramSearchRequest, engine: Engine) -> NgramSearchResponse:
    """The runs a row must contain for the term to be somewhere inside it.

    All of them, which in SQL is `<field>_ngrams @> :ngrams` against a text
    array with a GIN index on it. The result is candidates rather than an
    answer: a row holding every run of "ana" and "nan" might be "banana" or
    "ananas", so a caller that needs certainty opens the candidates and
    checks. For a staff search box, candidates are what is wanted.

    A term shorter than the run length is refused rather than answered with
    an empty list, which would read as "nothing matched".
    """
    if len(body.term.strip()) < MIN_TERM:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"a substring search needs at least {MIN_TERM} characters",
        )
    normalised, ngrams = engine.search_ngram(body.type, body.term, body.ngram_size)
    return NgramSearchResponse(
        term_normalised=normalised,
        ngrams=ngrams,
        ngram_size=body.ngram_size,
        sql="<field>_ngrams @> :ngrams",
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
