"""Generate the human-readable API and role reference from authoritative data."""

# Long strings below are Markdown rows and prose emitted verbatim.
# ruff: noqa: E501, RUF005, T201

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "backend" / "api" / "openapi.json"
OUT = ROOT / "api_docs"
METHODS = ("get", "post", "put", "patch", "delete")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def ref_name(schema: dict[str, Any]) -> str | None:
    ref = schema.get("$ref")
    return str(ref).rsplit("/", 1)[-1] if ref else None


def schema_label(schema: dict[str, Any]) -> str:
    if name := ref_name(schema):
        return f"[`{name}`](#schema-{slug(name)})"
    if "anyOf" in schema:
        return " or ".join(schema_label(item) for item in schema["anyOf"])
    if "allOf" in schema:
        return " and ".join(schema_label(item) for item in schema["allOf"])
    kind = schema.get("type", "object")
    if kind == "array":
        return f"array of {schema_label(schema.get('items', {}))}"
    if values := schema.get("enum"):
        return "enum: " + ", ".join(f"`{value}`" for value in values)
    return f"`{kind}`"


def constraints(schema: dict[str, Any]) -> str:
    bits: list[str] = []
    for key, label in (
        ("minLength", "min length"),
        ("maxLength", "max length"),
        ("minimum", "minimum"),
        ("maximum", "maximum"),
        ("pattern", "pattern"),
        ("format", "format"),
    ):
        if key in schema:
            bits.append(f"{label}: `{schema[key]}`")
    if "default" in schema:
        bits.append(f"default: `{schema['default']}`")
    for alternative in schema.get("anyOf", []):
        nested = constraints(alternative)
        if nested != "—":
            bits.extend(part for part in nested.split("; ") if part not in bits)
    return "; ".join(bits) or "—"


