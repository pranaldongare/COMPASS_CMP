# Cross-Border Transfers API

Generated from `backend/api/openapi.json`. **3 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /restricted-countries`](#1_get_restricted_countries)
2. [`POST /restricted-countries`](#2_post_restricted_countries)
3. [`POST /restricted-countries/{country_uuid}/lift`](#3_post_restricted_countries_country_uuid_lift)

<a id="1_get_restricted_countries"></a>
## 1. `GET /restricted-countries` — The restricted list

### API

- **Operation ID:** `list_restrictions_restricted_countries_get`
- **Access:** Role-controlled `cross-border transfers` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `active` | query | No | `boolean` | default: `True` | Only restrictions in force |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`RestrictionOut`](#schema-restrictionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "country_uuid": "00000000-0000-4000-8000-000000000000",
    "country_code": "string",
    "notification_ref": "string",
    "listed_at": "2026-09-17T12:00:00Z",
    "listed_by_name": "string",
    "lifted_at": "2026-09-17T12:00:00Z",
    "lifted_by_name": "string"
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

<a id="2_post_restricted_countries"></a>
## 2. `POST /restricted-countries` — Restrict transfers to a country

### API

- **Operation ID:** `restrict_restricted_countries_post`
- **Access:** Role-controlled `cross-border transfers` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RestrictionIn`](#schema-restrictionin)

```json
{
  "country_code": "string",
  "notification_ref": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`RestrictionOut`](#schema-restrictionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "country_uuid": "00000000-0000-4000-8000-000000000000",
  "country_code": "string",
  "notification_ref": "string",
  "listed_at": "2026-09-17T12:00:00Z",
  "listed_by_name": "string",
  "lifted_at": "2026-09-17T12:00:00Z",
  "lifted_by_name": "string"
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

<a id="3_post_restricted_countries_country_uuid_lift"></a>
## 3. `POST /restricted-countries/{country_uuid}/lift` — Lift a restriction

### API

- **Operation ID:** `lift_restricted_countries__country_uuid__lift_post`
- **Access:** Role-controlled `cross-border transfers` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `country_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RestrictionOut`](#schema-restrictionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "country_uuid": "00000000-0000-4000-8000-000000000000",
  "country_code": "string",
  "notification_ref": "string",
  "listed_at": "2026-09-17T12:00:00Z",
  "listed_by_name": "string",
  "lifted_at": "2026-09-17T12:00:00Z",
  "lifted_by_name": "string"
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

# Referenced schemas

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-restrictionin"></a>
#### `RestrictionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `country_code` | `string` | Yes | min length: `2`; max length: `2`; pattern: `^[A-Za-z]{2}$` | ISO 3166-1 alpha-2 country code, e.g. IN |
| `notification_ref` | `string` | Yes | min length: `1`; max length: `500` | — |

<a id="schema-restrictionout"></a>
#### `RestrictionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `country_uuid` | `string` | Yes | format: `uuid` | — |
| `country_code` | `string` | Yes | — | — |
| `notification_ref` | `string` | Yes | — | — |
| `listed_at` | `string` | Yes | format: `date-time` | — |
| `listed_by_name` | `string` or `null` | Yes | — | — |
| `lifted_at` | `string` or `null` | Yes | format: `date-time` | — |
| `lifted_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
