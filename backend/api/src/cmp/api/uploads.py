"""A file sent with a message, in and out (S3-08).

The breach ticket routes, the office's and the holder's, take a file the way
the rights thread does: checked against the evidence rules, stored through the
storage seam, kept with its hash and the name it was uploaded with. Kept here
rather than copied into each router; the rights router predates it and keeps
its own.
"""

from __future__ import annotations

from fastapi import Response, UploadFile

from cmp.core.security import file_hash
from cmp.infrastructure.storage.service import storage
from cmp.validation.files import EVIDENCE, check_upload


def safe_name(filename: str | None) -> str | None:
    """A file name fit for a header: the base name, no quotes, bounded."""
    if not filename:
        return None
    base = filename.replace("\\", "/").rsplit("/", 1)[-1].replace('"', "").strip()
    return base[:255] or None


async def stored(
    upload: UploadFile | None, *, subdir: str
) -> tuple[str | None, str | None, str | None]:
    """Store an attached file, if there is one: its reference, its hash, and
    the name it came with."""
    if upload is None:
        return None, None, None
    payload = await upload.read()
    check_upload(payload, upload.content_type, EVIDENCE)
    name = safe_name(upload.filename)
    return (
        storage().save(payload, subdir=subdir, suggested_name=name or "attachment"),
        file_hash(payload),
        name,
    )


def download(payload: bytes, filename: str, recorded: str) -> Response:
    """The file, with the hash recorded at upload and the hash of what was read,
    so whoever downloads it can tell the two apart."""
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name(filename) or "file"}"',
            "X-Recorded-SHA256": recorded,
            "X-Content-SHA256": file_hash(payload),
        },
    )