def example(schema: dict[str, Any], schemas: dict[str, Any], depth: int = 0) -> Any:
    if depth > 5:
        return "…"
    if name := ref_name(schema):
        return example(schemas.get(name, {}), schemas, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if schema.get("enum"):
        return schema["enum"][0]
    if "anyOf" in schema:
        candidates = [item for item in schema["anyOf"] if item.get("type") != "null"]
        return example(candidates[0] if candidates else {}, schemas, depth + 1)
    if "allOf" in schema:
        merged: dict[str, Any] = {}
        for item in schema["allOf"]:
            value = example(item, schemas, depth + 1)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        return {
            key: example(value, schemas, depth + 1)
            for key, value in schema.get("properties", {}).items()
        }
    if kind == "array":
        return [example(schema.get("items", {}), schemas, depth + 1)]
    if kind == "integer":
        return schema.get("minimum", 1)
    if kind == "number":
        return schema.get("minimum", 1.0)
    if kind == "boolean":
        return True
    if schema.get("format") == "date":
        return "2026-09-17"
    if schema.get("format") == "date-time":
        return "2026-09-17T12:00:00Z"
    if schema.get("format") == "uuid":
        return "00000000-0000-4000-8000-000000000000"
    return "string"


def json_block(value: Any) -> list[str]:
    return ["```json", json.dumps(value, indent=2, ensure_ascii=False), "```"]


def schema_section(name: str, schema: dict[str, Any]) -> list[str]:
    lines = [f'<a id="schema-{slug(name)}"></a>', f"#### `{name}`", ""]
    description = schema.get("description")
    if description:
        lines.extend([str(description).strip(), ""])
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if not properties:
        return lines + [f"Type: {schema_label(schema)}", ""]
    lines += ["| Field | Type | Required | Validation | Description |", "|---|---|---:|---|---|"]
    for field, detail in properties.items():
        desc = str(detail.get("description", "—")).replace("\n", " ").replace("|", "\\|")
        lines.append(
            f"| `{field}` | {schema_label(detail)} | {'Yes' if field in required else 'No'} "
            f"| {constraints(detail)} | {desc} |"
        )
    return lines + [""]


def access_for(tag: str, path: str) -> str:
    if tag in {"public information", "public consent"} or path in {"/health", "/ready", "/metrics"}:
        return "Public or operator endpoint; see the endpoint description and deployment controls."
    if tag == "auth":
        return (
            "Authentication endpoint; availability depends on the current sign-in or recovery step."
        )
    if tag == "me":
        return "Authenticated caller acting on their own records."
    if tag in {"meta", "dashboard"}:
        return "Authenticated caller; content is filtered for the active role."
    return (
        f"Role-controlled `{tag}` operation. See [`../../roles/README.md`](../../roles/README.md)."
    )


def operation_lines(
    order: int, tag: str, path: str, method: str, operation: dict[str, Any], schemas: dict[str, Any]
) -> tuple[list[str], set[str]]:
    used: set[str] = set()
    title = operation.get("summary") or operation.get("operationId") or path
    anchor = slug(f"{order}-{method}-{path}")
    lines = [
        f'<a id="{anchor}"></a>',
        f"## {order}. `{method.upper()} {path}` — {title}",
        "",
        "### API",
        "",
    ]
    lines += [
        f"- **Operation ID:** `{operation.get('operationId', '—')}`",
        f"- **Access:** {access_for(tag, path)}",
    ]
    if description := operation.get("description"):
        lines += ["", str(description).strip()]

    lines += ["", "### Validation", ""]
    params = operation.get("parameters", [])
    if params:
        lines += [
            "| Parameter | Location | Required | Type | Constraints | Description |",
            "|---|---|---:|---|---|---|",
        ]
        for param in params:
            detail = param.get("schema", {})
            desc = str(param.get("description", "—")).replace("\n", " ").replace("|", "\\|")
            lines.append(
                f"| `{param['name']}` | {param['in']} | {'Yes' if param.get('required') else 'No'} "
                f"| {schema_label(detail)} | {constraints(detail)} | {desc} |"
            )
            if name := ref_name(detail):
                used.add(name)
    else:
        lines.append(
            "No path, query, header, or cookie parameters are declared for this operation."
        )

    body = operation.get("requestBody")
    lines += ["", "### Payload", ""]
    if not body:
        lines.append("No request body.")
    else:
        lines.append(f"Request body required: **{'yes' if body.get('required') else 'no'}**.")
        for media, content in body.get("content", {}).items():
            schema = content.get("schema", {})
            lines += ["", f"**Content type:** `{media}`  ", f"**Schema:** {schema_label(schema)}"]
            if name := ref_name(schema):
                used.add(name)
            lines += [""] + json_block(example(schema, schemas))

    lines += ["", "### Response", ""]
    lines += ["| Status | Description | Content type | Schema |", "|---:|---|---|---|"]
    response_examples: list[tuple[str, str, Any]] = []
    for status, response in operation.get("responses", {}).items():
        content = response.get("content", {})
        if not content:
            lines.append(f"| `{status}` | {response.get('description', '—')} | — | — |")
            continue
        first = True
        for media, spec in content.items():
            schema = spec.get("schema", {})
            lines.append(
                f"| `{status}` | {response.get('description', '—') if first else '↳'} | `{media}` | {schema_label(schema)} |"
            )
            first = False
            if name := ref_name(schema):
                used.add(name)
            response_examples.append((status, media, example(schema, schemas)))
    for status, media, value in response_examples:
        lines += ["", f"**Example `{status}` `{media}` response:**", ""] + json_block(value)
    return lines + [""], used


def generate_modules(spec: dict[str, Any]) -> list[tuple[str, int]]:
    schemas = spec.get("components", {}).get("schemas", {})
    grouped: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    for path, path_item in spec["paths"].items():
        for method in METHODS:
            if operation := path_item.get(method):
                # OpenAPI permits several tags, but every operation belongs to
                # one module here. The first tag is FastAPI's primary grouping
                # and avoids documenting the same endpoint twice.
                tag = (operation.get("tags") or ["other"])[0]
                grouped.setdefault(tag, []).append((path, method, operation))

    modules_dir = OUT / "modules"
    if modules_dir.exists():
        shutil.rmtree(modules_dir)
    modules_dir.mkdir(parents=True)
    summary: list[tuple[str, int]] = []
    for tag, operations in sorted(grouped.items()):
        folder = modules_dir / slug(tag)
        folder.mkdir()
        used: set[str] = set()
        lines = [
            f"# {tag.title()} API",
            "",
            f"Generated from `backend/api/openapi.json`. **{len(operations)} operations.**",
            "",
        ]
        lines += [
            "For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.",
            "",
            "## Contents",
            "",
        ]
        for number, (path, method, _operation) in enumerate(operations, 1):
            anchor = slug(f"{number}-{method}-{path}")
            lines.append(f"{number}. [`{method.upper()} {path}`](#{anchor})")
        lines.append("")
        for number, (path, method, operation) in enumerate(operations, 1):
            rendered, refs = operation_lines(number, tag, path, method, operation, schemas)
            lines += rendered
            used |= refs
        if used:
            lines += ["# Referenced schemas", ""]
            pending = sorted(used)
            rendered_names: set[str] = set()
            while pending:
                name = pending.pop(0)
                if name in rendered_names or name not in schemas:
                    continue
                rendered_names.add(name)
                schema = schemas[name]
                lines += schema_section(name, schema)
                blob = json.dumps(schema)
                for candidate in re.findall(r'#/components/schemas/([^"/]+)', blob):
                    if candidate not in rendered_names:
                        pending.append(candidate)
        (folder / "api.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        summary.append((tag, len(operations)))
    return summary


def generate_roles() -> None:
    sys.path.insert(0, str(ROOT / "backend" / "api" / "src"))
    from cmp.core.permissions import MATRIX, NAV_BY_ROLE, ROLE_TITLES, Role

    roles_dir = OUT / "roles"
    if roles_dir.exists():
        shutil.rmtree(roles_dir)
    roles_dir.mkdir(parents=True)
    index = [
        "# Role access",
        "",
        "Generated from `cmp.core.permissions`; denied resources are shown explicitly.",
        "",
        "| Role | Documentation |",
        "|---|---|",
    ]
    all_resources = sorted(MATRIX)
    for role in Role:
        title = ROLE_TITLES[role.value]
        index.append(f"| `{role.value}` | [{title}]({role.value}.md) |")
        lines = [f"# {title} (`{role.value}`)", "", "## What this role can do", ""]
        lines.append(
            "Navigation returned after sign-in: "
            + ", ".join(f"`{item}`" for item in NAV_BY_ROLE[role])
            + "."
        )
        lines += [
            "",
            "## Resource access",
            "",
            "| Resource | Read | Write | Scope | What the scope means |",
            "|---|---:|---:|---|---|",
        ]
        for resource in all_resources:
            grant = MATRIX[resource].get(role)
            if grant is None:
                lines.append(f"| `{resource}` | No | No | `none` | Denied |")
            else:
                meanings = {
                    "all": "All rows",
                    "scoped": "Assigned project/organisational rows",
                    "own": "Own or addressed rows",
                    "none": "Denied",
                }
                lines.append(
                    f"| `{resource}` | {'Yes' if grant.readable else 'No'} | {'Yes' if grant.write else 'No'} "
                    f"| `{grant.scope.value}` | {meanings[grant.scope.value]} |"
                )
        lines += [
            "",
            "## Enforcement notes",
            "",
            "- A missing grant is a denial.",
            "- Scope is applied in the database query, not after rows are loaded.",
            "- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.",
            "- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.",
            "- Every staff role requires MFA by default.",
            "",
        ]
        (roles_dir / f"{role.value}.md").write_text("\n".join(lines), encoding="utf-8")
    (roles_dir / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def generate_readme(spec: dict[str, Any], modules: list[tuple[str, int]]) -> None:
    total = sum(count for _, count in modules)
    lines = [
        "# API documentation",
        "",
        f"Reference for **{total} operations over {len(spec['paths'])} paths**, grouped by OpenAPI module/tag.",
        "",
        "## How to read an endpoint",
        "",
        "Every endpoint uses the requested order:",
        "",
        "1. **API** — method, path, operation ID, access and behavior.",
        "2. **Validation** — path/query/header/cookie parameters and constraints.",
        "3. **Payload** — request content type, schema and generated shape, when a body exists.",
        "4. **Response** — status codes, content types, schemas and generated shapes.",
        "",
        "Generated values are structural examples, not production credentials or semantically valid business records. Service-layer validation can add rules beyond those expressible in OpenAPI.",
        "",
        "## Modules",
        "",
        "| Module | Operations | File |",
        "|---|---:|---|",
    ]
    for tag, count in modules:
        lines.append(
            f"| {tag.title()} | {count} | [`modules/{slug(tag)}/api.md`](modules/{slug(tag)}/api.md) |"
        )
    lines += [
        "",
        "## Roles",
        "",
        "See [`roles/README.md`](roles/README.md) for all seven roles, their read/write permissions, row scope, navigation, and enforcement notes.",
        "",
        "## Source and regeneration",
        "",
        "- API source: `backend/api/openapi.json`",
        "- Role source: `backend/api/src/cmp/core/permissions.py`",
        "- Regenerate: `cd backend/api && uv run python ../../api_docs/generate.py`",
        "",
        "Do not hand-edit generated module or role files; update the API schema or permission matrix and regenerate.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    spec = json.loads(OPENAPI.read_text(encoding="utf-8"))
    modules = generate_modules(spec)
    generate_roles()
    generate_readme(spec, modules)
    print(f"Generated {len(modules)} modules and 7 role documents.")


if __name__ == "__main__":
    main()
