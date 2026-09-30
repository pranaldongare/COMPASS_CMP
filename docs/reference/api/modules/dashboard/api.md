# Dashboard API

Generated from `backend/api/openapi.json`. **3 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /dashboard`](#1_get_dashboard)
2. [`GET /notifications`](#2_get_notifications)
3. [`POST /notifications/{log_uuid}/resend`](#3_post_notifications_log_uuid_resend)

<a id="1_get_dashboard"></a>
## 1. `GET /dashboard` — Role-aware aggregate

### API

- **Operation ID:** `dashboard_dashboard_get`
- **Access:** Authenticated caller; content is filtered for the active role.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Dashboard`](#schema-dashboard) |

**Example `200` `application/json` response:**

```json
{
  "role": "string",
  "counts": {},
  "queues": [
    {}
  ],
  "recent": [
    {}
  ],
  "attention": [
    {
      "key": "string",
      "label": "string",
      "count": 1,
      "severity": "string",
      "href": "string"
    }
  ],
  "breaches": [
    {
      "breach_uuid": "00000000-0000-4000-8000-000000000000",
      "reference": "string",
      "title": "string",
      "status": "string",
      "detected_at": "2026-09-17T12:00:00Z",
      "location": "…",
      "determination": "string",
      "obligations": [
        "…"
      ]
    }
  ]
}
```

<a id="2_get_notifications"></a>
## 2. `GET /notifications` — Notifications

### API

- **Operation ID:** `notifications_notifications_get`
- **Access:** Authenticated caller; content is filtered for the active role.

Derived from the audit trail rather than a separate table.

There is no notifications table among the 22, and deriving the feed means it
can never disagree with the record it is describing.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `limit` | query | No | `integer` | minimum: `1`; maximum: `100`; default: `50` | — |

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

<a id="3_post_notifications_log_uuid_resend"></a>
## 3. `POST /notifications/{log_uuid}/resend` — Resend

### API

- **Operation ID:** `resend_notifications__log_uuid__resend_post`
- **Access:** Authenticated caller; content is filtered for the active role.

Re-deliver a failed notification.

Restricted to DPO and DCO: re-sending a consent receipt puts a message in
somebody's inbox, and that is not an action a general user should be able to
trigger for an arbitrary event.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `log_uuid` | path | Yes | `string` | format: `uuid` | — |

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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-dashboard"></a>
#### `Dashboard`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `role` | `string` | Yes | — | — |
| `counts` | `object` | Yes | — | — |
| `queues` | array of `object` | Yes | — | — |
| `recent` | array of `object` | Yes | — | — |
| `attention` | array of [`AttentionRow`](#schema-attentionrow) | No | — | — |
| `breaches` | array of [`BreachSummaryOut`](#schema-breachsummaryout) | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-attentionrow"></a>
#### `AttentionRow`

One thing that needs this person today: a count, how urgent it is,
and where to act on it. Rows with nothing to count are not sent.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `count` | `integer` | Yes | — | — |
| `severity` | `string` | Yes | — | — |
| `href` | `string` | Yes | — | — |

<a id="schema-breachsummaryout"></a>
#### `BreachSummaryOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `breach_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `determination` | `string` | Yes | — | — |
| `obligations` | array of [`BreachDutyOut`](#schema-breachdutyout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-breachlocationout"></a>
#### `BreachLocationOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `processor_name` | `string` or `null` | Yes | — | — |
| `source_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `source_name` | `string` or `null` | Yes | — | — |
| `detail` | `string` or `null` | Yes | — | — |

<a id="schema-breachdutyout"></a>
#### `BreachDutyOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `obligation_uuid` | `string` | Yes | format: `uuid` | — |
| `duty` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `state` | `string` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `anchored_at` | `string` or `null` | Yes | format: `date-time` | — |
| `completed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | Yes | — | — |
| `extended_until` | `string` or `null` | Yes | format: `date-time` | — |
| `extension_requested_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`BreachClockOut`](#schema-breachclockout) | Yes | — | — |
| `events` | array of [`BreachDutyEventOut`](#schema-breachdutyeventout) | Yes | — | — |

<a id="schema-breachclockout"></a>
#### `BreachClockOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `without_delay` | `boolean` | Yes | — | — |
| `seconds_remaining` | `integer` or `null` | Yes | — | — |
| `overdue` | `boolean` | Yes | — | — |
| `seconds_elapsed` | `integer` or `null` | Yes | — | — |
| `target_at` | `string` or `null` | Yes | format: `date-time` | — |
| `past_target` | `boolean` | Yes | — | — |

<a id="schema-breachdutyeventout"></a>
#### `BreachDutyEventOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `event_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `occurred_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `requested_at` | `string` or `null` | Yes | format: `date-time` | — |
| `determination_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `recorded_by_name` | `string` or `null` | Yes | — | — |
