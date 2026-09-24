#!/usr/bin/env python3
"""Rebuild the database reference from a database, not by hand.

`docs/reference/database/` was assembled once, by hand, from a disposable
container at migration 0026. By 0029 it described a schema that no longer
existed: `email varchar(255)` where the column is `text`, and no sign of the
eight `*_hash` columns or `minor_until`. A reference that has to be rebuilt by
hand is a reference that goes stale, and one that quietly disagrees with the
database is worse than none.

So this reads the catalogue and writes all of it: the inventory JSON, the
schema SQL, the column reference, the enum reference and the Graphviz sources
for every diagram. Run it against a scratch database built from the migration
chain - never a database with data in it, though it only ever reads:

    createdb cmp_ref && POSTGRES_DB=cmp_ref alembic upgrade head
    python3 docs/tools/generate-schema-docs.py --database cmp_ref

Then render the SVGs (`--render` does this when a renderer is available):

    dot -Tsvg source/complete_schema.dot -o complete_schema.svg

The drawing style - the colours, the PK/FK/UQ markers, the module clusters,
the tooltips carrying the constraint definition - is kept exactly as the
hand-built diagrams had it, because people have those in review comments and
a wholesale restyle would make every old link point at something unfamiliar.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "reference" / "database"
MIGRATIONS = ROOT / "backend" / "api" / "migrations" / "versions"

#: Which module each table belongs to, and the order modules are drawn in.
#: Hand-maintained because it is an editorial decision, not a fact in the
#: catalogue: `auth_user` is identity, `consent_artefact` is consent, and no
#: column says so.
MODULES: dict[str, list[str]] = {
    "identity": ["auth_user", "person_type_history", "delegation"],
    "registry": ["purpose", "processor", "processor_respondent", "data_source"],
    "projects": [
        "project",
        "project_processor",
        "project_approval",
        "project_site",
        "project_status_history",
    ],
    "notices": ["notice", "notice_language", "notice_purpose"],
    "consent": ["consent_link", "consent_artefact", "consent_purpose_grant", "v_current_consent"],
    "exchange": [
        "export_log",
        "export_line",
        "import_batch",
        "collection",
        "data_asset",
        "asset_consent",
    ],
    "rights": [
        "rights_request",
        "rights_request_holder",
        "rights_request_item",
        "rights_ticket_message",
        "rights_response_file",
        "rights_item_execution",
        "legal_hold",
        "nomination",
    ],
    "platform": ["audit_log", "message_template"],
}
MODULE_OF = {table: module for module, tables in MODULES.items() for table in tables}

#: Compact type names for the diagrams; the reference prints the full ones.
SHORT_TYPES = [
    (r"^character varying\((\d+)\)$", r"varchar(\1)"),
    (r"^character varying$", "varchar"),
    (r"^timestamp with time zone$", "timestamptz"),
    (r"^timestamp without time zone$", "timestamp"),
    (r"^integer$", "int4"),
    (r"^bigint$", "int8"),
    (r"^smallint$", "int2"),
    (r"^boolean$", "bool"),
    (r"^double precision$", "float8"),
    (r"^numeric\((\d+),(\d+)\)$", r"numeric(\1,\2)"),
    (r"^character\((\d+)\)$", r"char(\1)"),
]

INK = {
    "edge": "#174E8295",
    "head": "#174E82",
    "band": "#F1F5F9",
    "row_a": "#F8FAFC",
    "row_b": "#FFFFFF",
    "muted": "#526477",
    "text": "#152536",
    "mark": "#334155",
    "fk": "#087F8C",
    "page": "#F7FAFC",
    "title": "#142C44",
}


# --------------------------------------------------------------- the catalogue
def catalogue(dsn: dict[str, str]) -> dict[str, Any]:
    """Everything the reference needs, read from PostgreSQL's own catalogue."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(**dsn, row_factory=dict_row) as conn:  # type: ignore[call-overload]
        q = conn.execute

        version = q("SHOW server_version").fetchone()["server_version"].split()[0]
        tables = q(
            """SELECT c.relname AS name, c.relkind::text AS kind,
                      obj_description(c.oid) AS comment
                 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind IN ('r','v')
                ORDER BY c.relkind DESC, c.relname"""
        ).fetchall()
        columns = q(
            """SELECT c.relname AS table_name, a.attname AS name, a.attnum AS position,
                      format_type(a.atttypid, a.atttypmod) AS type,
                      a.attnotnull AS not_null,
                      pg_get_expr(d.adbin, d.adrelid) AS default_value,
                      col_description(c.oid, a.attnum) AS comment
                 FROM pg_attribute a
                 JOIN pg_class c ON c.oid = a.attrelid
                 JOIN pg_namespace n ON n.oid = c.relnamespace
                 LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
                WHERE n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped
                  AND c.relkind IN ('r','v')
                ORDER BY c.relname, a.attnum"""
        ).fetchall()
        constraints = q(
            """SELECT rel.relname AS table_name, con.conname AS name, con.contype::text AS kind,
                      pg_get_constraintdef(con.oid) AS definition,
                      ARRAY(SELECT a.attname FROM unnest(con.conkey) k
                              JOIN pg_attribute a ON a.attrelid = rel.oid AND a.attnum = k
                             ORDER BY array_position(con.conkey, k)) AS columns,
                      ref.relname AS referenced_table,
                      ARRAY(SELECT a.attname FROM unnest(con.confkey) k
                              JOIN pg_attribute a ON a.attrelid = ref.oid AND a.attnum = k
                             ORDER BY array_position(con.confkey, k)) AS referenced_columns,
                      con.confdeltype::text AS delete_action,
                      con.confupdtype::text AS update_action,
                      con.condeferrable AS deferrable, con.condeferred AS initially_deferred
                 FROM pg_constraint con
                 JOIN pg_class rel ON rel.oid = con.conrelid
                 JOIN pg_namespace n ON n.oid = rel.relnamespace
                 LEFT JOIN pg_class ref ON ref.oid = con.confrelid
                WHERE n.nspname = 'public'
                ORDER BY rel.relname, con.conname"""
        ).fetchall()
        indexes = q(
            """SELECT tablename AS table_name, indexname AS name, indexdef AS definition
                 FROM pg_indexes WHERE schemaname = 'public'
                ORDER BY tablename, indexname"""
        ).fetchall()
        enums = q(
            """SELECT t.typname AS name,
                      ARRAY(SELECT e.enumlabel FROM pg_enum e
                             WHERE e.enumtypid = t.oid ORDER BY e.enumsortorder) AS values
                 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'public' AND t.typtype = 'e'
                ORDER BY t.typname"""
        ).fetchall()
        triggers = q(
            """SELECT c.relname AS table_name, t.tgname AS name,
                      pg_get_triggerdef(t.oid) AS definition
                 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                 JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND NOT t.tgisinternal
                ORDER BY c.relname, t.tgname"""
        ).fetchall()
        views = q(
            """SELECT viewname AS name, definition FROM pg_views
                WHERE schemaname = 'public' ORDER BY viewname"""
        ).fetchall()
        sequences = q(
            """SELECT sequencename AS name FROM pg_sequences
                WHERE schemaname = 'public' ORDER BY sequencename"""
        ).fetchall()
        functions = q(
            """SELECT p.proname AS name FROM pg_proc p
                 JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname LIKE 'cmp\\_%'
                ORDER BY p.proname"""
        ).fetchall()
        head = q("SELECT version_num FROM alembic_version").fetchone()["version_num"]

    view_names = {v["name"] for v in views}
    dependencies = [
        {"view": v["name"], "depends_on": sorted({t["name"] for t in tables if t["name"] in v["definition"]})}
        for v in views
    ]
    fks = [c for c in constraints if c["kind"] == "f"]
    checks = [c for c in constraints if c["kind"] == "c"]
    return {
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip(),
        "migration_head": head,
        "migrations": [
            {"revision": m.name.split("_")[0], "source": f"backend/api/migrations/versions/{m.name}"}
            for m in sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.py"))
        ],
        "postgres_version": version,
        "tables": tables,
        "columns": columns,
        "constraints": constraints,
        "indexes": indexes,
        "enums": enums,
        "triggers": triggers,
        "views": views,
        "view_dependencies": dependencies,
        "sequences": sequences,
        "functions": functions,
        "counts": {
            "application_tables": len([t for t in tables if t["kind"] == "r"]) - 1,
            "metadata_tables": 1,
            "views": len(view_names),
            "table_columns": len([c for c in columns if c["table_name"] != "alembic_version"
                                  and c["table_name"] not in view_names]),
            "foreign_keys": len(fks),
            "enums": len(enums),
            "triggers": len(triggers),
            "checks": len(checks),
        },
    }


