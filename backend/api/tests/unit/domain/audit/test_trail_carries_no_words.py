"""Nothing a person could ask to have erased is written into the trail (ADR 0015).

Static, on purpose. The trail is append-only, so a test that wrote a bad row to
prove the rule would leave the bad row behind. This reads every call to
`audit.record(` in the source and refuses a `detail` that carries free text
under `reason`, or a contact under any name. A constant cause goes under
`cause`; the person is named by `subject_user_id`; the words live in their row,
sealed.
"""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[4] / "src" / "cmp"
FORBIDDEN_KEYS = (
    '"reason":',
    '"email":',
    '"mobile":',
    '"contact":',
    '"full_name":',
    '"to": fresh.get("responder_contact")',
)


def _record_calls(text: str) -> list[str]:
    """Each `audit.record(...)` / `record(...)` call, as its source text."""
    out = []
    for m in re.finditer(r"\baudit\.record\(|\brecord\(\n", text):
        depth, i = 0, m.end() - 1
        start = m.start()
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append(text[start : i + 1])
    return out


def test_no_reason_is_written_to_the_trail() -> None:
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text()
        for site in _record_calls(text):
            if "detail=" not in site:
                continue
            detail = site[site.index("detail=") :]
            for key in FORBIDDEN_KEYS:
                if key in detail:
                    offenders.append(f"{path.relative_to(SRC)}: {key}")
    assert not offenders, (
        "audit detail carries something a person could ask to erase:\n" + "\n".join(offenders)
    )
