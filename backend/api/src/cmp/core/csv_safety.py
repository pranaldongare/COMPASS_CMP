"""A cell that a spreadsheet would run is written so that it is only read.

Quoting a comma is not the same as neutralising a formula: `=HYPERLINK(...)`
survives CSV quoting intact and Excel evaluates it on open. A free-text cell
that begins with a formula character is prefixed with an apostrophe, which
every spreadsheet shows as text and never evaluates. Applied to free text
only; a mobile number begins with `+` on purpose and is validated to be
digits after it, so callers leave it alone.
"""

from __future__ import annotations

from typing import Final

FORMULA_LEADERS: Final = ("=", "+", "-", "@", "\t", "\r")


def text_cell(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(FORMULA_LEADERS):
        return "'" + text
    return text
