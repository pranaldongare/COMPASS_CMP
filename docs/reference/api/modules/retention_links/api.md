# Retention Links API

Generated from `backend/api/openapi.json`. **7 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /retention-links/{token}`](#1_get_retention_links_token)
2. [`POST /retention-links/{token}/code`](#2_post_retention_links_token_code)
3. [`POST /retention-links/{token}/verify`](#3_post_retention_links_token_verify)
4. [`POST /retention-links/{token}/sign-out`](#4_post_retention_links_token_sign_out)
5. [`GET /retention-links/{token}/action`](#5_get_retention_links_token_action)
6. [`POST /retention-links/{token}/answer`](#6_post_retention_links_token_answer)
7. [`POST /retention-links/{token}/evidence`](#7_post_retention_links_token_evidence)

<a id="1_get_retention_links_token"></a>
## 1. `GET /retention-links/{token}` — What the link opens

### API

- **Operation ID:** `open_link_retention_links__token__get`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RetentionLinkOut`](#schema-retentionlinkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "reference": "string",
  "holder_label": "string",
  "kind": "string",
  "code_goes_to": "string",
  "status": "string",
  "due_at": "2026-09-17T12:00:00Z",
  "signed_in": true
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

<a id="2_post_retention_links_token_code"></a>
## 2. `POST /retention-links/{token}/code` — Send a code

### API

- **Operation ID:** `send_code_retention_links__token__code_post`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

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

<a id="3_post_retention_links_token_verify"></a>
## 3. `POST /retention-links/{token}/verify` — Enter the code

### API

- **Operation ID:** `verify_retention_links__token__verify_post`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CodeIn`](#schema-codein)

```json
{
  "code": "string"
}
```

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

<a id="4_post_retention_links_token_sign_out"></a>
## 4. `POST /retention-links/{token}/sign-out` — Close the review here

### API

- **Operation ID:** `sign_out_retention_links__token__sign_out_post`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `204` | Successful Response | — | — |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

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

<a id="5_get_retention_links_token_action"></a>
## 5. `GET /retention-links/{token}/action` — The action, after the code

### API

- **Operation ID:** `read_action_retention_links__token__action_get`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

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
    "evidence_name": "string",
    "evidence_hash": "string",
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

<a id="6_post_retention_links_token_answer"></a>
## 6. `POST /retention-links/{token}/answer` — Answer it

### API

- **Operation ID:** `answer_retention_links__token__answer_post`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

It waits for the Privacy Office to accept it, or send it back.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

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
    "evidence_name": "string",
    "evidence_hash": "string",
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

<a id="7_post_retention_links_token_evidence"></a>
## 7. `POST /retention-links/{token}/evidence` — Attach proof

### API

- **Operation ID:** `add_evidence_retention_links__token__evidence_post`
- **Access:** Role-controlled `retention links` operation. See [`../../roles/README.md`](../../roles/README.md).

One file, replaced by the next, while the answer is still to give.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_add_evidence_retention_links__token__evidence_post`](#schema-body_add_evidence_retention_links_token_evidence_post)

```json
{
  "evidence": "string"
}
```

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
    "evidence_name": "string",
    "evidence_hash": "string",
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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-body_add_evidence_retention_links_token_evidence_post"></a>
#### `Body_add_evidence_retention_links__token__evidence_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `evidence` | `string` | Yes | — | The proof, max 25 MB |

<a id="schema-codein"></a>
#### `CodeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-retentionanswerin"></a>
#### `RetentionAnswerIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `outcome` | `string` or `null` | No | max length: `16` | — |
| `reason` | `string` or `null` | No | max length: `2000` | — |
| `keep_until` | `string` or `null` | No | format: `date` | — |
| `reconsent` | `boolean` or `null` | No | — | — |

<a id="schema-retentionholderactionout"></a>
#### `RetentionHolderActionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `action` | [`RetentionActionOut`](#schema-retentionactionout) | Yes | — | — |
| `review` | [`RetentionHolderReviewOut`](#schema-retentionholderreviewout) | Yes | — | — |

<a id="schema-retentionlinkout"></a>
#### `RetentionLinkOut`

What the link alone shows: which review, who is asked, where the code goes.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `holder_label` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `code_goes_to` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `signed_in` | `boolean` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

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
| `evidence_name` | `string` or `null` | No | — | — |
| `evidence_hash` | `string` or `null` | No | — | — |
| `overdue` | `boolean` | Yes | — | — |

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
