# Exchange API

Generated from `backend/api/openapi.json`. **19 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /exports`](#1_get_exports)
2. [`GET /collections`](#2_get_collections)
3. [`GET /projects/{project_uuid}/exports`](#3_get_projects_project_uuid_exports)
4. [`POST /projects/{project_uuid}/exports`](#4_post_projects_project_uuid_exports)
5. [`GET /exports/{export_uuid}`](#5_get_exports_export_uuid)
6. [`GET /exports/{export_uuid}/download`](#6_get_exports_export_uuid_download)
7. [`GET /exports/{export_uuid}/lines`](#7_get_exports_export_uuid_lines)
8. [`GET /imports/template`](#8_get_imports_template)
9. [`POST /imports/validate`](#9_post_imports_validate)
10. [`GET /imports`](#10_get_imports)
11. [`POST /imports`](#11_post_imports)
12. [`GET /imports/{batch_uuid}`](#12_get_imports_batch_uuid)
13. [`GET /imports/{batch_uuid}/errors`](#13_get_imports_batch_uuid_errors)
14. [`GET /projects/{project_uuid}/collections`](#14_get_projects_project_uuid_collections)
15. [`GET /collections/{collection_uuid}`](#15_get_collections_collection_uuid)
16. [`GET /collections/{collection_uuid}/assets`](#16_get_collections_collection_uuid_assets)
17. [`GET /collections/{collection_uuid}/exceptions`](#17_get_collections_collection_uuid_exceptions)
18. [`GET /assets/{asset_uuid}`](#18_get_assets_asset_uuid)
19. [`GET /assets/{asset_uuid}/subjects`](#19_get_assets_asset_uuid_subjects)

<a id="1_get_exports"></a>
## 1. `GET /exports` — The disclosure register

### API

- **Operation ID:** `list_all_exports_exports_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

Every export in scope: what left, when, to which site, and how many people.

This is the register that makes s.11(1)(b) answerable at the organisation
level rather than one project at a time.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `type` | query | No | `string` or `null` | — | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_ExportListRow_`](#schema-page_exportlistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "export_uuid": "00000000-0000-4000-8000-000000000000",
      "export_type": "string",
      "exported_at": "2026-09-17T12:00:00Z",
      "row_count": 1,
      "file_hash": "string",
      "line_count": "…",
      "site_uuid": "…",
      "site_label": "…",
      "exported_by_name": "…",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
    }
  ],
  "next_cursor": "string",
  "total": 1
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="2_get_collections"></a>
## 2. `GET /collections` — All collections, with their reconciliation gap

### API

- **Operation ID:** `list_all_collections_collections_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

`unaccounted` is declared minus mapped, carried in the list itself.

