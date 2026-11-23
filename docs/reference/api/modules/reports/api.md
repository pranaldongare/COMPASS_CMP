# Reports API

Generated from `backend/api/openapi.json`. **9 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /reports`](#1_get_reports)
2. [`POST /reports`](#2_post_reports)
3. [`GET /reports/schedules`](#3_get_reports_schedules)
4. [`POST /reports/schedules`](#4_post_reports_schedules)
5. [`PATCH /reports/schedules/{schedule_uuid}`](#5_patch_reports_schedules_schedule_uuid)
6. [`DELETE /reports/schedules/{schedule_uuid}`](#6_delete_reports_schedules_schedule_uuid)
7. [`GET /reports/{report_uuid}`](#7_get_reports_report_uuid)
8. [`DELETE /reports/{report_uuid}`](#8_delete_reports_report_uuid)
9. [`GET /reports/{report_uuid}/file`](#9_get_reports_report_uuid_file)

<a id="1_get_reports"></a>
## 1. `GET /reports` — The reports this reader may see

### API

- **Operation ID:** `list_reports_reports_get`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ReportOut`](#schema-reportout) |

**Example `200` `application/json` response:**

```json
[
  {
    "report_uuid": "00000000-0000-4000-8000-000000000000",
    "kind": "string",
    "title": "string",
    "params": {},
    "office": "string",
    "format": "string",
    "status": "string",
    "file_sha256": "string",
    "file_bytes": 1,
    "error": "string",
    "requested_by_name": "string",
    "requested_role": "string",
    "schedule_uuid": "00000000-0000-4000-8000-000000000000",
    "created_at": "2026-09-17T12:00:00Z",
    "ready_at": "2026-09-17T12:00:00Z"
  }
]
```

<a id="2_post_reports"></a>
## 2. `POST /reports` — Ask for a report

### API

- **Operation ID:** `create_report_reports_post`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ReportIn`](#schema-reportin)

```json
{
  "kind": "string",
  "format": "string",
  "period": "string",
  "start": "2026-09-17",
  "end": "2026-09-17",
  "office": "string",
  "audit": "string",
  "entity_type": "string",
  "entity_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `202` | Successful Response | `application/json` | [`ReportOut`](#schema-reportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `202` `application/json` response:**

```json
{
  "report_uuid": "00000000-0000-4000-8000-000000000000",
  "kind": "string",
  "title": "string",
  "params": {},
  "office": "string",
  "format": "string",
  "status": "string",
  "file_sha256": "string",
  "file_bytes": 1,
  "error": "string",
  "requested_by_name": "string",
  "requested_role": "string",
  "schedule_uuid": "00000000-0000-4000-8000-000000000000",
  "created_at": "2026-09-17T12:00:00Z",
  "ready_at": "2026-09-17T12:00:00Z"
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

<a id="3_get_reports_schedules"></a>
## 3. `GET /reports/schedules` — Report schedules

### API

- **Operation ID:** `list_schedules_reports_schedules_get`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ScheduleOut`](#schema-scheduleout) |

**Example `200` `application/json` response:**

```json
[
  {
    "schedule_uuid": "00000000-0000-4000-8000-000000000000",
    "kind": "string",
    "title": "string",
    "params": {},
    "format": "string",
    "cadence": "string",
    "recipient_roles": [
      "string"
    ],
    "office": "string",
    "active": true,
    "created_by_name": "string",
    "created_role": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "last_run_at": "2026-09-17T12:00:00Z",
    "next_run_at": "2026-09-17T12:00:00Z"
  }
]
```

<a id="4_post_reports_schedules"></a>
## 4. `POST /reports/schedules` — Make a report on a cadence and mail it

### API

- **Operation ID:** `create_schedule_reports_schedules_post`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ScheduleIn`](#schema-schedulein)

```json
{
  "kind": "string",
  "format": "string",
  "cadence": "string",
  "recipient_roles": [
    "string"
  ],
  "office": "string",
  "audit": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`ScheduleOut`](#schema-scheduleout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "schedule_uuid": "00000000-0000-4000-8000-000000000000",
  "kind": "string",
  "title": "string",
  "params": {},
  "format": "string",
  "cadence": "string",
  "recipient_roles": [
    "string"
  ],
  "office": "string",
  "active": true,
  "created_by_name": "string",
  "created_role": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "last_run_at": "2026-09-17T12:00:00Z",
  "next_run_at": "2026-09-17T12:00:00Z"
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

<a id="5_patch_reports_schedules_schedule_uuid"></a>
## 5. `PATCH /reports/schedules/{schedule_uuid}` — Pause or resume a schedule

### API

- **Operation ID:** `change_schedule_reports_schedules__schedule_uuid__patch`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `schedule_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ScheduleChangeIn`](#schema-schedulechangein)

```json
{
  "active": true
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ScheduleOut`](#schema-scheduleout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "schedule_uuid": "00000000-0000-4000-8000-000000000000",
  "kind": "string",
  "title": "string",
  "params": {},
  "format": "string",
  "cadence": "string",
  "recipient_roles": [
    "string"
  ],
  "office": "string",
  "active": true,
  "created_by_name": "string",
  "created_role": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "last_run_at": "2026-09-17T12:00:00Z",
  "next_run_at": "2026-09-17T12:00:00Z"
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

<a id="6_delete_reports_schedules_schedule_uuid"></a>
## 6. `DELETE /reports/schedules/{schedule_uuid}` — Remove a schedule

### API

- **Operation ID:** `remove_schedule_reports_schedules__schedule_uuid__delete`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `schedule_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string"
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

<a id="7_get_reports_report_uuid"></a>
## 7. `GET /reports/{report_uuid}` — One report

### API

- **Operation ID:** `get_report_reports__report_uuid__get`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ReportOut`](#schema-reportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "report_uuid": "00000000-0000-4000-8000-000000000000",
  "kind": "string",
  "title": "string",
  "params": {},
  "office": "string",
  "format": "string",
  "status": "string",
  "file_sha256": "string",
  "file_bytes": 1,
  "error": "string",
  "requested_by_name": "string",
  "requested_role": "string",
  "schedule_uuid": "00000000-0000-4000-8000-000000000000",
  "created_at": "2026-09-17T12:00:00Z",
  "ready_at": "2026-09-17T12:00:00Z"
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

<a id="8_delete_reports_report_uuid"></a>
## 8. `DELETE /reports/{report_uuid}` — Delete a report

### API

- **Operation ID:** `delete_report_reports__report_uuid__delete`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string"
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

<a id="9_get_reports_report_uuid_file"></a>
## 9. `GET /reports/{report_uuid}/file` — Download a report, as it was made

### API

- **Operation ID:** `download_report_reports__report_uuid__file_get`
- **Access:** Role-controlled `reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-reportin"></a>
#### `ReportIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | max length: `48` | — |
| `format` | `string` | Yes | pattern: `^(pdf|xlsx|csv)$` | — |
| `period` | `string` or `null` | No | max length: `24` | — |
| `start` | `string` or `null` | No | format: `date` | — |
| `end` | `string` or `null` | No | format: `date` | — |
| `office` | `string` or `null` | No | pattern: `^(rnd|hr)$` | — |
| `audit` | `string` or `null` | No | max length: `32` | — |
| `entity_type` | `string` or `null` | No | pattern: `^(rights_request|breach)$` | — |
| `entity_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-reportout"></a>
#### `ReportOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `report_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `params` | `object` | Yes | — | — |
| `office` | `string` or `null` | Yes | — | — |
| `format` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `file_sha256` | `string` or `null` | Yes | — | — |
| `file_bytes` | `integer` or `null` | Yes | — | — |
| `error` | `string` or `null` | Yes | — | — |
| `requested_by_name` | `string` or `null` | Yes | — | — |
| `requested_role` | `string` | Yes | — | — |
| `schedule_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `ready_at` | `string` or `null` | Yes | format: `date-time` | — |

<a id="schema-schedulechangein"></a>
#### `ScheduleChangeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `active` | `boolean` | Yes | — | — |

<a id="schema-schedulein"></a>
#### `ScheduleIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | max length: `48` | — |
| `format` | `string` | Yes | pattern: `^(pdf|xlsx|csv)$` | — |
| `cadence` | `string` | Yes | pattern: `^(weekly|monthly|quarterly)$` | — |
| `recipient_roles` | array of `string` | Yes | — | — |
| `office` | `string` or `null` | No | pattern: `^(rnd|hr)$` | — |
| `audit` | `string` or `null` | No | max length: `32` | — |

<a id="schema-scheduleout"></a>
#### `ScheduleOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `schedule_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `params` | `object` | Yes | — | — |
| `format` | `string` | Yes | — | — |
| `cadence` | `string` | Yes | — | — |
| `recipient_roles` | array of `string` | Yes | — | — |
| `office` | `string` or `null` | Yes | — | — |
| `active` | `boolean` | Yes | — | — |
| `created_by_name` | `string` or `null` | Yes | — | — |
| `created_role` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `last_run_at` | `string` or `null` | Yes | format: `date-time` | — |
| `next_run_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
