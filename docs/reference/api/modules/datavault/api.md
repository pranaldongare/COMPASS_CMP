# Datavault API

Generated from `backend/api/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /datavault-connection`](#1_get_datavault_connection)
2. [`PUT /datavault-connection`](#2_put_datavault_connection)
3. [`GET /requests/{request_uuid}/datavault`](#3_get_requests_request_uuid_datavault)
4. [`POST /requests/{request_uuid}/datavault/check`](#4_post_requests_request_uuid_datavault_check)
5. [`GET /tickets/{holder_uuid}/datavault`](#5_get_tickets_holder_uuid_datavault)

<a id="1_get_datavault_connection"></a>
## 1. `GET /datavault-connection` — Where DataVault is reached, and whether it is on

### API

- **Operation ID:** `get_connection_datavault_connection_get`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ConnectionOut`](#schema-connectionout) |

**Example `200` `application/json` response:**

```json
{
  "base_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
}
```

<a id="2_put_datavault_connection"></a>
## 2. `PUT /datavault-connection` — Set DataVault's address, its key, and switch it on

### API

- **Operation ID:** `put_connection_datavault_connection_put`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ConnectionIn`](#schema-connectionin)

```json
{
  "base_url": "string",
  "api_key": "string",
  "clear_api_key": false,
  "api_key_header": "string",
  "enabled": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ConnectionOut`](#schema-connectionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "base_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
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

<a id="3_get_requests_request_uuid_datavault"></a>
## 3. `GET /requests/{request_uuid}/datavault` — What DataVault last said it holds of this request's person

### API

- **Operation ID:** `request_datavault_requests__request_uuid__datavault_get`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestDataVaultOut`](#schema-requestdatavaultout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "configured": true,
  "may_check": true,
  "why_not": "string",
  "answer": {
    "check_uuid": "00000000-0000-4000-8000-000000000000",
    "asked_at": "2026-09-17T12:00:00Z",
    "automatic": true,
    "asked_by_name": "…",
    "outcome": "string",
    "failure": "…",
    "failure_said": "…",
    "asset_count": 1
  },
  "assets": [
    {
      "asset_ref": "string",
      "consent_ref": "…",
      "project_ref": "…",
      "consent_uuid": "…",
      "consent_no": "…",
      "project_uuid": "…",
      "project_no": "…",
      "project_name": "…",
      "mid": "…",
      "datapath": "…"
    }
  ],
  "last_failure": {
    "check_uuid": "00000000-0000-4000-8000-000000000000",
    "asked_at": "2026-09-17T12:00:00Z",
    "automatic": true,
    "asked_by_name": "…",
    "outcome": "string",
    "failure": "…",
    "failure_said": "…",
    "asset_count": 1
  }
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

<a id="4_post_requests_request_uuid_datavault_check"></a>
## 4. `POST /requests/{request_uuid}/datavault/check` — Check in DataVault: ask it now what it holds of this request's person

### API

- **Operation ID:** `check_in_datavault_requests__request_uuid__datavault_check_post`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

One call to DataVault, made while the caller waits and recorded whether
or not it is answered. No transaction is open during the call.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestDataVaultOut`](#schema-requestdatavaultout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "configured": true,
  "may_check": true,
  "why_not": "string",
  "answer": {
    "check_uuid": "00000000-0000-4000-8000-000000000000",
    "asked_at": "2026-09-17T12:00:00Z",
    "automatic": true,
    "asked_by_name": "…",
    "outcome": "string",
    "failure": "…",
    "failure_said": "…",
    "asset_count": 1
  },
  "assets": [
    {
      "asset_ref": "string",
      "consent_ref": "…",
      "project_ref": "…",
      "consent_uuid": "…",
      "consent_no": "…",
      "project_uuid": "…",
      "project_no": "…",
      "project_name": "…",
      "mid": "…",
      "datapath": "…"
    }
  ],
  "last_failure": {
    "check_uuid": "00000000-0000-4000-8000-000000000000",
    "asked_at": "2026-09-17T12:00:00Z",
    "automatic": true,
    "asked_by_name": "…",
    "outcome": "string",
    "failure": "…",
    "failure_said": "…",
    "asset_count": 1
  }
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

<a id="5_get_tickets_holder_uuid_datavault"></a>
## 5. `GET /tickets/{holder_uuid}/datavault` — On a DCO Admin's ticket: the assets DataVault listed for their project

### API

- **Operation ID:** `ticket_datavault_tickets__holder_uuid__datavault_get`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

Bounded by the holder's own account, as every ticket route is: a ticket
addressed to somebody else, or one that is not a project's DCO Admin's,
answers with nothing listed.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TicketDataVaultOut`](#schema-ticketdatavaultout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "asked_at": "2026-09-17T12:00:00Z",
  "assets": [
    {
      "asset_ref": "string",
      "consent_ref": "…",
      "project_ref": "…",
      "consent_uuid": "…",
      "consent_no": "…",
      "project_uuid": "…",
      "project_no": "…",
      "project_name": "…",
      "mid": "…",
      "datapath": "…"
    }
  ]
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

<a id="schema-connectionin"></a>
#### `ConnectionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `base_url` | `string` or `null` | No | max length: `500` | — |
| `api_key` | `string` or `null` | No | min length: `1`; max length: `4000` | — |
| `clear_api_key` | `boolean` | No | default: `False` | — |
| `api_key_header` | `string` or `null` | No | min length: `1`; max length: `64` | — |
| `enabled` | `boolean` | No | default: `False` | — |

<a id="schema-connectionout"></a>
#### `ConnectionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `base_url` | `string` or `null` | Yes | — | — |
| `api_key_set` | `boolean` | Yes | — | — |
| `api_key_header` | `string` | Yes | — | — |
| `enabled` | `boolean` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-requestdatavaultout"></a>
#### `RequestDataVaultOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `configured` | `boolean` | Yes | — | — |
| `may_check` | `boolean` | Yes | — | — |
| `why_not` | `string` or `null` | Yes | — | — |
| `answer` | [`CheckOut`](#schema-checkout) or `null` | Yes | — | — |
| `assets` | array of [`HeldAssetOut`](#schema-heldassetout) | Yes | — | — |
| `last_failure` | [`CheckOut`](#schema-checkout) or `null` | Yes | — | — |

<a id="schema-ticketdatavaultout"></a>
#### `TicketDataVaultOut`

What DataVault listed for the project a DCO Admin's ticket is about.
`asked_at` null: not such a ticket, or DataVault has not answered yet.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `asked_at` | `string` or `null` | Yes | format: `date-time` | — |
| `assets` | array of [`HeldAssetOut`](#schema-heldassetout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-checkout"></a>
#### `CheckOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `check_uuid` | `string` | Yes | format: `uuid` | — |
| `asked_at` | `string` | Yes | format: `date-time` | — |
| `automatic` | `boolean` | Yes | — | — |
| `asked_by_name` | `string` or `null` | Yes | — | — |
| `outcome` | `string` | Yes | — | — |
| `failure` | `string` or `null` | Yes | — | — |
| `failure_said` | `string` or `null` | Yes | — | — |
| `asset_count` | `integer` | Yes | — | — |

<a id="schema-heldassetout"></a>
#### `HeldAssetOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `asset_ref` | `string` | Yes | — | — |
| `consent_ref` | `string` or `null` | Yes | — | — |
| `project_ref` | `string` or `null` | Yes | — | — |
| `consent_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `consent_no` | `integer` or `null` | Yes | — | — |
| `project_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `project_no` | `integer` or `null` | Yes | — | — |
| `project_name` | `string` or `null` | Yes | — | — |
| `mid` | `string` or `null` | Yes | — | — |
| `datapath` | `string` or `null` | Yes | — | — |
