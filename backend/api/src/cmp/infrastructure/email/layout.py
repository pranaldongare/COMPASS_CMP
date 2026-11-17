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
| Text marked `quoted()` (a report's words) | Plain paragraphs and nothing else |

Everything in the text is escaped before any of it becomes markup: a breach
notice's words or a person's name in a response are text, never HTML. The
layout is tables and inline styles - what email clients render alike - with
no images, scripts or remote files, so nothing is blocked and nothing loads
from elsewhere when the message is opened.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final

# The look chosen on 2026-11-17 (wireframe C): centred, a soft green accent,
# a round badge over the title, a pill button, a quiet footer.
BRAND: Final = "#0f9f8f"
BRAND_DARK: Final = "#0b6157"
INK: Final = "#172033"
MUTED: Final = "#64708a"
PAGE: Final = "#e9f3f4"
CARD: Final = "#ffffff"
LINE: Final = "#e4e9f2"
CODE_BG: Final = "#e6f7f4"
WASH: Final = "#dff4f1"
FOOT: Final = "#f5f8fb"

#: A message this short is set centred, as a card; a longer one - a notice, a
#: report, a digest - is read, so its text is set from the left.
CENTRED_UP_TO: Final = 600

FONT: Final = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
)

_CODE = re.compile(r"^\s*(\d{6})\s*$")
_URL = re.compile(r"https?://[^\s<>\"']+[^\s<>\"'.,;:!?)\]]")
_LONE_URL = re.compile(r"^\s*(https?://\S+)\s*$")
_SMALL_PRINT = ("if you were not expecting this message",)

#: Around text that is quoted rather than the platform's own. Control characters
#: nobody types, and `quoted` takes them out of what it marks, so the words
#: cannot end their own quotation.
_QUOTE_OPEN: Final = "\x02"
_QUOTE_CLOSE: Final = "\x03"
_QUOTED = re.compile(f"{_QUOTE_OPEN}(.*?){_QUOTE_CLOSE}", re.DOTALL)


def quoted(text: str) -> str:
    """Mark text as somebody's words, for a template variable that carries them:
    in the email they stay plain paragraphs, whatever they look like. A link
    alone on its line stays text, and so does a six-digit number or a line
    starting "- ". The template's own links, around it, work as ever."""
    return f"{_QUOTE_OPEN}{unmarked(text)}{_QUOTE_CLOSE}"


def unmarked(text: str) -> str:
    """The text with its quotation marks gone: what a reader of plain text gets."""
    return text.replace(_QUOTE_OPEN, "").replace(_QUOTE_CLOSE, "")


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


def _paragraph(lines: list[str], *, inline: Callable[[str], str] = _inline) -> str:
    text = "<br>".join(inline(line.strip()) for line in lines)
    return f'<p style="margin:0 0 16px;font-size:15px;line-height:1.65;color:{INK};">{text}</p>'


def _heading(text: str) -> str:
    return (
        f'<p style="margin:24px 0 6px;font-size:13px;font-weight:700;letter-spacing:0.04em;'
        f'text-transform:uppercase;color:{BRAND_DARK};">{html.escape(text.strip())}</p>'
    )


def _code(code: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'align="center" style="margin:4px auto 20px;"><tr><td align="center" '
        f'style="background:{CODE_BG};border-radius:14px;'
        f"padding:16px 28px;font-family:'SFMono-Regular',Consolas,'Courier New',monospace;"
        f'font-size:30px;font-weight:700;letter-spacing:8px;color:{BRAND_DARK};">'
        f"{html.escape(code)}</td></tr></table>"
    )


def _button(url: str, label: str = "Open the link") -> str:
    href = html.escape(url, quote=True)
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'align="center" style="margin:6px auto 8px;"><tr>'
        f'<td style="border-radius:999px;background:{BRAND};">'
        f'<a href="{href}" style="display:inline-block;padding:13px 28px;font-family:{FONT};'
        'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;border-radius:999px;">'
        f"{html.escape(label)}</a></td></tr></table>"
        f'<p style="margin:0 0 16px;font-size:12px;line-height:1.5;color:{MUTED};'
        f'word-break:break-all;">{href}</p>'
    )


