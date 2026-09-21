#!/usr/bin/env python3
"""Every relative link in every Markdown file points at something that exists.

Two hundred documents cross-referencing each other need a check rather than a
convention. A link that 404s is not a small thing here: these documents are
read with trust, and a reader who follows a dead one learns to stop following
them.

Anchors are checked only as far as the file - `a.md#section` has to find `a.md`,
and whether the heading exists is not something this knows.

    python3 docs/tools/check-links.py          # everything
    python3 docs/tools/check-links.py docs     # one subtree
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"node_modules", ".venv", ".next", ".git", "test-results", "playwright-report"}
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


FENCE = re.compile(r"^\s*```", re.M)


def outside_code(text: str) -> str:
    """The prose only.

    A document that quotes a script - this repository has several - would
    otherwise have its example strings read as links. Everything between a pair
    of fences is dropped.
    """
    parts = FENCE.split(text)
    return "\n".join(parts[::2])


def files(where: Path):
    for path in where.rglob("*.md"):
        if not SKIP & set(path.parts):
            yield path


def main() -> int:
    where = ROOT / sys.argv[1] if len(sys.argv) > 1 else ROOT
    broken: list[str] = []
    checked = 0

    for md in files(where):
        for text, target in LINK.findall(outside_code(md.read_text(encoding="utf-8"))):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            checked += 1
            if not (md.parent / target.split("#")[0]).exists():
                broken.append(f"{md.relative_to(ROOT)}: [{text}]({target})")

    if broken:
        print(f"{len(broken)} broken of {checked} relative links:\n", file=sys.stderr)
        print("\n".join(f"  {b}" for b in broken), file=sys.stderr)
        return 1
    print(f"all {checked} relative links resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