The failure mode this exists for is 500 declared and 480 mapped. Surfacing
the gap here means nobody has to open each collection to find the one with
twenty assets in an unlawful state.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_CollectionListRow_`](#schema-page_collectionlistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "collection_uuid": "00000000-0000-4000-8000-000000000000",
      "source_collection_ref": "string",
      "collected_on": "string",
      "declared_asset_count": 1,
      "mapped_asset_count": 1,
      "unaccounted": 1,
      "agent_ref": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "source_uuid": "00000000-0000-4000-8000-000000000000",
      "source_code": "string",
      "source_name": "string",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "site_uuid": "…",
      "site_label": "…"
    }
  ],
  "next_cursor": "string",
  "total": 1
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="3_get_projects_project_uuid_exports"></a>
## 3. `GET /projects/{project_uuid}/exports` — List Exports

### API

- **Operation ID:** `list_exports_projects__project_uuid__exports_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ExportOut`](#schema-exportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "export_uuid": "00000000-0000-4000-8000-000000000000",
    "export_type": "string",
    "exported_at": "2026-09-17T12:00:00Z",
    "row_count": 1,
    "file_hash": "string",
    "line_count": 1,
    "site_uuid": "00000000-0000-4000-8000-000000000000",
    "site_label": "string",
    "exported_by_name": "string"
  }
]
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="4_post_projects_project_uuid_exports"></a>
## 4. `POST /projects/{project_uuid}/exports` — Generate Export

### API

- **Operation ID:** `generate_export_projects__project_uuid__exports_post`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

One CSV for the project, and it carries person rows.

No body: there is one kind of export and it covers the project. What the
caller may see decides the contents - a collection owner gets the people who
consented at the sites they run, a DPO gets all of them - so the same
request returns a different, correct file to each of them.

Every person named writes an `export_line`. That is the disclosure record,
and it is why generating and downloading are separate: re-downloading must
not claim a second disclosure.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`ExportOut`](#schema-exportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "export_uuid": "00000000-0000-4000-8000-000000000000",
  "export_type": "string",
  "exported_at": "2026-09-17T12:00:00Z",
  "row_count": 1,
  "file_hash": "string",
  "line_count": 1,
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "site_label": "string",
  "exported_by_name": "string"
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="5_get_exports_export_uuid"></a>
## 5. `GET /exports/{export_uuid}` — Get Export

### API

- **Operation ID:** `get_export_exports__export_uuid__get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `export_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ExportOut`](#schema-exportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "export_uuid": "00000000-0000-4000-8000-000000000000",
  "export_type": "string",
  "exported_at": "2026-09-17T12:00:00Z",
  "row_count": 1,
  "file_hash": "string",
  "line_count": 1,
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "site_label": "string",
  "exported_by_name": "string"
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="6_get_exports_export_uuid_download"></a>
## 6. `GET /exports/{export_uuid}/download` — Download Export

### API

- **Operation ID:** `download_export_exports__export_uuid__download_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

Repeatable, and it does not write a new disclosure record.

The staleness header is deliberate: a consented list is true at the moment it
was generated, and somebody acting on a three-week-old file needs to know
that withdrawals since then are not reflected in it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `export_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
"string"
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="7_get_exports_export_uuid_lines"></a>
## 7. `GET /exports/{export_uuid}/lines` — Who was in this file (s.11(1)(b))

### API

- **Operation ID:** `export_lines_exports__export_uuid__lines_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `export_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {}
]
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="8_get_imports_template"></a>
## 8. `GET /imports/template` — A manifest file to fill in

### API