def _bullets(lines: list[str]) -> str:
    items = "".join(
        f'<li style="margin:0 0 6px;">{_inline(line.strip()[2:].strip())}</li>' for line in lines
    )
    return (
        f'<ul style="margin:0 0 16px;padding-left:22px;text-align:left;font-size:15px;line-height:1.6;'
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
    # Split on a group: every second part is what was quoted.
    for index, part in enumerate(_QUOTED.split(body)):
        blocks.extend(_quoted_blocks(part) if index % 2 else _blocks(part))
    return "\n".join(blocks)


def _chunks(text: str) -> list[list[str]]:
    """The text's paragraphs, as lines."""
    chunks = [
        [line for line in chunk.split("\n") if line.strip()]
        for chunk in re.split(r"\n\s*\n", text.strip())
    ]
    return [lines for lines in chunks if lines]


def _quoted_blocks(text: str) -> list[str]:
    """Somebody's words: escaped, in paragraphs, and read as nothing else."""
    return [_paragraph(lines, inline=html.escape) for lines in _chunks(text)]


def _blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for lines in _chunks(text):
        if lines[0].strip().lower().startswith(_SMALL_PRINT):
            blocks.append(_small_print(lines))
            continue
        if len(lines) > 1 and _is_heading(lines[0], lines[1:]):
            blocks.append(_heading(lines[0]))
            lines = lines[1:]
        blocks.extend(_lines(lines))
    return blocks


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
        line.strip()
        for line in unmarked(body).split("\n")
        if line.strip() and not _CODE.match(line)
    )
    return html.escape(words[:140])


_ASKS = ("action required", "needs your", "is waiting", "waiting for")


def _kind(body: str, subject: str = "") -> tuple[str, str]:
    """What the message is, read from its own text, for the badge and the label
    over the title: one carrying a code, one with something to open, or one
    that only tells. Words that are quoted do not count."""
    own = _QUOTED.sub("", body)
    lines = own.split("\n")
    if any(_CODE.match(line) for line in lines):
        return "&#128274;", "Verification"
    if any(_LONE_URL.match(line) for line in lines) or any(a in subject.lower() for a in _ASKS):
        return "&#128233;", "Action needed"
    return "&#128276;", "Notice"


def _align(body: str) -> str:
    text = unmarked(body)
    short = len(text) <= CENTRED_UP_TO and not any(
        line.strip().startswith(("- ", "\u2022 ")) for line in text.split("\n")
    )
    return "center" if short else "left"


def render_html(*, subject: str, body: str, organisation: str) -> str:
    """The whole email: header, the subject as its title, the content, the footer."""
    org = html.escape(organisation)
    year = datetime.now(UTC).year
    icon, label = _kind(body, subject)
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

<tr><td align="center" style="background:{WASH};background-image:linear-gradient(180deg,{WASH} 0%,{CARD} 100%);border-radius:22px 22px 0 0;padding:26px 32px 6px;">
<p style="margin:0;font-size:17px;font-weight:700;color:{INK};">{org}</p>
<p style="margin:4px 0 0;font-size:11px;font-weight:600;color:{MUTED};letter-spacing:0.14em;text-transform:uppercase;">Privacy Office</p>
</td></tr>

<tr><td style="background:{CARD};padding:20px 32px 28px;">
<table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto 14px;"><tr>
<td align="center" width="60" height="60" style="width:60px;height:60px;background:{BRAND};border:8px solid {CODE_BG};border-radius:50%;font-size:26px;line-height:60px;color:#ffffff;">{icon}</td>
</tr></table>
<p style="margin:0 0 12px;text-align:center;"><span style="display:inline-block;background:{CODE_BG};color:{BRAND_DARK};border-radius:999px;padding:4px 12px;font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;">{label}</span></p>
<h1 style="margin:0 0 20px;font-size:22px;line-height:1.3;font-weight:700;color:{INK};text-align:center;">{html.escape(subject)}</h1>
<div style="text-align:{_align(body)};">
{body_html(body)}
</div>
</td></tr>

<tr><td align="center" style="background:{FOOT};border-radius:0 0 22px 22px;padding:22px 32px;text-align:center;">
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
        f"{unmarked(body).rstrip()}\n\n"
        f"--\n{organisation} Privacy Office\n"
        f"This message was sent automatically by the {organisation} consent management platform.\n"
    )
