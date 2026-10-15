"""The consent record PDF (2026-10-15): what it says about the person, and
that it can say it in every language a notice is served in."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pytest

from cmp.core.errors import ServiceUnavailable
from cmp.domain.consent import record
from cmp.domain.consent.record import mask_email, mask_mobile, masked_contact, status_of
from cmp.infrastructure.pdf import Document, Heading, Verbatim, render


@pytest.mark.parametrize(
    ("mobile", "masked"),
    [
        ("+919876543210", "+91******3210"),
        ("+91 98765 43210", "+91******3210"),
        ("9876543210", "******3210"),
        ("1234", "****"),
    ],
)
def test_a_mobile_keeps_its_country_code_and_last_four(mobile: str, masked: str) -> None:
    assert mask_mobile(mobile) == masked


def test_an_email_keeps_its_first_letter_and_domain() -> None:
    assert mask_email("asha.rao@example.org") == "a***@example.org"
    assert mask_email("not-an-address") == "***"


def test_the_mobile_is_the_contact_shown_and_the_email_only_without_one() -> None:
    assert masked_contact("+919876543210", "a@b.org") == ("Mobile (masked)", "+91******3210")
    assert masked_contact(None, "asha@example.org") == ("Email (masked)", "a***@example.org")
    assert masked_contact(None, None) is None


@pytest.mark.parametrize(
    ("granted", "total", "withdrawal", "status"),
    [
        (2, 2, False, "consented"),
        (1, 2, False, "partial"),
        (0, 2, False, "declined"),
        (0, 2, True, "withdrawn"),
        (1, 2, True, "partial"),
    ],
)
def test_status_is_derived_as_every_consent_read_derives_it(
    granted: int, total: int, withdrawal: bool, status: str
) -> None:
    assert status_of(granted, total, is_withdrawal=withdrawal) == status


#: One line in each script a notice can be served in (language_code).
SCRIPTS = {
    "english": "Consent recorded under the DPDP Act, 2023.",
    "hindi": "धारा 5, डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 के अंतर्गत सूचना",
    "marathi": "तुमची संमती नोंदवली गेली आहे",
    "tamil": "உங்கள் ஒப்புதல் பதிவு செய்யப்பட்டது",
    "telugu": "మీ సమ్మతి నమోదు చేయబడింది",
    "kannada": "ನಿಮ್ಮ ಒಪ್ಪಿಗೆ ದಾಖಲಾಗಿದೆ",
    "bengali": "আপনার সম্মতি নথিভুক্ত হয়েছে",
    "gujarati": "તમારી સંમતિ નોંધાઈ છે",
}


def test_every_served_language_renders_with_no_missing_glyph(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A glyph the bundled fonts lack prints as an empty box: the record would
    no longer show the words as they were shown."""
    doc = Document(
        title="Consent record",
        created_at=datetime(2026, 10, 15, tzinfo=UTC),
        blocks=[Heading("Notice"), *(Verbatim(text) for text in SCRIPTS.values())],
    )
    with caplog.at_level(logging.WARNING):
        payload = render(doc)
    assert payload.startswith(b"%PDF")
    assert not [r for r in caplog.records if "missing" in r.getMessage()]


def test_the_language_enum_has_a_font_for_each_value() -> None:
    from cmp.core import enums

    language = getattr(enums, "LanguageCode", None)
    values = {v.value for v in language} if language else set(SCRIPTS)
    assert values <= set(SCRIPTS), f"no font tested for {values - set(SCRIPTS)}"


async def test_a_name_the_key_service_could_not_open_is_refused_not_printed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def nothing_opened(values: list[Any]) -> dict[str, Any]:
        return {}

    monkeypatch.setattr(record, "unseal_strings", nothing_opened)
    artefact = {"subject_name": "SE::v1:abc", "subject_mobile": None, "subject_email": None}
    with pytest.raises(ServiceUnavailable):
        await record._open_people([artefact])