- **Operation ID:** `import_template_imports_template_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

The CSV, with its own instructions in it.

Registered before `/imports/{batch_uuid}` in this module so the literal path
wins - `template` is not a uuid, but relying on the parser to notice that is
relying on the wrong thing.

Not cached. The file names the valid asset types and subject roles, which
come from the same constants the parser checks against, so a stale copy in a
proxy would hand somebody a template that disagrees with the validator.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |

**Example `200` `application/json` response:**

```json
"string"
```

<a id="9_post_imports_validate"></a>
## 9. `POST /imports/validate` — Dry run - nothing is written

### API

- **Operation ID:** `validate_import_imports_validate_post`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

Same parsing, same checks, nothing written.

A manifest arriving from a third-party tool is the input you trust least, and
finding out after a partial write is worse than finding out before.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_validate_import_imports_validate_post`](#schema-body_validate_import_imports_validate_post)

```json
{
  "source": "00000000-0000-4000-8000-000000000000",
  "manifest": "string",
  "project": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="10_get_imports"></a>
## 10. `GET /imports` — List Imports

### API

- **Operation ID:** `list_imports_imports_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source` | query | No | `string` or `null` | format: `uuid` | — |
| `status` | query | No | `string` or `null` | — | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="11_post_imports"></a>
## 11. `POST /imports` — Create Import

### API

- **Operation ID:** `create_import_imports_post`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

Idempotent: re-submitting the same file accepts nothing and reports zero.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_create_import_imports_post`](#schema-body_create_import_imports_post)

```json
{
  "source": "00000000-0000-4000-8000-000000000000",
  "project": "00000000-0000-4000-8000-000000000000",
  "manifest": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="12_get_imports_batch_uuid"></a>
## 12. `GET /imports/{batch_uuid}` — Get Import

### API

- **Operation ID:** `get_import_imports__batch_uuid__get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `batch_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ImportBatchOut`](#schema-importbatchout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "batch_uuid": "00000000-0000-4000-8000-000000000000",
  "file_name": "string",
  "file_hash": "string",
  "declared_rows": 1,
  "accepted_rows": 1,
  "rejected_rows": 1,
  "status": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "source_code": "string",
  "source_name": "string",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "imported_by_uuid": "00000000-0000-4000-8000-000000000000",
  "imported_by_name": "string"
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="13_get_imports_batch_uuid_errors"></a>
## 13. `GET /imports/{batch_uuid}/errors` — Import Errors

### API

- **Operation ID:** `import_errors_imports__batch_uuid__errors_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `batch_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="14_get_projects_project_uuid_collections"></a>
## 14. `GET /projects/{project_uuid}/collections` — List Collections

### API

- **Operation ID:** `list_collections_projects__project_uuid__collections_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="15_get_collections_collection_uuid"></a>
## 15. `GET /collections/{collection_uuid}` — Get Collection

### API

- **Operation ID:** `get_collection_collections__collection_uuid__get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `collection_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`CollectionOut`](#schema-collectionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "collection_uuid": "00000000-0000-4000-8000-000000000000",
  "source_collection_ref": "string",
  "collected_on": "string",
  "declared_asset_count": 1,
  "mapped_asset_count": 1,
  "unaccounted": 1,
  "agent_ref": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "source_code": "string",
  "source_name": "string",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "site_label": "string",
  "batch_uuid": "00000000-0000-4000-8000-000000000000"
}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="16_get_collections_collection_uuid_assets"></a>
## 16. `GET /collections/{collection_uuid}/assets` — Collection Assets

### API

- **Operation ID:** `collection_assets_collections__collection_uuid__assets_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `collection_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CollectionAssetOut`](#schema-collectionassetout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "asset_uuid": "00000000-0000-4000-8000-000000000000",
    "source_asset_ref": "string",
    "asset_type": "string",
    "storage_ref": "string",
    "has_unmapped_subjects": true,
    "created_at": "2026-09-17T12:00:00Z",
    "subject_count": 1,
    "bystander_count": 1
  }
]
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="17_get_collections_collection_uuid_exceptions"></a>
## 17. `GET /collections/{collection_uuid}/exceptions` — Declared against mapped - the control that makes direct collection workable

### API

- **Operation ID:** `collection_exceptions_collections__collection_uuid__exceptions_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

The failure mode is not a rejected file.

It is 500 declared and 480 mapped, with 20 sitting in an unlawful state
nobody sees. This is the endpoint that surfaces those 20.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `collection_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="18_get_assets_asset_uuid"></a>
## 18. `GET /assets/{asset_uuid}` — Get Asset

### API

- **Operation ID:** `get_asset_assets__asset_uuid__get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `asset_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{}
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

<a id="19_get_assets_asset_uuid_subjects"></a>
## 19. `GET /assets/{asset_uuid}/subjects` — One row per subject, bystanders included

### API

- **Operation ID:** `asset_subjects_assets__asset_uuid__subjects_get`
- **Access:** Role-controlled `exchange` operation. See [`../../roles/README.md`](../../roles/README.md).

Includes bystanders with a null consent id.

Multi-subject capture includes people in frame who never consented. If the
row cannot exist, a redact-before-release rule cannot be enforced against
someone the system does not know is there (INV-12).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `asset_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {}
]
```

**Example `422` `application/json` response:**

```json
{
  "detail": [
    {
      "loc": [
        "…"
      ],
      "msg": "string",
      "type": "string",
      "input": "string",
      "ctx": {}
    }
  ]
}
```

# Referenced schemas

<a id="schema-body_create_import_imports_post"></a>
#### `Body_create_import_imports_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source` | `string` | Yes | format: `uuid` | — |
| `project` | `string` | Yes | format: `uuid` | — |
| `manifest` | `string` | Yes | — | — |

<a id="schema-body_validate_import_imports_validate_post"></a>
#### `Body_validate_import_imports_validate_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source` | `string` | Yes | format: `uuid` | — |
| `manifest` | `string` | Yes | — | — |
| `project` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-collectionout"></a>
#### `CollectionOut`

