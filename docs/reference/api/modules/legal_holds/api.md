# Legal Holds API

Generated from `backend/api/openapi.json`. **3 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /legal-holds`](#1_get_legal_holds)
2. [`POST /legal-holds`](#2_post_legal_holds)
3. [`POST /legal-holds/{hold_uuid}/release`](#3_post_legal_holds_hold_uuid_release)

<a id="1_get_legal_holds"></a>
## 1. `GET /legal-holds` — Holds, active first

### API

- **Operation ID:** `list_holds_legal_holds_get`
- **Access:** Role-controlled `legal holds` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `active` | query | No | `boolean` | default: `True` | Only holds not yet released |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`LegalHoldOut`](#schema-legalholdout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "hold_uuid": "00000000-0000-4000-8000-000000000000",
    "asset_uuid": "00000000-0000-4000-8000-000000000000",
    "source_asset_ref": "string",
    "subject_uuid": "00000000-0000-4000-8000-000000000000",
    "subject_name": "string",
    "reason": "string",
    "placed_at": "2026-09-17T12:00:00Z",
    "placed_by_name": "string",
    "released_at": "2026-09-17T12:00:00Z",
    "released_by_name": "string"
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

<a id="2_post_legal_holds"></a>
## 2. `POST /legal-holds` — Stop erasure of an asset or a person

### API

- **Operation ID:** `place_hold_legal_holds_post`
- **Access:** Role-controlled `legal holds` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`LegalHoldIn`](#schema-legalholdin)

```json
{
  "asset_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`LegalHoldOut`](#schema-legalholdout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "hold_uuid": "00000000-0000-4000-8000-000000000000",
  "asset_uuid": "00000000-0000-4000-8000-000000000000",
  "source_asset_ref": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "reason": "string",
  "placed_at": "2026-09-17T12:00:00Z",
  "placed_by_name": "string",
  "released_at": "2026-09-17T12:00:00Z",
  "released_by_name": "string"
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

<a id="3_post_legal_holds_hold_uuid_release"></a>
## 3. `POST /legal-holds/{hold_uuid}/release` — Release a hold; what it stopped carries on

### API

- **Operation ID:** `release_hold_legal_holds__hold_uuid__release_post`
- **Access:** Role-controlled `legal holds` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `hold_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`LegalHoldOut`](#schema-legalholdout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "hold_uuid": "00000000-0000-4000-8000-000000000000",
  "asset_uuid": "00000000-0000-4000-8000-000000000000",
  "source_asset_ref": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "reason": "string",
  "placed_at": "2026-09-17T12:00:00Z",
  "placed_by_name": "string",
  "released_at": "2026-09-17T12:00:00Z",
  "released_by_name": "string"
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

<a id="schema-legalholdin"></a>
#### `LegalHoldIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `asset_uuid` | `string` or `null` | No | format: `uuid` | — |
| `subject_uuid` | `string` or `null` | No | format: `uuid` | — |
| `reason` | `string` | Yes | min length: `1`; max length: `2000` | — |

<a id="schema-legalholdout"></a>
#### `LegalHoldOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `hold_uuid` | `string` | Yes | format: `uuid` | — |
| `asset_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `source_asset_ref` | `string` or `null` | Yes | — | — |
| `subject_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `subject_name` | `string` or `null` | Yes | — | — |
| `reason` | `string` | Yes | — | — |
| `placed_at` | `string` | Yes | format: `date-time` | — |
| `placed_by_name` | `string` or `null` | Yes | — | — |
| `released_at` | `string` or `null` | Yes | format: `date-time` | — |
| `released_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
