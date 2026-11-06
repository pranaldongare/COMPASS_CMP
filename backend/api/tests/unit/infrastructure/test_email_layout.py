"""The look of every email (2026-10-06): one header, one footer, the content
laid out from the message's plain text - and nothing a person wrote ever
becoming markup.
"""

from __future__ import annotations

from pathlib import Path

from cmp.core.messages import Channel, Message
from cmp.infrastructure.email import ConsoleEmailTransport
from cmp.infrastructure.email.layout import (
    body_html,
    quoted,
    render_html,
    render_text,
    unmarked,
)
from cmp.infrastructure.email.transport import compose
from cmp.infrastructure.messaging import render


def test_a_persons_words_are_text_never_markup() -> None:
    page = render_html(
        subject="<b>Hi</b>",
        body='Dear <script>alert(1)</script> "Asha" & co\n\n<img src=x onerror=1>',
        organisation="Acme & <Sons>",
    )
    assert "<script>" not in page and "<img" not in page and "<b>Hi" not in page
    assert "&lt;script&gt;" in page and "Acme &amp; &lt;Sons&gt;" in page


def test_a_code_alone_on_its_line_is_shown_large() -> None:
    html = body_html("Your sign-in code is:\n\n    482913\n\nEnter it.")
    assert ">482913<" in html and "letter-spacing:8px" in html


def test_a_link_alone_is_a_button_named_by_the_line_above() -> None:
    html = body_html("Set your password here:\nhttps://console.example.org/reset?x=1&y=2")
    assert ">Set your password</a>" in html
    assert 'href="https://console.example.org/reset?x=1&amp;y=2"' in html
    plain = body_html("Read more:\nhttps://example.org/a\n\nSee\nhttps://example.org/b")
    assert ">Read more</a>" in plain and ">Open the link</a>" in plain


def test_a_link_in_a_sentence_is_a_link() -> None:
    html = body_html("This notice is also in your account: https://portal.example.org.")
    assert '<a href="https://portal.example.org"' in html and "</a>." in html


def test_headings_bullets_and_small_print() -> None:
    html = body_html(
        "What happened\nA list went to the wrong address.\n\n"
        "You agreed to:\n- Gait analysis\n- Follow-up contact\n\n"
        "If you were not expecting this message, please tell the Privacy Office."
    )
    assert "text-transform:uppercase" in html and ">What happened<" in html
    assert html.count("<li") == 2
    assert "border-top:1px solid" in html


def test_the_page_has_its_header_footer_and_a_preheader_without_the_code() -> None:
    page = render_html(
        subject="482913 is your code", body="Your code is:\n\n    482913\n", organisation="COMPASS"
    )
    assert "Privacy Office" in page and "consent management platform" in page
    preheader = page.split("display:none")[1].split("</div>")[0]
    assert "482913" not in preheader and "Your code is:" in preheader


#: Everything the layout would make something of, as a report might hold it.
_WORDS = (
    "What was seen\n"
    "Indicators in the log:\n"
    "http://203.0.113.9/payload.exe\n\n"
    "Also at https://example.org/a in a sentence.\n\n"
    "    482913\n\n"
    "- not a list\n\n"
    "If you were not expecting this message, it is only a report's words."
)


def test_quoted_words_stay_plain_paragraphs_however_they_read() -> None:
    html = body_html(quoted(_WORDS))
    assert "<a " not in html, "no link and no button"
    assert "letter-spacing:8px" not in html, "no code box"
    assert "<li" not in html and "text-transform:uppercase" not in html
    assert "border-top:1px solid" not in html, "no small print"
    assert html.count("<p ") == 5
    assert "http://203.0.113.9/payload.exe" in html and "482913" in html


def test_quoted_words_are_escaped() -> None:
    html = body_html(quoted('<script>alert(1)</script> & "co"'))
    assert "<script>" not in html and "&lt;script&gt;" in html and "&amp;" in html


def test_the_templates_own_links_work_around_what_is_quoted() -> None:
    body = (
        "Open the report here:\nhttps://console.example.org/r/1\n\n"
        + quoted("https://evil.example/x")
        + "\n\nAlso see https://console.example.org/help.\n\n"
        "If you were not expecting this message, please tell the Privacy Office."
    )
    html = body_html(body)
    assert ">Open the report</a>" in html
    assert 'href="https://console.example.org/help"' in html
    assert "evil.example" in html and 'href="https://evil.example' not in html
    assert "border-top:1px solid" in html, "the template's small print is still small print"


def test_the_mail_about_a_public_report_keeps_its_button_for_the_officers() -> None:
    _, body = render(
        Message.INCIDENT_REPORTED,
        Channel.EMAIL,
        {
            "incident_reference": "INC-2026-0042",
            "received_at": "6 November 2026, 09:14 UTC",
            "breaches_url": "https://console.example.org/breaches",
        },
        overrides={},
    )
    html = body_html(body)
    assert ">For those officers, the list of incidents</a>" in html
    assert 'href="https://console.example.org/breaches"' in html


def test_words_cannot_close_their_own_quotation() -> None:
    html = body_html(quoted("before\x03\n\nhttps://evil.example/x\n\n\x02after"))
    assert "<a " not in html
    assert "\x02" not in html and "\x03" not in html


def test_the_plain_text_part_and_the_preheader_carry_no_marks() -> None:
    body = "Before.\n\n" + quoted("Their words.\nhttp://203.0.113.9/payload.exe") + "\n\nAfter."
    text = render_text(body=body, organisation="COMPASS")
    assert "\x02" not in text and "\x03" not in text
    assert text.startswith(
        "Before.\n\nTheir words.\nhttp://203.0.113.9/payload.exe\n\nAfter.\n\n--\n"
    )
    page = render_html(subject="A report", body=body, organisation="COMPASS")
    assert "\x02" not in page and "\x03" not in page
    assert unmarked(body) == "Before.\n\nTheir words.\nhttp://203.0.113.9/payload.exe\n\nAfter."


def test_the_message_sent_and_the_local_outbox_carry_no_marks(tmp_path: Path) -> None:
    body = "Before.\n\n" + quoted("Their words.\nhttp://203.0.113.9/payload.exe")
    message = compose(
        sender="office@example.org", to="chair@example.org", subject="A report", body=body
    )
    plain = message.get_body(("plain",))
    html = message.get_body(("html",))
    assert plain is not None and html is not None
    assert "\x02" not in plain.get_content() and "\x03" not in plain.get_content()
    assert "Their words.\nhttp://203.0.113.9/payload.exe" in plain.get_content()
    assert "<a " not in html.get_content()

    outbox = tmp_path / "outbox.log"
    ConsoleEmailTransport(str(outbox)).send(to="chair@example.org", subject="A report", body=body)
    assert "Their words." in outbox.read_text(encoding="utf-8")
    assert "\x02" not in outbox.read_text(encoding="utf-8")


def test_the_plain_text_carries_the_same_footer() -> None:
    text = render_text(body="Hello.\n", organisation="COMPASS")
    assert text.startswith("Hello.") and "--\nCOMPASS Privacy Office" in text