# ------------------------------------------------------------------- helpers
def short(type_name: str) -> str:
    for pattern, replacement in SHORT_TYPES:
        if re.match(pattern, type_name):
            return re.sub(pattern, replacement, type_name)
    return type_name


def anchor(name: str) -> str:
    return name.replace("_", "-")


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def keys_of(inv: dict[str, Any]) -> tuple[dict, dict, dict]:
    """(primary key columns, unique columns, foreign key columns) per table."""
    pk, uq, fk = defaultdict(set), defaultdict(set), defaultdict(set)
    for c in inv["constraints"]:
        target = {"p": pk, "u": uq, "f": fk}.get(c["kind"])
        if target is not None:
            target[c["table_name"]].update(c["columns"])
    return pk, uq, fk


# ---------------------------------------------------------------- the writers
def write_inventory(inv: dict[str, Any]) -> None:
    (OUT / "schema_inventory.json").write_text(json.dumps(inv, indent=2, default=str) + "\n")


def write_table_reference(inv: dict[str, Any]) -> None:
    pk, uq, fk = keys_of(inv)
    by_table: dict[str, list] = defaultdict(list)
    for c in inv["columns"]:
        by_table[c["table_name"]].append(c)
    cons_by_table: dict[str, list] = defaultdict(list)
    for c in inv["constraints"]:
        cons_by_table[c["table_name"]].append(c)
    idx_by_table: dict[str, list] = defaultdict(list)
    for i in inv["indexes"]:
        idx_by_table[i["table_name"]].append(i)
    trg_by_table: dict[str, list] = defaultdict(list)
    for t in inv["triggers"]:
        trg_by_table[t["table_name"]].append(t)

    fk_ids = {c["name"]: f"FK{n:03d}" for n, c in enumerate(
        sorted([c for c in inv["constraints"] if c["kind"] == "f"], key=lambda c: c["name"]), start=1)}

    out = [
        "# Column and relationship reference",
        "",
        "[Guide](README.md) · [Complete SVG](complete_schema.svg) · [Enums](enum_reference.md)",
        "",
        f"Generated by `docs/tools/generate-schema-docs.py` from PostgreSQL "
        f"{inv['postgres_version']} after applying all {len(inv['migrations'])} repository "
        f"migrations to an empty isolated instance (head **{inv['migration_head']}**). View "
        "columns do not carry reliable NOT NULL metadata; their nullability is shown as derived. "
        "`UQ` marks membership in a unique constraint, including composite constraints; unique "
        "indexes and CHECK expressions are listed separately.",
        "",
    ]
    for table in inv["tables"]:
        name = table["name"]
        module = MODULE_OF.get(name, "").upper() or "—"
        kind = "Application table" if table["kind"] == "r" else "View"
        if name == "alembic_version":
            kind = "Migration metadata"
        out += [f"## {name}", "", f"Module: **{module.title()}**. {kind}.", ""]
        if table["comment"]:
            out += [table["comment"], ""]
        out += [
            "| Column | PostgreSQL type | Keys | Nullable | Default | Comment |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for c in by_table[name]:
            marks = []
            if c["name"] in pk[name]:
                marks.append("PK")
            if c["name"] in uq[name]:
                marks.append("UQ")
            if c["name"] in fk[name]:
                marks.append("FK")
            out.append(
                f"| {c['name']} | {c['type']} | {' '.join(marks) or '—'} | "
                f"{'No' if c['not_null'] else 'Yes'} | {c['default_value'] or '—'} | "
                f"{(c['comment'] or '—').replace(chr(10), ' ')} |"
            )
        out.append("")

        foreign = [c for c in cons_by_table[name] if c["kind"] == "f"]
        if foreign:
            out += ["### Foreign keys", "", "| ID | Column(s) | Referenced key | Definition |",
                    "| --- | --- | --- | --- |"]
            for c in foreign:
                cols = ", ".join(c["columns"])
                ref = f"{c['referenced_table']}({', '.join(c['referenced_columns'])})"
                out.append(f"| {fk_ids[c['name']]} | {cols} | {ref} | {c['definition']} |")
            out.append("")

        others = [c for c in cons_by_table[name] if c["kind"] in ("p", "u", "c")]
        if others:
            out += ["### Key and CHECK constraints", "", "| Name | Definition |", "| --- | --- |"]
            out += [f"| {c['name']} | {c['definition']} |" for c in others]
            out.append("")

        if idx_by_table[name]:
            out += ["### Indexes", "", "| Name | Definition |", "| --- | --- |"]
            out += [f"| {i['name']} | {i['definition']} |" for i in idx_by_table[name]]
            out.append("")

        if trg_by_table[name]:
            out += ["### Triggers", "", "| Name | Definition |", "| --- | --- |"]
            out += [f"| {t['name']} | {t['definition']} |" for t in trg_by_table[name]]
            out.append("")

    (OUT / "table_reference.md").write_text("\n".join(out).rstrip() + "\n")


def write_enum_reference(inv: dict[str, Any]) -> None:
    out = [
        "# Enum reference",
        "",
        "[Guide](README.md) · [Enum SVG](enums.svg) · [Columns](table_reference.md)",
        "",
        f"{len(inv['enums'])} enumerated types, in declaration order within each type.",
        "",
        "| Type | Values |",
        "| --- | --- |",
    ]
    out += [f"| `{e['name']}` | {', '.join(f'`{v}`' for v in e['values'])} |" for e in inv["enums"]]
    (OUT / "enum_reference.md").write_text("\n".join(out) + "\n")


# ------------------------------------------------------------------ the dots
def table_node(inv: dict[str, Any], name: str, *, context_only: bool = False) -> str:
    """One table drawn as a Graphviz HTML label: header, band, one row per column."""
    pk, uq, fk = keys_of(inv)
    columns = [c for c in inv["columns"] if c["table_name"] == name]
    fk_count = len({c["name"] for c in inv["constraints"]
                    if c["table_name"] == name and c["kind"] == "f"})
    module = MODULE_OF.get(name, "").upper() or "SCHEMA"
    if context_only:
        columns = [c for c in columns if c["name"] in pk[name] | uq[name] | fk[name]]

    rows = [
        f'<TR><TD COLSPAN="3" BGCOLOR="{INK["head"]}" ALIGN="LEFT">'
        f'<FONT COLOR="white" FACE="Helvetica" POINT-SIZE="16"><B>{esc(name)}</B></FONT></TD></TR>',
        f'<TR><TD COLSPAN="3" ALIGN="LEFT" BGCOLOR="{INK["band"]}">'
        f'<FONT FACE="Helvetica" POINT-SIZE="10" COLOR="{INK["muted"]}">{module} / '
        f'{len([c for c in inv["columns"] if c["table_name"] == name])} columns / '
        f"{fk_count} foreign keys</FONT></TD></TR>",
    ]
    for i, c in enumerate(columns):
        bg = INK["row_a"] if i % 2 == 0 else INK["row_b"]
        if c["name"] in pk[name]:
            mark, colour = "PK", INK["head"]
        elif c["name"] in fk[name]:
            mark, colour = "FK", INK["fk"]
        elif c["name"] in uq[name]:
            mark, colour = "UQ", INK["mark"]
        else:
            mark, colour = "/", INK["mark"]
        label = esc(c["name"]) + ("" if c["not_null"] else "?")
        rows.append(
            f'<TR><TD BGCOLOR="{bg}" ALIGN="LEFT"><FONT POINT-SIZE="9" COLOR="{colour}">{mark}'
            f'</FONT></TD><TD PORT="{esc(c["name"])}" BGCOLOR="{bg}" ALIGN="LEFT">'
            f'<FONT FACE="Helvetica" POINT-SIZE="11" COLOR="{INK["text"]}">{label}</FONT></TD>'
            f'<TD BGCOLOR="{bg}" ALIGN="LEFT"><FONT FACE="Helvetica" POINT-SIZE="10" '
            f'COLOR="{INK["muted"]}">{esc(short(c["type"]))}</FONT></TD></TR>'
        )
    table = (
        '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" '
        f'COLOR="{INK["head"]}" BGCOLOR="{INK["row_b"]}">' + "".join(rows) + "</TABLE>"
    )
    return (
        f'"{name}" [id="table_{name}", tooltip="{name}", '
        f'URL="../table_reference.md#{anchor(name)}", label=<{table}>];'
    )


def edges(inv: dict[str, Any], tables: set[str]) -> list[str]:
    fks = sorted([c for c in inv["constraints"] if c["kind"] == "f"], key=lambda c: c["name"])
    ids = {c["name"]: f"FK{n:03d}" for n, c in enumerate(fks, start=1)}
    not_null = {(c["table_name"], c["name"]) for c in inv["columns"] if c["not_null"]}
    out = []
    for c in fks:
        if c["table_name"] not in tables or c["referenced_table"] not in tables:
            continue
        style = "solid" if all((c["table_name"], col) in not_null for col in c["columns"]) else "dashed"
        tip = (
            f"{ids[c['name']]} / {c['name']} / {c['table_name']}({', '.join(c['columns'])}) to "
            f"{c['referenced_table']}({', '.join(c['referenced_columns'])}) / {c['definition']}"
        )
        out.append(
            f'"{c["table_name"]}":"{c["columns"][0]}":e -> '
            f'"{c["referenced_table"]}":"{c["referenced_columns"][0]}":w '
            f'[id="{ids[c["name"]]}", color="{INK["edge"]}", style="{style}", '
            f'tooltip="{esc(tip)}", edgetooltip="{esc(tip)}"];'
        )
    return out


def graph(inv: dict[str, Any], title: str, subtitle: str, body: list[str]) -> str:
    header = (
        f'<<FONT POINT-SIZE="30" COLOR="{INK["title"]}"><B>{title}</B></FONT><BR ALIGN="LEFT"/>'
        f'<FONT POINT-SIZE="14" COLOR="{INK["muted"]}">{subtitle}</FONT><BR ALIGN="LEFT"/>'
        '<BR ALIGN="LEFT"/>'
        f'<FONT POINT-SIZE="12" COLOR="{INK["mark"]}">FK arrow: child column to referenced key '
        "  |   Solid = required FK; dashed = nullable FK; dotted = view dependency</FONT>"
        '<BR ALIGN="LEFT"/>'
        f'<FONT POINT-SIZE="12" COLOR="{INK["mark"]}">PK = primary key; FK = foreign key; '
        "UQ = member of unique constraint (possibly composite); ? = nullable column</FONT>>"
    )
    return "\n".join(
        [
            "digraph Schema {",
            f'graph [rankdir=LR, bgcolor="{INK["page"]}", pad="0.5", nodesep="0.42", '
            'ranksep="1.25", splines=polyline, concentrate=false, compound=true, newrank=true, '
            f"outputorder=edgesfirst, fontname=\"Helvetica\", labelloc=t, labeljust=l, label={header}];",
            "node [shape=plain, fontname=\"Helvetica\", margin=0];",
            "edge [fontname=\"Helvetica\", fontsize=9, arrowsize=0.65, penwidth=1.1];",
            *body,
            "}",
            "",
        ]
    )


def write_dots(inv: dict[str, Any]) -> None:
    source = OUT / "source"
    source.mkdir(exist_ok=True)
    head, commit = inv["migration_head"], (inv["commit"] or "")[:7]
    drawn = {t["name"] for t in inv["tables"]} - {"alembic_version"}

    # One module at a time: the module's own tables in full, anything they
    # point at outside it as a key-only card, so the drawing stays readable.
    for module, names in MODULES.items():
        local = [n for n in names if n in drawn]
        outside = sorted(
            {c["referenced_table"] for c in inv["constraints"]
             if c["kind"] == "f" and c["table_name"] in local and c["referenced_table"] not in local}
        )
        body = [
            f'subgraph cluster_{module} {{ label="{module.upper()}"; color="{INK["head"]}65"; '
            f'fontcolor="{INK["head"]}"; fontsize=16; style="rounded"; margin=24;',
            *[table_node(inv, n) for n in local],
            "}",
            *[table_node(inv, n, context_only=True) for n in outside],
            *edges(inv, set(local) | set(outside)),
        ]
        (source / f"{module}.dot").write_text(
            graph(
                inv,
                f"COMPASS / {module.upper()}",
                f"Migration {head} / full module tables with outgoing references / source {commit}",
                body,
            )
        )

    # Everything, clustered by module.
    body = []
    for module, names in MODULES.items():
        local = [n for n in names if n in drawn]
        body += [
            f'subgraph cluster_{module} {{ label="{module.upper()}"; color="{INK["head"]}65"; '
            f'fontcolor="{INK["head"]}"; fontsize=16; style="rounded"; margin=24;',
            *[table_node(inv, n) for n in local],
            "}",
        ]
    body += [table_node(inv, n) for n in sorted(drawn - set(MODULE_OF))]
    body += edges(inv, drawn)
    (source / "complete_schema.dot").write_text(
        graph(
            inv,
            "COMPASS / COMPLETE SCHEMA",
            f"Migration {head} / {inv['counts']['application_tables']} tables / "
            f"{inv['counts']['foreign_keys']} foreign keys / source {commit}",
            body,
        )
    )

    # The overview: one compact card per table, relationships only.
    cards = []
    for name in sorted(drawn):
        module = MODULE_OF.get(name, "").upper() or "SCHEMA"
        count = len([c for c in inv["columns"] if c["table_name"] == name])
        cards.append(
            f'"{name}" [id="table_{name}", URL="../table_reference.md#{anchor(name)}", '
            f'label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="8" '
            f'COLOR="{INK["head"]}" BGCOLOR="{INK["row_b"]}">'
            f'<TR><TD BGCOLOR="{INK["head"]}" ALIGN="LEFT"><FONT COLOR="white" POINT-SIZE="14">'
            f"<B>{esc(name)}</B></FONT></TD></TR>"
            f'<TR><TD ALIGN="LEFT" BGCOLOR="{INK["band"]}"><FONT POINT-SIZE="10" '
            f'COLOR="{INK["muted"]}">{module} / {count} columns</FONT></TD></TR></TABLE>>];'
        )
    fks = sorted([c for c in inv["constraints"] if c["kind"] == "f"], key=lambda c: c["name"])
    seen: set[tuple[str, str]] = set()
    links = []
    for c in fks:
        pair = (c["table_name"], c["referenced_table"])
        if pair in seen or pair[1] is None:
            continue
        seen.add(pair)
        links.append(f'"{pair[0]}" -> "{pair[1]}" [color="{INK["edge"]}"];')
    (source / "schema_overview.dot").write_text(
        graph(
            inv,
            "COMPASS / RELATIONSHIPS",
            f"Migration {head} / {len(drawn)} tables and views / source {commit}",
            cards + links,
        )
    )

    # The enums, as one table each.
    nodes = []
    for e in inv["enums"]:
        values = "".join(
            f'<TR><TD ALIGN="LEFT" BGCOLOR="{INK["row_a"] if i % 2 == 0 else INK["row_b"]}">'
            f'<FONT POINT-SIZE="11" COLOR="{INK["text"]}">{esc(v)}</FONT></TD></TR>'
            for i, v in enumerate(e["values"])
        )
        nodes.append(
            f'"{e["name"]}" [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="5" COLOR="{INK["head"]}" BGCOLOR="{INK["row_b"]}">'
            f'<TR><TD BGCOLOR="{INK["head"]}" ALIGN="LEFT"><FONT COLOR="white" POINT-SIZE="13">'
            f"<B>{esc(e['name'])}</B></FONT></TD></TR>{values}</TABLE>>];"
        )
    (source / "enums.dot").write_text(
        graph(
            inv,
            "COMPASS / ENUMERATED TYPES",
            f"Migration {head} / {len(inv['enums'])} types / source {commit}",
            ["graph [rankdir=TB];", *nodes],
        )
    )


def render(names: list[str]) -> list[str]:
    """dot → svg, with whatever renderer this machine has. Returns what it did."""
    done = []
    for stem in names:
        src = OUT / "source" / f"{stem}.dot"
        dst = (OUT / "modules" / f"{stem}.svg") if stem in MODULES else (OUT / f"{stem}.svg")
        dst.parent.mkdir(exist_ok=True)
        try:
            result = subprocess.run(
                ["dot", "-Tsvg", str(src), "-o", str(dst)],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return done
        if result.returncode != 0:
            return done
        done.append(stem)
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="cmp_ref", help="the database to read")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--user", default="cmp")
    parser.add_argument("--password", default="cmp")
    parser.add_argument("--no-render", action="store_true", help="write .dot, do not render SVG")
    args = parser.parse_args()

    inv = catalogue(
        {
            "dbname": args.database,
            "host": args.host,
            "port": args.port,
            "user": args.user,
            "password": args.password,
        }
    )
    write_inventory(inv)
    write_table_reference(inv)
    write_enum_reference(inv)
    write_dots(inv)
    print(
        f"schema {inv['migration_head']}: {inv['counts']['application_tables']} tables, "
        f"{inv['counts']['table_columns']} columns, {inv['counts']['foreign_keys']} foreign keys, "
        f"{inv['counts']['enums']} enums"
    )
    if not args.no_render:
        stems = [*MODULES, "complete_schema", "schema_overview", "enums"]
        done = render(stems)
        if len(done) == len(stems):
            print(f"rendered {len(done)} SVGs")
        else:
            print(
                f"rendered {len(done)} of {len(stems)} SVGs - install Graphviz "
                "(`brew install graphviz`) and re-run, or render the .dot sources yourself",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
