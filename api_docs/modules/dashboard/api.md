# Dashboard API

Generated from `cmp_backend/openapi.json`. **3 operations.**

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

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
