# Portal Address API

Generated from `backend/api/openapi.json`. **2 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /portal-address`](#1_get_portal_address)
2. [`PUT /portal-address`](#2_put_portal_address)

<a id="1_get_portal_address"></a>
## 1. `GET /portal-address` — The address portal links start with

### API

- **Operation ID:** `get_portal_address_portal_address_get`
- **Access:** Role-controlled `portal address` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PortalAddressOut`](#schema-portaladdressout) |

**Example `200` `application/json` response:**

```json
{
  "portal_url": "string",
  "configured_url": "string",
  "in_use": "string",
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
}
```

<a id="2_put_portal_address"></a>
## 2. `PUT /portal-address` — Set the address portal links start with

### API

- **Operation ID:** `put_portal_address_portal_address_put`
- **Access:** Role-controlled `portal address` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PortalAddressIn`](#schema-portaladdressin)

```json
{
  "portal_url": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PortalAddressOut`](#schema-portaladdressout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "portal_url": "string",
  "configured_url": "string",
  "in_use": "string",
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
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

<a id="schema-portaladdressin"></a>
#### `PortalAddressIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `portal_url` | `string` or `null` | No | max length: `300` | — |

<a id="schema-portaladdressout"></a>
#### `PortalAddressOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `portal_url` | `string` or `null` | Yes | — | — |
| `configured_url` | `string` | Yes | — | — |
| `in_use` | `string` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
