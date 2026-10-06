# ruff: noqa: E501 - an email template is read as markup; wrapped, it is not.
"""The look of every email: one header, one footer, the content laid out.

Every message the platform sends is written as plain text - the default in
`cmp.core.messages`, or the Privacy Office's own words from Message templates
- so the office edits words, never markup. This module lays that text out as
an HTML email around it, and the transport sends both: the HTML for every
mail client that shows it, the text for the ones that do not (and for spam
filters, which trust a message with both).

What the text becomes:

| In the text | In the email |
|---|---|
| Paragraphs, separated by a blank line | Paragraphs |
| A six-digit code alone on its line | The code, large, in a highlighted box |
| A link alone on its line | A button, with the address written beneath it; a short line ending ":" just above it ("Set your password here:") becomes the button's label |
| A link inside a sentence | A link |
| A short first line followed by more ("What happened") | A heading over its paragraph |
| Lines starting "- " | A bulleted list |
| "If you were not expecting this message..." | Small print, last |

Everything in the text is escaped before any of it becomes markup: a breach
notice's words or a person's name in a response are text, never HTML. The
layout is tables and inline styles - what email clients render alike - with
no images, scripts or remote files, so nothing is blocked and nothing loads
from elsewhere when the message is opened.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Final

# The console's colours, so an email looks like it came from the same place.
BRAND: Final = "#4f46e5"
BRAND_DARK: Final = "#3730a3"
INK: Final = "#1f2937"
MUTED: Final = "#6b7280"
PAGE: Final = "#f3f4f8"
CARD: Final = "#ffffff"
LINE: Final = "#e5e7eb"
CODE_BG: Final = "#eef2ff"

FONT: Final = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
)

_CODE = re.compile(r"^\s*(\d{6})\s*$")
_URL = re.compile(r"https?://[^\s<>\"']+[^\s<>\"'.,;:!?)\]]")
_LONE_URL = re.compile(r"^\s*(https?://\S+)\s*$")
_SMALL_PRINT = ("if you were not expecting this message",)


def _inline(text: str) -> str:
    """One line of text as HTML: escaped, its links made links."""
    out: list[str] = []
    last = 0
    for match in _URL.finditer(text):
        out.append(html.escape(text[last : match.start()]))
        url = html.escape(match.group(0), quote=True)
        out.append(
            f'<a href="{url}" style="color:{BRAND};text-decoration:underline;word-break:break-all;">'
            f"{url}</a>"
        )
        last = match.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


def _paragraph(lines: list[str]) -> str:
    text = "<br>".join(_inline(line.strip()) for line in lines)
    return f'<p style="margin:0 0 16px;font-size:15px;line-height:1.65;color:{INK};">{text}</p>'


def _heading(text: str) -> str:
    return (
        f'<p style="margin:24px 0 6px;font-size:13px;font-weight:700;letter-spacing:0.04em;'
        f'text-transform:uppercase;color:{BRAND_DARK};">{html.escape(text.strip())}</p>'
    )


def _code(code: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:4px 0 20px;"><tr><td align="center" '
        f'style="background:{CODE_BG};border:1px dashed {BRAND};border-radius:10px;'
        f"padding:16px 28px;font-family:'SFMono-Regular',Consolas,'Courier New',monospace;"
        f'font-size:30px;font-weight:700;letter-spacing:8px;color:{BRAND_DARK};">'
        f"{html.escape(code)}</td></tr></table>"
    )


def _button(url: str, label: str = "Open the link") -> str:
    href = html.escape(url, quote=True)
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:4px 0 8px;"><tr>'
        f'<td style="border-radius:8px;background:{BRAND};">'
        f'<a href="{href}" style="display:inline-block;padding:12px 22px;font-family:{FONT};'
        'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:8px;">'
        f"{html.escape(label)}</a></td></tr></table>"
        f'<p style="margin:0 0 16px;font-size:12px;line-height:1.5;color:{MUTED};'
        f'word-break:break-all;">{href}</p>'
    )


def _bullets(lines: list[str]) -> str:
    items = "".join(
        f'<li style="margin:0 0 6px;">{_inline(line.strip()[2:].strip())}</li>' for line in lines
    )
    return (
        f'<ul style="margin:0 0 16px;padding-left:22px;font-size:15px;line-height:1.6;'
        f'color:{INK};">{items}</ul>'
    )


def _small_print(lines: list[str]) -> str:
    text = " ".join(_inline(line.strip()) for line in lines)
    return (
        f'<p style="margin:24px 0 0;padding-top:16px;border-top:1px solid {LINE};'
        f'font-size:13px;line-height:1.6;color:{MUTED};">{text}</p>'
    )


def _is_heading(line: str, rest: list[str]) -> bool:
    """A short line with more beneath it and no sentence ending: a heading."""
    text = line.strip()
    return (
        bool(rest)
        and 0 < len(text) <= 60
        and not text.endswith((".", ":", ",", ";", "?", "!"))
        and not _URL.search(text)
        and not _CODE.match(text)
    )


def body_html(body: str) -> str:
    """The message's text, laid out."""
    blocks: list[str] = []
    for chunk in re.split(r"\n\s*\n", body.strip()):
        lines = [line for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].strip().lower().startswith(_SMALL_PRINT):
            blocks.append(_small_print(lines))
            continue
        if len(lines) > 1 and _is_heading(lines[0], lines[1:]):
            blocks.append(_heading(lines[0]))
            lines = lines[1:]
        blocks.extend(_lines(lines))
    return "\n".join(blocks)


