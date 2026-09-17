# System API

Generated from `cmp_backend/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /health`](#1_get_health)
2. [`GET /ready`](#2_get_ready)
3. [`GET /meta/version`](#3_get_meta_version)
4. [`GET /meta/enums`](#4_get_meta_enums)
5. [`GET /meta/data-categories`](#5_get_meta_data_categories)

<a id="1_get_health"></a>
## 1. `GET /health` — Liveness

### API

- **Operation ID:** `health_health_get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Process is up. No dependency is consulted - see the module docstring.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Health`](#schema-health) |

**Example `200` `application/json` response:**

```json
{
  "status": "string",
  "service": "string",
  "version": "string"
}
```

<a id="2_get_ready"></a>
## 2. `GET /ready` — Readiness

### API

- **Operation ID:** `ready_ready_get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Database reachable, migrations current, Redis reachable.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Ready`](#schema-ready) |

**Example `200` `application/json` response:**

```json
{
  "status": "string",
  "checks": [
    {
      "name": "string",
      "ok": true,
      "detail": "…"
    }
  ],
  "schema_version": "string",
  "schema_expected": "string"
}
```

<a id="3_get_meta_version"></a>
## 3. `GET /meta/version` — Version

### API

- **Operation ID:** `version_meta_version_get`
- **Access:** Role-controlled `system` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Version`](#schema-version) |

**Example `200` `application/json` response:**

```json
{
  "service": "string",
  "version": "string",
  "environment": "string",
  "schema_version": "string"
}
```

<a id="4_get_meta_enums"></a>
## 4. `GET /meta/enums` — All enum values for dropdowns

### API

- **Operation ID:** `meta_enums_meta_enums_get`
- **Access:** Role-controlled `system` operation. See [`../../roles/README.md`](../../roles/README.md).

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
{}
```

<a id="5_get_meta_data_categories"></a>
## 5. `GET /meta/data-categories` — Controlled vocabulary

### API

- **Operation ID:** `meta_data_categories_meta_data_categories_get`
- **Access:** Role-controlled `system` operation. See [`../../roles/README.md`](../../roles/README.md).

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
{}
```

# Referenced schemas

<a id="schema-health"></a>
#### `Health`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `status` | `string` | Yes | — | — |
| `service` | `string` | Yes | — | — |
| `version` | `string` | Yes | — | — |

<a id="schema-ready"></a>
#### `Ready`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `status` | `string` | Yes | — | — |
| `checks` | array of [`ReadyCheck`](#schema-readycheck) | Yes | — | — |
| `schema_version` | `string` or `null` | No | — | — |
| `schema_expected` | `string` or `null` | No | — | — |

<a id="schema-version"></a>
#### `Version`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `service` | `string` | Yes | — | — |
| `version` | `string` | Yes | — | — |
| `environment` | `string` | Yes | — | — |
| `schema_version` | `string` or `null` | No | — | — |

<a id="schema-readycheck"></a>
#### `ReadyCheck`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` | Yes | — | — |
| `ok` | `boolean` | Yes | — | — |
| `detail` | `string` or `null` | No | — | — |
