# Retention API

Generated from `backend/api/openapi.json`. **13 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /retention/reviews`](#1_get_retention_reviews)
2. [`POST /retention/refresh`](#2_post_retention_refresh)
3. [`GET /retention/settings`](#3_get_retention_settings)
4. [`PUT /retention/settings`](#4_put_retention_settings)
5. [`GET /retention/reviews/{review_uuid}`](#5_get_retention_reviews_review_uuid)
6. [`POST /retention/reviews/{review_uuid}/actions/{action_uuid}/accept`](#6_post_retention_reviews_review_uuid_actions_action_uuid_accept)
7. [`POST /retention/reviews/{review_uuid}/actions/{action_uuid}/send-back`](#7_post_retention_reviews_review_uuid_actions_action_uuid_send_back)
8. [`POST /retention/reviews/{review_uuid}/actions/{action_uuid}/not-needed`](#8_post_retention_reviews_review_uuid_actions_action_uuid_not_needed)
9. [`POST /retention/reviews/{review_uuid}/close`](#9_post_retention_reviews_review_uuid_close)
10. [`GET /retention/reviews/{review_uuid}/certificate`](#10_get_retention_reviews_review_uuid_certificate)
11. [`GET /retention-actions`](#11_get_retention_actions)
12. [`GET /retention-actions/{action_uuid}`](#12_get_retention_actions_action_uuid)
13. [`POST /retention-actions/{action_uuid}/answer`](#13_post_retention_actions_action_uuid_answer)

<a id="1_get_retention_reviews"></a>
## 1. `GET /retention/reviews` — The retention reviews

### API

- **Operation ID:** `list_reviews_retention_reviews_get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `kind` | query | No | `string` or `null` | max length: `12` | — |
| `status` | query | No | `string` or `null` | max length: `12` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`RetentionReviewOut`](#schema-retentionreviewout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "review_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "kind": "string",
    "status": "string",
    "office": "string",
    "cohort": "2026-09-17",
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string",
    "project_status": "string",
    "is_activity": true,
    "purpose_code": "string",
    "purpose_name": "string",
    "retention_days": 1,
    "validity_days": 1,
    "lapse_behaviour": "string",
    "notify_before_erasure": true,
    "people": 1,
    "held": 1,
    "renewed": 1,
    "first_due_at": "2026-09-17T12:00:00Z",
    "last_due_at": "2026-09-17T12:00:00Z",
    "actions": 1,
    "actions_open": 1,
    "actions_to_review": 1,
    "reconsent": "string",
    "opened_at": "2026-09-17T12:00:00Z",
    "closed_at": "2026-09-17T12:00:00Z",
    "closed_by_name": "string",
    "close_note": "string"
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

<a id="2_post_retention_refresh"></a>
## 2. `POST /retention/refresh` — Look for what falls due, now

### API

- **Operation ID:** `refresh_retention_refresh_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

What the night does, at once: across both offices, as the night does -
it decides nothing an officer could not see tomorrow.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionSweepOut`](#schema-retentionsweepout) |

**Example `200` `application/json` response:**

```json
{
  "reviews_made": 1,
  "people_added": 1,
  "holds_changed": 1,
  "renewed": 1,
  "fell_due": 1,
  "actions_opened": 1,
  "reminders": 1,
  "chased": 1,
  "escalated": 1,
  "people_told": 1
}
```

<a id="3_get_retention_settings"></a>
## 3. `GET /retention/settings` — Reminders, notice and deadlines

### API

- **Operation ID:** `get_settings_retention_settings_get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionSettingsOut`](#schema-retentionsettingsout) |

**Example `200` `application/json` response:**

```json
{
  "reminder_days": [
    1
  ],
  "notice_hours": 1,
  "action_days": 1,
  "escalate_after_days": 1,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
}
```

<a id="4_put_retention_settings"></a>
## 4. `PUT /retention/settings` — Set reminders, notice and deadlines

### API

- **Operation ID:** `put_settings_retention_settings_put`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RetentionSettingsIn`](#schema-retentionsettingsin)

```json
{
  "reminder_days": [
    1
  ],
  "notice_hours": 0.0,
  "action_days": 1.0,
  "escalate_after_days": 1.0
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionSettingsOut`](#schema-retentionsettingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "reminder_days": [
    1
  ],
  "notice_hours": 1,
  "action_days": 1,
  "escalate_after_days": 1,
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

<a id="5_get_retention_reviews_review_uuid"></a>
## 5. `GET /retention/reviews/{review_uuid}` — One review

### API

- **Operation ID:** `get_review_retention_reviews__review_uuid__get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionReviewDetailOut`](#schema-retentionreviewdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "kind": "string",
  "status": "string",
  "office": "string",
  "cohort": "2026-09-17",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "project_status": "string",
  "is_activity": true,
  "purpose_code": "string",
  "purpose_name": "string",
  "retention_days": 1,
  "validity_days": 1,
  "lapse_behaviour": "string",
  "notify_before_erasure": true,
  "people": 1,
  "held": 1,
  "renewed": 1,
  "first_due_at": "2026-09-17T12:00:00Z",
  "last_due_at": "2026-09-17T12:00:00Z",
  "actions": 1,
  "actions_open": 1,
  "actions_to_review": 1,
  "reconsent": "string",
  "opened_at": "2026-09-17T12:00:00Z",
  "closed_at": "2026-09-17T12:00:00Z",
  "closed_by_name": "string",
  "close_note": "string",
  "people_list": [
    {
      "consent_uuid": "00000000-0000-4000-8000-000000000000",
      "consent_no": 1,
      "person_no": 1,
      "due_at": "2026-09-17T12:00:00Z",
      "ended_by": "string",
      "state": "string",
      "notified_at": "…",
      "invited_at": "…"
    }
  ],
  "actions_list": [
    {
      "action_uuid": "00000000-0000-4000-8000-000000000000",
      "review_uuid": "00000000-0000-4000-8000-000000000000",
      "reference": "string",
      "review_kind": "string",
      "kind": "string",
      "label": "string",
      "channel": "string",
      "assignee_name": "…",
      "status": "string",
      "outcome": "…",
      "reason": "…",
      "keep_until": "…",
      "reconsent": "…",
      "due_at": "2026-09-17T12:00:00Z",
      "answered_at": "…",
      "answered_by_name": "…",
      "accepted_at": "…",
      "accepted_by_name": "…",
      "sent_back_reason": "…",
      "overdue": true
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

<a id="6_post_retention_reviews_review_uuid_actions_action_uuid_accept"></a>
## 6. `POST /retention/reviews/{review_uuid}/actions/{action_uuid}/accept` — Accept an answer

### API

- **Operation ID:** `accept_retention_reviews__review_uuid__actions__action_uuid__accept_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |
| `action_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionActionOut`](#schema-retentionactionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "action_uuid": "00000000-0000-4000-8000-000000000000",
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "review_kind": "string",
  "kind": "string",
  "label": "string",
  "channel": "string",
  "assignee_name": "string",
  "status": "string",
  "outcome": "string",
  "reason": "string",
  "keep_until": "2026-09-17",
  "reconsent": true,
  "due_at": "2026-09-17T12:00:00Z",
  "answered_at": "2026-09-17T12:00:00Z",
  "answered_by_name": "string",
  "accepted_at": "2026-09-17T12:00:00Z",
  "accepted_by_name": "string",
  "sent_back_reason": "string",
  "overdue": true
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

<a id="7_post_retention_reviews_review_uuid_actions_action_uuid_send_back"></a>
## 7. `POST /retention/reviews/{review_uuid}/actions/{action_uuid}/send-back` — Send an answer back, saying what is missing

### API

- **Operation ID:** `send_back_retention_reviews__review_uuid__actions__action_uuid__send_back_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |
| `action_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RetentionReasonIn`](#schema-retentionreasonin)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionActionOut`](#schema-retentionactionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "action_uuid": "00000000-0000-4000-8000-000000000000",
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "review_kind": "string",
  "kind": "string",
  "label": "string",
  "channel": "string",
  "assignee_name": "string",
  "status": "string",
  "outcome": "string",
  "reason": "string",
  "keep_until": "2026-09-17",
  "reconsent": true,
  "due_at": "2026-09-17T12:00:00Z",
  "answered_at": "2026-09-17T12:00:00Z",
  "answered_by_name": "string",
  "accepted_at": "2026-09-17T12:00:00Z",
  "accepted_by_name": "string",
  "sent_back_reason": "string",
  "overdue": true
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

<a id="8_post_retention_reviews_review_uuid_actions_action_uuid_not_needed"></a>
## 8. `POST /retention/reviews/{review_uuid}/actions/{action_uuid}/not-needed` — Set an action aside: nobody need answer it

### API

- **Operation ID:** `not_needed_retention_reviews__review_uuid__actions__action_uuid__not_needed_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |
| `action_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionActionOut`](#schema-retentionactionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "action_uuid": "00000000-0000-4000-8000-000000000000",
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "review_kind": "string",
  "kind": "string",
  "label": "string",
  "channel": "string",
  "assignee_name": "string",
  "status": "string",
  "outcome": "string",
  "reason": "string",
  "keep_until": "2026-09-17",
  "reconsent": true,
  "due_at": "2026-09-17T12:00:00Z",
  "answered_at": "2026-09-17T12:00:00Z",
  "answered_by_name": "string",
  "accepted_at": "2026-09-17T12:00:00Z",
  "accepted_by_name": "string",
  "sent_back_reason": "string",
  "overdue": true
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

<a id="9_post_retention_reviews_review_uuid_close"></a>
## 9. `POST /retention/reviews/{review_uuid}/close` — Close a review

### API

- **Operation ID:** `close_retention_reviews__review_uuid__close_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RetentionCloseIn`](#schema-retentionclosein)

```json
{
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionReviewOut`](#schema-retentionreviewout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "kind": "string",
  "status": "string",
  "office": "string",
  "cohort": "2026-09-17",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "project_status": "string",
  "is_activity": true,
  "purpose_code": "string",
  "purpose_name": "string",
  "retention_days": 1,
  "validity_days": 1,
  "lapse_behaviour": "string",
  "notify_before_erasure": true,
  "people": 1,
  "held": 1,
  "renewed": 1,
  "first_due_at": "2026-09-17T12:00:00Z",
  "last_due_at": "2026-09-17T12:00:00Z",
  "actions": 1,
  "actions_open": 1,
  "actions_to_review": 1,
  "reconsent": "string",
  "opened_at": "2026-09-17T12:00:00Z",
  "closed_at": "2026-09-17T12:00:00Z",
  "closed_by_name": "string",
  "close_note": "string"
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

<a id="10_get_retention_reviews_review_uuid_certificate"></a>
## 10. `GET /retention/reviews/{review_uuid}/certificate` — The certificate of a closed review, as PDF or CSV

### API

- **Operation ID:** `get_certificate_retention_reviews__review_uuid__certificate_get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

Which consents, why each ended, who was asked and what each answered,
who accepted it and who closed the review. Consents by number; every
download on the trail.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `review_uuid` | path | Yes | `string` | format: `uuid` | — |
| `format` | query | No | `string` | pattern: `^(pdf|csv)$`; default: `pdf` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/pdf` | `object` |
| `200` | ↳ | `text/csv` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/pdf` response:**

```json
"string"
```

**Example `200` `text/csv` response:**

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

<a id="11_get_retention_actions"></a>
## 11. `GET /retention-actions` — What I am asked to do

### API

- **Operation ID:** `my_actions_retention_actions_get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

Read across both offices: what is asked of a person is theirs, whichever
office's project it is - the query names them.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`RetentionActionOut`](#schema-retentionactionout) |

**Example `200` `application/json` response:**

```json
[
  {
    "action_uuid": "00000000-0000-4000-8000-000000000000",
    "review_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "review_kind": "string",
    "kind": "string",
    "label": "string",
    "channel": "string",
    "assignee_name": "string",
    "status": "string",
    "outcome": "string",
    "reason": "string",
    "keep_until": "2026-09-17",
    "reconsent": true,
    "due_at": "2026-09-17T12:00:00Z",
    "answered_at": "2026-09-17T12:00:00Z",
    "answered_by_name": "string",
    "accepted_at": "2026-09-17T12:00:00Z",
    "accepted_by_name": "string",
    "sent_back_reason": "string",
    "overdue": true
  }
]
```

<a id="12_get_retention_actions_action_uuid"></a>
## 12. `GET /retention-actions/{action_uuid}` — One of mine

### API

- **Operation ID:** `my_action_retention_actions__action_uuid__get`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `action_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionHolderActionOut`](#schema-retentionholderactionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "action": {
    "action_uuid": "00000000-0000-4000-8000-000000000000",
    "review_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "review_kind": "string",
    "kind": "string",
    "label": "string",
    "channel": "string",
    "assignee_name": "string",
    "status": "string",
    "outcome": "string",
    "reason": "string",
    "keep_until": "2026-09-17",
    "reconsent": true,
    "due_at": "2026-09-17T12:00:00Z",
    "answered_at": "2026-09-17T12:00:00Z",
    "answered_by_name": "string",
    "accepted_at": "2026-09-17T12:00:00Z",
    "accepted_by_name": "string",
    "sent_back_reason": "string",
    "overdue": true
  },
  "review": {
    "reference": "string",
    "kind": "string",
    "project_name": "string",
    "is_activity": true,
    "purpose_code": "string",
    "purpose_name": "string",
    "people": 1,
    "first_due_at": "2026-09-17T12:00:00Z",
    "last_due_at": "2026-09-17T12:00:00Z",
    "retention_days": 1,
    "validity_days": 1,
    "status": "string"
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

<a id="13_post_retention_actions_action_uuid_answer"></a>
## 13. `POST /retention-actions/{action_uuid}/answer` — Answer it

### API

- **Operation ID:** `answer_retention_actions__action_uuid__answer_post`
- **Access:** Role-controlled `retention` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `action_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RetentionAnswerIn`](#schema-retentionanswerin)

```json
{
  "outcome": "string",
  "reason": "string",
  "keep_until": "2026-09-17",
  "reconsent": true
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionActionOut`](#schema-retentionactionout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "action_uuid": "00000000-0000-4000-8000-000000000000",
  "review_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "review_kind": "string",
  "kind": "string",
  "label": "string",
  "channel": "string",
  "assignee_name": "string",
  "status": "string",
  "outcome": "string",
  "reason": "string",
  "keep_until": "2026-09-17",
  "reconsent": true,
  "due_at": "2026-09-17T12:00:00Z",
  "answered_at": "2026-09-17T12:00:00Z",
  "answered_by_name": "string",
  "accepted_at": "2026-09-17T12:00:00Z",
  "accepted_by_name": "string",
  "sent_back_reason": "string",
  "overdue": true
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

<a id="schema-retentionactionout"></a>
#### `RetentionActionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `action_uuid` | `string` | Yes | format: `uuid` | — |
| `review_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `review_kind` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `assignee_name` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `reason` | `string` or `null` | Yes | — | — |
| `keep_until` | `string` or `null` | Yes | format: `date` | — |
| `reconsent` | `boolean` or `null` | Yes | — | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `answered_at` | `string` or `null` | Yes | format: `date-time` | — |
| `answered_by_name` | `string` or `null` | Yes | — | — |
| `accepted_at` | `string` or `null` | Yes | format: `date-time` | — |
| `accepted_by_name` | `string` or `null` | Yes | — | — |
| `sent_back_reason` | `string` or `null` | Yes | — | — |
| `overdue` | `boolean` | Yes | — | — |

<a id="schema-retentionanswerin"></a>
#### `RetentionAnswerIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `outcome` | `string` or `null` | No | max length: `16` | — |
| `reason` | `string` or `null` | No | max length: `2000` | — |
| `keep_until` | `string` or `null` | No | format: `date` | — |
| `reconsent` | `boolean` or `null` | No | — | — |

<a id="schema-retentionclosein"></a>
#### `RetentionCloseIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `note` | `string` or `null` | No | max length: `2000` | — |

<a id="schema-retentionholderactionout"></a>
#### `RetentionHolderActionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `action` | [`RetentionActionOut`](#schema-retentionactionout) | Yes | — | — |
| `review` | [`RetentionHolderReviewOut`](#schema-retentionholderreviewout) | Yes | — | — |

<a id="schema-retentionreasonin"></a>
#### `RetentionReasonIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `1`; max length: `2000` | — |

<a id="schema-retentionreviewdetailout"></a>
#### `RetentionReviewDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `review_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `office` | `string` | Yes | — | — |
| `cohort` | `string` | Yes | format: `date` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `project_status` | `string` | Yes | — | — |
| `is_activity` | `boolean` | Yes | — | — |
| `purpose_code` | `string` | Yes | — | — |
| `purpose_name` | `string` | Yes | — | — |
| `retention_days` | `integer` or `null` | Yes | — | — |
| `validity_days` | `integer` or `null` | Yes | — | — |
| `lapse_behaviour` | `string` | Yes | — | — |
| `notify_before_erasure` | `boolean` | Yes | — | — |
| `people` | `integer` | Yes | — | — |
| `held` | `integer` | Yes | — | — |
| `renewed` | `integer` | Yes | — | — |
| `first_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `last_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `actions` | `integer` | Yes | — | — |
| `actions_open` | `integer` | Yes | — | — |
| `actions_to_review` | `integer` | Yes | — | — |
| `reconsent` | `string` or `null` | Yes | — | — |
| `opened_at` | `string` or `null` | Yes | format: `date-time` | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `closed_by_name` | `string` or `null` | Yes | — | — |
| `close_note` | `string` or `null` | Yes | — | — |
| `people_list` | array of [`RetentionPersonOut`](#schema-retentionpersonout) | Yes | — | — |
| `actions_list` | array of [`RetentionActionOut`](#schema-retentionactionout) | Yes | — | — |

<a id="schema-retentionreviewout"></a>
#### `RetentionReviewOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `review_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `office` | `string` | Yes | — | — |
| `cohort` | `string` | Yes | format: `date` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `project_status` | `string` | Yes | — | — |
| `is_activity` | `boolean` | Yes | — | — |
| `purpose_code` | `string` | Yes | — | — |
| `purpose_name` | `string` | Yes | — | — |
| `retention_days` | `integer` or `null` | Yes | — | — |
| `validity_days` | `integer` or `null` | Yes | — | — |
| `lapse_behaviour` | `string` | Yes | — | — |
| `notify_before_erasure` | `boolean` | Yes | — | — |
| `people` | `integer` | Yes | — | — |
| `held` | `integer` | Yes | — | — |
| `renewed` | `integer` | Yes | — | — |
| `first_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `last_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `actions` | `integer` | Yes | — | — |
| `actions_open` | `integer` | Yes | — | — |
| `actions_to_review` | `integer` | Yes | — | — |
| `reconsent` | `string` or `null` | Yes | — | — |
| `opened_at` | `string` or `null` | Yes | format: `date-time` | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `closed_by_name` | `string` or `null` | Yes | — | — |
| `close_note` | `string` or `null` | Yes | — | — |

<a id="schema-retentionsettingsin"></a>
#### `RetentionSettingsIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reminder_days` | array of `integer` | Yes | — | — |
| `notice_hours` | `integer` | Yes | minimum: `0.0`; maximum: `720.0` | — |
| `action_days` | `integer` | Yes | minimum: `1.0`; maximum: `365.0` | — |
| `escalate_after_days` | `integer` | Yes | minimum: `1.0`; maximum: `365.0` | — |

<a id="schema-retentionsettingsout"></a>
#### `RetentionSettingsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reminder_days` | array of `integer` | Yes | — | — |
| `notice_hours` | `integer` | Yes | — | — |
| `action_days` | `integer` | Yes | — | — |
| `escalate_after_days` | `integer` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-retentionsweepout"></a>
#### `RetentionSweepOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reviews_made` | `integer` | Yes | — | — |
| `people_added` | `integer` | Yes | — | — |
| `holds_changed` | `integer` | Yes | — | — |
| `renewed` | `integer` | Yes | — | — |
| `fell_due` | `integer` | Yes | — | — |
| `actions_opened` | `integer` | Yes | — | — |
| `reminders` | `integer` | Yes | — | — |
| `chased` | `integer` | Yes | — | — |
| `escalated` | `integer` | Yes | — | — |
| `people_told` | `integer` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-retentionholderreviewout"></a>
#### `RetentionHolderReviewOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `project_name` | `string` | Yes | — | — |
| `is_activity` | `boolean` | Yes | — | — |
| `purpose_code` | `string` | Yes | — | — |
| `purpose_name` | `string` | Yes | — | — |
| `people` | `integer` | Yes | — | — |
| `first_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `last_due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `retention_days` | `integer` or `null` | Yes | — | — |
| `validity_days` | `integer` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |

<a id="schema-retentionpersonout"></a>
#### `RetentionPersonOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `consent_uuid` | `string` | Yes | format: `uuid` | — |
| `consent_no` | `integer` | Yes | — | — |
| `person_no` | `integer` | Yes | — | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `ended_by` | `string` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `notified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `invited_at` | `string` or `null` | Yes | format: `date-time` | — |