def _lines(lines: list[str]) -> list[str]:
    """One paragraph's lines: text runs, bullet runs, codes and lone links."""
    out: list[str] = []
    text: list[str] = []
    bullets: list[str] = []
    for line in lines:
        if line.strip().startswith(("- ", "• ")):
            if text:
                out.append(_paragraph(text))
                text = []
            bullets.append(line)
            continue
        if bullets:
            out.append(_bullets(bullets))
            bullets = []
        code = _CODE.match(line)
        lone = _LONE_URL.match(line)
        if code:
            if text:
                out.append(_paragraph(text))
                text = []
            out.append(_code(code.group(1)))
        elif lone:
            label = "Open the link"
            # "Set your password here:" just above the link names the button.
            if text and text[-1].strip().endswith(":") and len(text[-1].strip()) <= 45:
                label = text.pop().strip().rstrip(":").removesuffix(" here").strip()
            if text:
                out.append(_paragraph(text))
                text = []
            out.append(_button(lone.group(1), label))
        else:
            text.append(line)
    if bullets:
        out.append(_bullets(bullets))
    if text:
        out.append(_paragraph(text))
    return out


def _preheader(body: str) -> str:
    """The line an inbox shows beside the subject: the message's first words,
    with any code left out of it."""
    words = " ".join(
        line.strip() for line in body.split("\n") if line.strip() and not _CODE.match(line)
    )
    return html.escape(words[:140])


def render_html(*, subject: str, body: str, organisation: str) -> str:
    """The whole email: header, the subject as its title, the content, the footer."""
    org = html.escape(organisation)
    year = datetime.now(UTC).year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light">
<title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:{PAGE};-webkit-text-size-adjust:100%;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{PAGE};">{_preheader(body)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAGE};">
<tr><td align="center" style="padding:32px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;font-family:{FONT};">

<tr><td style="background:{BRAND};background-image:linear-gradient(135deg,{BRAND} 0%,#2563eb 100%);border-radius:14px 14px 0 0;padding:22px 32px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="font-size:18px;font-weight:700;color:#ffffff;letter-spacing:0.01em;">{org}</td>
<td align="right" style="font-size:12px;font-weight:600;color:#e0e7ff;letter-spacing:0.08em;text-transform:uppercase;">Privacy Office</td>
</tr></table>
</td></tr>

<tr><td style="background:{CARD};padding:32px 32px 28px;border-left:1px solid {LINE};border-right:1px solid {LINE};">
<h1 style="margin:0 0 20px;font-size:21px;line-height:1.35;font-weight:700;color:{INK};">{html.escape(subject)}</h1>
{body_html(body)}
</td></tr>

<tr><td style="background:#f9fafb;border:1px solid {LINE};border-top:0;border-radius:0 0 14px 14px;padding:20px 32px;">
<p style="margin:0 0 6px;font-size:13px;font-weight:600;color:{INK};">{org} Privacy Office</p>
<p style="margin:0;font-size:12px;line-height:1.6;color:{MUTED};">This message was sent automatically by the {org} consent management platform. Your personal data is handled under the Digital Personal Data Protection Act, 2023.</p>
<p style="margin:10px 0 0;font-size:12px;color:{MUTED};">&copy; {year} {org}</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>
"""


def render_text(*, body: str, organisation: str) -> str:
    """The plain-text part: the message, then the same footer in words."""
    return (
        f"{body.rstrip()}\n\n"
        f"--\n{organisation} Privacy Office\n"
        f"This message was sent automatically by the {organisation} consent management platform.\n"
    )