One collection, in full.

Declared rather than returned as a bare dict because the scoped query has to
select `collection_id` for its follow-up lookups, and an internal surrogate
key has no business on the wire.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `collection_uuid` | `string` | Yes | format: `uuid` | — |
| `source_collection_ref` | `string` | Yes | — | — |
| `collected_on` | `object` | Yes | — | — |
| `declared_asset_count` | `integer` | Yes | — | — |
| `mapped_asset_count` | `integer` | Yes | — | — |
| `unaccounted` | `integer` | Yes | — | — |
| `agent_ref` | `string` or `null` | No | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `source_uuid` | `string` | Yes | format: `uuid` | — |
| `source_code` | `string` | Yes | — | — |
| `source_name` | `string` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `site_uuid` | `string` or `null` | No | format: `uuid` | — |
| `site_label` | `string` or `null` | No | — | — |
| `batch_uuid` | `string` | Yes | format: `uuid` | — |

<a id="schema-exportout"></a>
#### `ExportOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `export_uuid` | `string` | Yes | format: `uuid` | — |
| `export_type` | `string` | Yes | — | — |
| `exported_at` | `string` | Yes | format: `date-time` | — |
| `row_count` | `integer` | Yes | — | — |
| `file_hash` | `string` | Yes | — | — |
| `line_count` | `integer` or `null` | No | — | — |
| `site_uuid` | `string` or `null` | No | format: `uuid` | — |
| `site_label` | `string` or `null` | No | — | — |
| `exported_by_name` | `string` or `null` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-importbatchout"></a>
#### `ImportBatchOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `batch_uuid` | `string` | Yes | format: `uuid` | — |
| `file_name` | `string` | Yes | — | — |
| `file_hash` | `string` | Yes | — | — |
| `declared_rows` | `integer` | Yes | — | — |
| `accepted_rows` | `integer` | Yes | — | — |
| `rejected_rows` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `source_uuid` | `string` | Yes | format: `uuid` | — |
| `source_code` | `string` | Yes | — | — |
| `source_name` | `string` | Yes | — | — |
| `project_uuid` | `string` or `null` | No | format: `uuid` | — |
| `project_name` | `string` or `null` | No | — | — |
| `imported_by_uuid` | `string` | Yes | format: `uuid` | — |
| `imported_by_name` | `string` | Yes | — | — |

<a id="schema-page_collectionlistrow"></a>
#### `Page_CollectionListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`CollectionListRow`](#schema-collectionlistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_exportlistrow"></a>
#### `Page_ExportListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ExportListRow`](#schema-exportlistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-collectionlistrow"></a>
#### `CollectionListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `collection_uuid` | `string` | Yes | format: `uuid` | — |
| `source_collection_ref` | `string` | Yes | — | — |
| `collected_on` | `object` | Yes | — | — |
| `declared_asset_count` | `integer` | Yes | — | — |
| `mapped_asset_count` | `integer` | Yes | — | — |
| `unaccounted` | `integer` | Yes | — | — |
| `agent_ref` | `string` or `null` | No | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `source_uuid` | `string` | Yes | format: `uuid` | — |
| `source_code` | `string` | Yes | — | — |
| `source_name` | `string` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `site_uuid` | `string` or `null` | No | format: `uuid` | — |
| `site_label` | `string` or `null` | No | — | — |

<a id="schema-exportlistrow"></a>
#### `ExportListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `export_uuid` | `string` | Yes | format: `uuid` | — |
| `export_type` | `string` | Yes | — | — |
| `exported_at` | `string` | Yes | format: `date-time` | — |
| `row_count` | `integer` | Yes | — | — |
| `file_hash` | `string` | Yes | — | — |
| `line_count` | `integer` or `null` | No | — | — |
| `site_uuid` | `string` or `null` | No | format: `uuid` | — |
| `site_label` | `string` or `null` | No | — | — |
| `exported_by_name` | `string` or `null` | No | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
