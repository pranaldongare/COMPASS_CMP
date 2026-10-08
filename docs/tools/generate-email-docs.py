"""Write docs/email/messages.md: every message the platform sends, from the code.

    backend/api/.venv/bin/python docs/tools/generate-email-docs.py
    backend/api/.venv/bin/python docs/tools/generate-email-docs.py --check

Three sources, read rather than copied, so the table cannot drift:

* the catalogue, `cmp.core.messages.CATALOGUE` - each junction's key, title,
  channels, when it is sent, its variables and its default email subject;
* the Celery tasks under `cmp/tasks/` - which task calls `deliver()` with
  which junction, and its registered name, file and line;
* the code that queues each task - every call site outside `cmp/tasks/`
  that names the task function, with file and line.

It also writes `docs/notifications/<module>.md` (2026-10-08): each module's
emails end to end - when, to, cc, attachment, the default subject and body,
the task and where it is queued from - from the same three sources and the
catalogue's `to`, `attachment`, `COPYABLE` and `ATTACHABLE`.

`--check` exits 1 when a file on disk is not what the code says, for CI.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "backend" / "api"
SRC = API / "src"
OUT = ROOT / "docs" / "email" / "messages.md"
sys.path.insert(0, str(SRC))

from cmp.core.messages import ATTACHABLE, CATALOGUE, COPYABLE, Channel, Junction  # noqa: E402

NOTIFICATIONS = ROOT / "docs" / "notifications"

#: Which module file each catalogue group is written to, and in what words.
MODULES: list[tuple[str, str, tuple[str, ...], str]] = [
    (
        "users.md",
        "Users, sign-in and accounts",
        ("Sign-in", "Accounts", "Staff"),
        "Signing in, signing up, confirming a contact, staff invitations and password "
        "resets, a member of staff's role or account changing, a cover arranged, and a note "
        "the office resends.",
    ),
    (
        "projects.md",
        "Projects and approvals",
        ("Projects",),
        "A project's way from draft to approved: submitted, approved, sent back, closed, and "
        "the collectors named on it.",
    ),
    (
        "consent.md",
        "Consent",
        ("Consent",),
        "What a data principal is sent when she gives or withdraws consent.",
    ),
    (
        "rights.md",
        "Rights requests",
        ("Rights",),
        "A rights request from the requester's side - acknowledged, verified, answered, "
        "closed - the nominee's, the holders' tickets, and the Privacy Office's alerts.",
    ),
    (
        "breach.md",
        "Personal data breaches",
        ("Breach",),
        "The people a breach touched, the staff asked to help on a ticket, and the DPO's "
        "alerts on the breach's duties.",
    ),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def tasks_by_message() -> dict[str, list[dict[str, str]]]:
    """Message key -> the tasks that deliver it: function, Celery name, place."""
    found: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in sorted((SRC / "cmp" / "tasks").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            name = fn.name
            for deco in fn.decorator_list:
                if isinstance(deco, ast.Call):
                    for kw in deco.keywords:
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                            name = str(kw.value.value)
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "deliver"):
                    continue
                for arg in node.args[:1]:
                    if isinstance(arg, ast.Attribute) and getattr(arg.value, "id", "") == "Message":
                        found[arg.attr].append(
                            {
                                "function": fn.name,
                                "task": name,
                                "where": f"{rel(path)}:{node.lineno}",
                            }
                        )
    return found


def queued_from(functions: set[str]) -> dict[str, list[str]]:
    """Task function -> where the rest of the code queues it (file:line)."""
    places: dict[str, list[str]] = defaultdict(list)
    for path in sorted((SRC / "cmp").rglob("*.py")):
        if "tasks" in path.relative_to(SRC / "cmp").parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in functions and not isinstance(
                getattr(node, "ctx", None), ast.Store
            ):
                places[node.id].append(f"{rel(path)}:{node.lineno}")
            # The rights service queues its tasks by name: `_notify("send_x", ...)`.
            elif isinstance(node, ast.Constant) and node.value in functions:
                places[str(node.value)].append(f"{rel(path)}:{node.lineno}")
    # An import line is not a call site: keep the places that are calls'
    # arguments or calls, which is every line but the `from ... import`.
    out: dict[str, list[str]] = {}
    for fn, lines in places.items():
        kept = []
        for place in lines:
            file, line = place.rsplit(":", 1)
            text = (ROOT / file).read_text(encoding="utf-8").splitlines()[int(line) - 1].strip()
            if text.startswith(("from ", "import ")) or text.rstrip(",") in (fn, f'"{fn}"'):
                # `send_x,` alone on a line is usually an import list or an
                # argument; keep it only when it is an argument to a dispatch.
                prev = (ROOT / file).read_text(encoding="utf-8").splitlines()[int(line) - 2]
                if "dispatch" not in prev and "notify" not in prev and "(" not in prev:
                    continue
            kept.append(place)
        out[fn] = sorted(set(kept))
    return out


def cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render() -> str:
    tasks = tasks_by_message()
    callers = queued_from({t["function"] for ts in tasks.values() for t in ts})
    email = [j for j in CATALOGUE if Channel.EMAIL in j.channels]
    lines = [
        "# Every message the platform sends",
        "",
        "[Email](README.md) · [Messages, in the domain](../domain/messages.md)",
        "",
        "Generated by `docs/tools/generate-email-docs.py` from the code - the catalogue",
        "(`backend/api/src/cmp/core/messages.py`), the Celery tasks that send each one,",
        "and the code that queues those tasks. Do not edit by hand; run the tool.",
        "",
        (
            f"**{len(CATALOGUE)} messages, every one of which can go by email**; some by SMS too."
            if len(email) == len(CATALOGUE)
            else f"**{len(CATALOGUE)} messages; {len(email)} can go by email**, the rest by SMS only."
        ),
        "Which channel a message takes is the shape of the contact it is sent to: an",
        "address gets the email words, a number the SMS words. Every one is sent by a",
        "Celery task through `deliver()` (`cmp/infrastructure/messaging`), after the",
        "transaction that caused it has committed; the words are the default below",
        "unless the office replaced them in **Message templates**.",
        "",
        "## At a glance",
        "",
        "| # | Message (key) | Group | Channels | Sent when | Celery task |",
        "|---|---|---|---|---|---|",
    ]
    for i, j in enumerate(CATALOGUE, start=1):
        names = ", ".join(f"`{t['task']}`" for t in tasks.get(j.key.name, [])) or "-"
        channels = ", ".join(c.value for c in j.channels)
        lines.append(
            f"| {i} | **{cell(j.title)}** (`{j.key.value}`) | {j.group} | {channels} | "
            f"{cell(j.description)} | {names} |"
        )
    lines += ["", "## In the code", ""]
    lines += [
        "Where each message is rendered and sent, and where its task is queued from.",
        "",
        "| Message (key) | Email subject (default) | Variables | Sent by (task, file:line) | Queued from |",
        "|---|---|---|---|---|",
    ]
    for j in CATALOGUE:
        sent = tasks.get(j.key.name, [])
        by = "<br>".join(f"`{t['function']}` - `{t['where']}`" for t in sent) or "-"
        queued = "<br>".join(
            f"`{place}`" for t in sent for place in callers.get(t["function"], [])
        ) or ("**not queued anywhere** - the task exists, nothing sends it" if sent else "-")
        subject = f"{cell(j.email_subject)}" if j.email_subject else "(SMS only)"
        variables = ", ".join(f"`{v.name}`" for v in j.variables) or "-"
        lines.append(f"| `{j.key.value}` | {subject} | {variables} | {by} | {queued} |")
    lines.append("")
    return "\n".join(lines)


def _cc(j: Junction) -> str:
    if j.key in COPYABLE:
        return (
            "None by default. The Privacy Office may add up to 5 addresses in **Message "
            "templates → Copy to** (a team mailbox, an approvals inbox)."
        )
    names = {v.name for v in j.variables}
    own = {"portal_url", "withdraw_url", "console_url"}
    if "code" in names or any(n.endswith("_url") and n not in own for n in names):
        return "Never - it carries a code or a link, and a copy would hand it to somebody else."
    return "Never - it is written to one person about her own data; a copy would disclose it."


def _block(text: str) -> list[str]:
    return ["```text", *text.rstrip("\n").split("\n"), "```"]


def render_module(title: str, groups: tuple[str, ...], intro: str) -> str:
    tasks = tasks_by_message()
    callers = queued_from({t["function"] for ts in tasks.values() for t in ts})
    mine = [j for j in CATALOGUE if j.group in groups]
    lines = [
        f"# {title}: every email",
        "",
        "[Notification strategy](README.md) · [Implementation plan](implementation-plan.md) · "
        "[Every message](../email/messages.md)",
        "",
        "Generated by `docs/tools/generate-email-docs.py` from the code. Do not edit by hand.",
        "",
        intro,
        "",
        f"**{len(mine)} {'email' if len(mine) == 1 else 'emails'}.** The subject and body below "
        "are the defaults; the Privacy Office may replace the words of any of them in **Message "
        "templates**, and the variables are filled in when each is sent. Every one is sent by "
        "a Celery task through `deliver()` after the transaction that caused it has committed, "
        "from `SENDER_EMAIL`, laid out in the platform's email template.",
        "",
        "| # | Email | When | To | CC | Attachment |",
        "|---|---|---|---|---|---|",
    ]
    for i, j in enumerate(mine, start=1):
        cc = "Office may set" if j.key in COPYABLE else "Never"
        att = "Yes" if j.key in ATTACHABLE else "None"
        lines.append(
            f"| {i} | [{cell(j.title)}](#{j.key.value.replace('_', '-')}) | "
            f"{cell(j.description)} | {cell(j.to)} | {cc} | {att} |"
        )
    for i, j in enumerate(mine, start=1):
        sent = tasks.get(j.key.name, [])
        by = "; ".join(f"`{t['task']}` (`{t['where']}`)" for t in sent) or "-"
        queued = ", ".join(
            f"`{place}`" for t in sent for place in callers.get(t["function"], [])
        ) or "-"
        lines += [
            "",
            f'<a id="{j.key.value.replace("_", "-")}"></a>',
            f"## {i}. {j.title}",
            "",
            f"Key `{j.key.value}` · channels: {', '.join(c.value for c in j.channels)}",
            "",
            "| | |",
            "|---|---|",
            f"| When | {cell(j.description)} |",
            f"| To | {cell(j.to)} |",
            f"| CC | {cell(_cc(j))} |",
            f"| Attachment | {cell(j.attachment) if j.key in ATTACHABLE else 'None.'} |",
            f"| Sent by | {by} |",
            f"| Queued from | {queued} |",
            "| Variables | "
            + (", ".join(f"`{v.name}` ({cell(v.description)})" for v in j.variables) or "-")
            + " |",
        ]
        if Channel.EMAIL in j.channels:
            subject, body = j.default(Channel.EMAIL)
            lines += ["", f"**Subject:** `{subject}`", "", "**Body:**", "", *_block(body or "")]
        if Channel.SMS in j.channels:
            _, sms = j.default(Channel.SMS)
            lines += ["", "**SMS:**", "", *_block(sms)]
    lines.append("")
    return "\n".join(lines)


def outputs() -> list[tuple[Path, str]]:
    out = [(OUT, render())]
    for name, title, groups, intro in MODULES:
        out.append((NOTIFICATIONS / name, render_module(title, groups, intro)))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if a file is stale")
    args = parser.parse_args()
    files = outputs()
    if args.check:
        stale = [
            rel(path)
            for path, text in files
            if (path.read_text(encoding="utf-8") if path.exists() else "") != text
        ]
        if stale:
            print(f"stale: {', '.join(stale)}: run docs/tools/generate-email-docs.py")
            return 1
        print(f"{len(files)} files are current")
        return 0
    for path, text in files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(files)} files: {len(CATALOGUE)} messages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
