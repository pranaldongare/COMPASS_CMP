"""Upload validation.

Two upload paths exist — an approval proof and an import manifest — and both are
input we trust least: one arrives from a researcher's laptop, the other from a
third-party capture tool.

Checks run in this order, and the order is the point: refuse on declared size
before reading, refuse on actual size before hashing, refuse on type before
parsing. Each step is cheaper than the one it protects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from cmp.core.errors import BadRequest, ValidationFailed


@dataclass(frozen=True, slots=True)
class UploadRules:
    """What one upload slot accepts."""

    field: str
    max_bytes: int
    allowed_mime: tuple[str, ...]
    #: Extensions kept on the stored file. Anything else becomes `.bin`, so a
    #: `.php` or `.exe` cannot be written to disk under its own name whatever
    #: the client called it.
    allowed_suffixes: tuple[str, ...]


PROOF = UploadRules(
    field="proof",
    max_bytes=25 * 1024 * 1024,
    allowed_mime=("application/pdf", "image/png", "image/jpeg"),
    allowed_suffixes=(".pdf", ".png", ".jpg", ".jpeg"),
)

MANIFEST = UploadRules(
    field="manifest",
    max_bytes=25 * 1024 * 1024,
    allowed_mime=("text/csv", "application/csv", "text/plain"),
    allowed_suffixes=(".csv", ".txt"),
)

#: Evidence attached to a rights request: a holder's confirmation of what was
#: removed, or a nominee's evidence of death or incapacity. Documents and
#: images, because that is what a lab or a hospital produces.
EVIDENCE = UploadRules(
    field="evidence",
    max_bytes=25 * 1024 * 1024,
    allowed_mime=(
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/csv",
        "text/plain",
    ),
    allowed_suffixes=(".pdf", ".png", ".jpg", ".jpeg", ".csv", ".txt"),
)


def check_upload(payload: bytes, content_type: str | None, rules: UploadRules) -> None:
    """Refuse an upload that breaks the rules, naming the field that failed.

    Raises rather than returning a verdict: there is no caller that wants to
    continue with a file it has been told is unacceptable, and a boolean return
    is one forgotten `if` away from writing it anyway.
    """
    if not payload:
        raise ValidationFailed(f"The {rules.field} is empty", field=rules.field)

    if len(payload) > rules.max_bytes:
        raise BadRequest(
            f"{rules.field.capitalize()} exceeds {rules.max_bytes // (1024 * 1024)} MB",
            code="payload_too_large",
            field=rules.field,
        )

    if content_type not in rules.allowed_mime:
        raise ValidationFailed(
            f"{rules.field.capitalize()} must be one of: {', '.join(rules.allowed_mime)}",
            field=rules.field,
        )


#: What a file begins with, and what to call it when it arrives where it should
#: not have. Only the formats people actually reach for instead of a .docx are
#: listed. The commonest by a distance is a .doc: Word calls that a Word document
#: too, so somebody uploading one has not been careless, and telling them "that
#: is not a .docx" reads as the platform being wrong rather than the file.
_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"%PDF", "a PDF"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "a .doc, the format Word used before 2007"),
    (b"{\\rtf", "an RTF document"),
    (b"\x89PNG\r\n\x1a\n", "a PNG image"),
    (b"\xff\xd8\xff", "a JPEG image"),
    (b"II*\x00", "a TIFF image"),
    (b"MM\x00*", "a TIFF image"),
    (b"%!PS", "a PostScript file"),
    (b"\x1f\x8b", "a gzip archive"),
    (b"<?xml", "an XML file"),
)


def describe_format(payload: bytes) -> str | None:
    """What this file appears to be, in words, or None when it is not a guess
    worth making.

    Exists to make a refusal legible, and nothing is decided by it: whoever
    calls this has already decided to refuse. A wrong guess therefore costs a
    slightly misleading sentence, never a file accepted or rejected wrongly.
    """
    for signature, name in _SIGNATURES:
        if payload.startswith(signature):
            return name
    return None


def safe_suffix(filename: str | None, rules: UploadRules) -> str:
    """The extension we are willing to store this file under.

    The client's filename is a suggestion, not an instruction. Anything outside
    the allow-list becomes `.bin` — the file is still stored, still hashed and
    still downloadable, it simply cannot claim to be something executable.
    """
    if not filename or "." not in filename:
        return ".bin"
    suffix = "." + filename.rsplit(".", 1)[-1].lower()
    return suffix if suffix in rules.allowed_suffixes else ".bin"
