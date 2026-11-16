# Datavault API

Generated from `backend/api/openapi.json`. **7 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /datavault-connection`](#1_get_datavault_connection)
2. [`PUT /datavault-connection`](#2_put_datavault_connection)
3. [`GET /requests/{request_uuid}/datavault`](#3_get_requests_request_uuid_datavault)
4. [`POST /requests/{request_uuid}/datavault/check`](#4_post_requests_request_uuid_datavault_check)
5. [`POST /requests/{request_uuid}/datavault/erase`](#5_post_requests_request_uuid_datavault_erase)
6. [`POST /requests/{request_uuid}/datavault/erase/status`](#6_post_requests_request_uuid_datavault_erase_status)
7. [`GET /tickets/{holder_uuid}/datavault`](#7_get_tickets_holder_uuid_datavault)

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
  "erasure_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
  "id_format": "numeric",
  "consent_changes": false,
  "consent_changes_waiting": 0,
  "consent_changes_last_delivered_at": "2026-09-17T12:00:00Z",
  "consent_changes_last_failure": "string",
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
  "erasure_url": "string",
  "api_key": "string",
  "clear_api_key": false,
  "api_key_header": "string",
  "enabled": false,
  "id_format": "string",
  "consent_changes": false
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
  "erasure_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
  "id_format": "numeric",
  "consent_changes": false,
  "consent_changes_waiting": 0,
  "consent_changes_last_delivered_at": "2026-09-17T12:00:00Z",
  "consent_changes_last_failure": "string",
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
      "datapath": "…",
      "in_scope": true,
      "erasure_status": "…",
      "erasure_status_at": "…",
      "erasure_completed_at": "…",
      "erasure_reason": "…"
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
  },
  "erasure": {
    "may_erase": true,
    "why_not": "…",
    "to_send": 1,
    "left_out": 1,
    "open": 1,
    "may_check_status": true,
    "counts": {},
    "last_asked_at": "…",
    "last_failure": "…",
    "last_failure_said": "…"
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
      "datapath": "…",
      "in_scope": true,
      "erasure_status": "…",
      "erasure_status_at": "…",
      "erasure_completed_at": "…",
      "erasure_reason": "…"
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
  },
  "erasure": {
    "may_erase": true,
    "why_not": "…",
    "to_send": 1,
    "left_out": 1,
    "open": 1,
    "may_check_status": true,
    "counts": {},
    "last_asked_at": "…",
    "last_failure": "…",
    "last_failure_said": "…"
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

<a id="5_post_requests_request_uuid_datavault_erase"></a>
## 5. `POST /requests/{request_uuid}/datavault/erase` — Erase in DataVault: tell it to erase the assets its last check listed

### API

- **Operation ID:** `erase_in_datavault_requests__request_uuid__datavault_erase_post`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

On an erasure request that has been started, with a check on record and
no legal hold on the person. The instruction is saved before it is sent,
so one that is never answered can be asked about again. Nothing about
this runs by itself.

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
      "datapath": "…",
      "in_scope": true,
      "erasure_status": "…",
      "erasure_status_at": "…",
      "erasure_completed_at": "…",
      "erasure_reason": "…"
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
  },
  "erasure": {
    "may_erase": true,
    "why_not": "…",
    "to_send": 1,
    "left_out": 1,
    "open": 1,
    "may_check_status": true,
    "counts": {},
    "last_asked_at": "…",
    "last_failure": "…",
    "last_failure_said": "…"
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

<a id="6_post_requests_request_uuid_datavault_erase_status"></a>
## 6. `POST /requests/{request_uuid}/datavault/erase/status` — Check status: ask DataVault how far each asset it was told to erase has got

### API

- **Operation ID:** `erasure_status_requests__request_uuid__datavault_erase_status_post`
- **Access:** Role-controlled `datavault` operation. See [`../../roles/README.md`](../../roles/README.md).

Repeats every instruction with an asset still pending or unanswered:
the same `erasure_id` and the same assets, which starts nothing new.

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
      "datapath": "…",
      "in_scope": true,
      "erasure_status": "…",
      "erasure_status_at": "…",
      "erasure_completed_at": "…",
      "erasure_reason": "…"
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
  },
  "erasure": {
    "may_erase": true,
    "why_not": "…",
    "to_send": 1,
    "left_out": 1,
    "open": 1,
    "may_check_status": true,
    "counts": {},
    "last_asked_at": "…",
    "last_failure": "…",
    "last_failure_said": "…"
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

<a id="7_get_tickets_holder_uuid_datavault"></a>
## 7. `GET /tickets/{holder_uuid}/datavault` — On a DCO Admin's ticket: the assets DataVault listed for their project

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
      "datapath": "…",
      "in_scope": true,
      "erasure_status": "…",
      "erasure_status_at": "…",
      "erasure_completed_at": "…",
      "erasure_reason": "…"
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
| `erasure_url` | `string` or `null` | No | max length: `500` | — |
| `api_key` | `string` or `null` | No | min length: `1`; max length: `4000` | — |
| `clear_api_key` | `boolean` | No | default: `False` | — |
| `api_key_header` | `string` or `null` | No | min length: `1`; max length: `64` | — |
| `enabled` | `boolean` | No | default: `False` | — |
| `id_format` | `string` or `null` | No | max length: `16` | — |
| `consent_changes` | `boolean` | No | default: `False` | — |

<a id="schema-connectionout"></a>
#### `ConnectionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `base_url` | `string` or `null` | Yes | — | — |
| `erasure_url` | `string` or `null` | No | — | — |
| `api_key_set` | `boolean` | Yes | — | — |
| `api_key_header` | `string` | Yes | — | — |
| `enabled` | `boolean` | Yes | — | — |
| `id_format` | `string` | No | default: `numeric` | — |
| `consent_changes` | `boolean` | No | default: `False` | — |
| `consent_changes_waiting` | `integer` | No | default: `0` | — |
| `consent_changes_last_delivered_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_changes_last_failure` | `string` or `null` | No | — | — |
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
| `erasure` | [`ErasureOut`](#schema-erasureout) or `null` | No | — | — |

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
| `in_scope` | `boolean` | No | default: `True` | — |
| `erasure_status` | `string` or `null` | No | — | — |
| `erasure_status_at` | `string` or `null` | No | format: `date-time` | — |
| `erasure_completed_at` | `string` or `null` | No | format: `date-time` | — |
| `erasure_reason` | `string` or `null` | No | — | — |

<a id="schema-erasureout"></a>
#### `ErasureOut`

What may be done about erasing in DataVault now, on an erasure request.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `may_erase` | `boolean` | Yes | — | — |
| `why_not` | `string` or `null` | Yes | — | — |
| `to_send` | `integer` | Yes | — | — |
| `left_out` | `integer` | Yes | — | — |
| `open` | `integer` | Yes | — | — |
| `may_check_status` | `boolean` | Yes | — | — |
| `counts` | `object` | Yes | — | — |
| `last_asked_at` | `string` or `null` | Yes | format: `date-time` | — |
| `last_failure` | `string` or `null` | Yes | — | — |
| `last_failure_said` | `string` or `null` | Yes | — | — |
