"""The look of every email (2026-10-06): one header, one footer, the content
laid out from the message's plain text - and nothing a person wrote ever
becoming markup.
"""

from __future__ import annotations

from cmp.infrastructure.email.layout import body_html, render_html, render_text


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


def test_the_plain_text_carries_the_same_footer() -> None:
    text = render_text(body="Hello.\n", organisation="COMPASS")
    assert text.startswith("Hello.") and "--\nCOMPASS Privacy Office" in text
