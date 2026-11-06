"""A file's name on the way out (S3-08, 2026-11-06).

A header carries Latin-1 at most. Proof is uploaded under whatever name Word or
Outlook gave it, so a name with an en dash, or one in Hindi, has to reach the
person who downloads it, and not fail the download of a file already stored.
"""

from __future__ import annotations

from urllib.parse import unquote

import pytest

from cmp.api import uploads


@pytest.mark.parametrize("name", ["Approval \u2013 final.pdf", "मंज़ूरी.pdf", "plain.pdf"])
@pytest.mark.parametrize("response", [uploads.download, uploads.generated])
def test_a_name_in_any_language_can_be_sent(name: str, response: object) -> None:
    sent = (
        uploads.download(b"x", name, "h")
        if response is uploads.download
        else uploads.generated(b"x", name, "application/pdf")
    )
    header = sent.headers["content-disposition"]
    plain, _, encoded = header.partition("; filename*=UTF-8''")
    assert plain.startswith('attachment; filename="') and plain.isascii()
    assert plain.endswith('.pdf"'), "the kind of file survives in the plain name"
    assert unquote(encoded) == name


def test_a_plain_name_is_kept_as_it_is_for_an_older_reader() -> None:
    header = uploads.download(b"x", "proof.pdf", "h").headers["content-disposition"]
    assert header.startswith('attachment; filename="proof.pdf"; ')


def test_control_characters_do_not_reach_a_header() -> None:
    assert uploads.safe_name("a\r\nb\x00\x7f.pdf") == "ab.pdf"
    assert uploads.safe_name("\r\n") is None


def test_a_name_keeps_the_marks_its_script_is_written_with() -> None:
    assert uploads.safe_name("मंज़ूरी.pdf") == "मंज़ूरी.pdf"
