# Holder Tickets API

Generated from `backend/api/openapi.json`. **8 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /holder-tickets/{token}`](#1_get_holder_tickets_token)
2. [`POST /holder-tickets/{token}/code`](#2_post_holder_tickets_token_code)
3. [`POST /holder-tickets/{token}/verify`](#3_post_holder_tickets_token_verify)
4. [`POST /holder-tickets/{token}/sign-out`](#4_post_holder_tickets_token_sign_out)
5. [`GET /holder-tickets/{token}/ticket`](#5_get_holder_tickets_token_ticket)
6. [`POST /holder-tickets/{token}/messages`](#6_post_holder_tickets_token_messages)
7. [`POST /holder-tickets/{token}/answer`](#7_post_holder_tickets_token_answer)
8. [`GET /holder-tickets/{token}/messages/{message_uuid}/evidence`](#8_get_holder_tickets_token_messages_message_uuid_evidence)

<a id="1_get_holder_tickets_token"></a>
## 1. `GET /holder-tickets/{token}` — What the link opens, before the code

### API

- **Operation ID:** `open_link_holder_tickets__token__get`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderLinkOut`](#schema-holderlinkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "reference": "string",
  "holder_label": "string",
  "request_type": "string",
  "code_goes_to": "string",
  "state": "string",
  "state_label": "string",
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

<a id="2_post_holder_tickets_token_code"></a>
## 2. `POST /holder-tickets/{token}/code` — Send a code to the ticket's address

### API

- **Operation ID:** `send_code_holder_tickets__token__code_post`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

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

<a id="3_post_holder_tickets_token_verify"></a>
## 3. `POST /holder-tickets/{token}/verify` — Enter the code

### API

- **Operation ID:** `verify_holder_tickets__token__verify_post`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

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

<a id="4_post_holder_tickets_token_sign_out"></a>
## 4. `POST /holder-tickets/{token}/sign-out` — Close the ticket here

### API

- **Operation ID:** `sign_out_holder_tickets__token__sign_out_post`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

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

<a id="5_get_holder_tickets_token_ticket"></a>
## 5. `GET /holder-tickets/{token}/ticket` — The ticket, after the code

### API

- **Operation ID:** `read_ticket_holder_tickets__token__ticket_get`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

What is asked, the items, what the platform holds about the person, and
the messages. Reading marks the office's messages read.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TicketDetailOut`](#schema-ticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "request_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "request_type": "string",
    "request_status": "string",
    "label": "string",
    "subject_name": "string",
    "instruction": "string",
    "ticket_status": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_outcome": "string",
    "return_evidence_hash": "string",
    "brief": {},
    "message_count": 0,
    "unread_for_holder": 0,
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0,
    "accepted_at": "2026-09-17T12:00:00Z",
    "state": "",
    "state_label": "",
    "overdue": false,
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_project": "string",
    "consent_notice_code": "string",
    "consent_notice_version": 1,
    "consent_at": "2026-09-17T12:00:00Z",
    "consent_purposes": [
      "…"
    ]
  },
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
    }
  ],
  "items": [
    {
      "item_uuid": "00000000-0000-4000-8000-000000000000",
      "decision": "string",
      "retain_until": "…",
      "other_subjects": 1,
      "state": "string",
      "asset_type": "string",
      "source_asset_ref": "string",
      "source_name": "string",
      "project_name": "string",
      "collected_on": "2026-09-17"
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

<a id="6_post_holder_tickets_token_messages"></a>
## 6. `POST /holder-tickets/{token}/messages` — Write to the Privacy Office, with a file if it helps

### API

- **Operation ID:** `write_holder_tickets__token__messages_post`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_write_holder_tickets__token__messages_post`](#schema-body_write_holder_tickets_token_messages_post)

```json
{
  "body": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TicketDetailOut`](#schema-ticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "request_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "request_type": "string",
    "request_status": "string",
    "label": "string",
    "subject_name": "string",
    "instruction": "string",
    "ticket_status": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_outcome": "string",
    "return_evidence_hash": "string",
    "brief": {},
    "message_count": 0,
    "unread_for_holder": 0,
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0,
    "accepted_at": "2026-09-17T12:00:00Z",
    "state": "",
    "state_label": "",
    "overdue": false,
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_project": "string",
    "consent_notice_code": "string",
    "consent_notice_version": 1,
    "consent_at": "2026-09-17T12:00:00Z",
    "consent_purposes": [
      "…"
    ]
  },
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
    }
  ],
  "items": [
    {
      "item_uuid": "00000000-0000-4000-8000-000000000000",
      "decision": "string",
      "retain_until": "…",
      "other_subjects": 1,
      "state": "string",
      "asset_type": "string",
      "source_asset_ref": "string",
      "source_name": "string",
      "project_name": "string",
      "collected_on": "2026-09-17"
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

<a id="7_post_holder_tickets_token_answer"></a>
## 7. `POST /holder-tickets/{token}/answer` — Give the answer: what was done, what is held, and proof

### API

- **Operation ID:** `answer_holder_tickets__token__answer_post`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

It waits for the Privacy Office to accept it, or send it back.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_answer_holder_tickets__token__answer_post`](#schema-body_answer_holder_tickets_token_answer_post)

```json
{
  "summary": "string",
  "outcome": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TicketDetailOut`](#schema-ticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "request_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "request_type": "string",
    "request_status": "string",
    "label": "string",
    "subject_name": "string",
    "instruction": "string",
    "ticket_status": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_outcome": "string",
    "return_evidence_hash": "string",
    "brief": {},
    "message_count": 0,
    "unread_for_holder": 0,
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0,
    "accepted_at": "2026-09-17T12:00:00Z",
    "state": "",
    "state_label": "",
    "overdue": false,
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_project": "string",
    "consent_notice_code": "string",
    "consent_notice_version": 1,
    "consent_at": "2026-09-17T12:00:00Z",
    "consent_purposes": [
      "…"
    ]
  },
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
    }
  ],
  "items": [
    {
      "item_uuid": "00000000-0000-4000-8000-000000000000",
      "decision": "string",
      "retain_until": "…",
      "other_subjects": 1,
      "state": "string",
      "asset_type": "string",
      "source_asset_ref": "string",
      "source_name": "string",
      "project_name": "string",
      "collected_on": "2026-09-17"
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

<a id="8_get_holder_tickets_token_messages_message_uuid_evidence"></a>
## 8. `GET /holder-tickets/{token}/messages/{message_uuid}/evidence` — Download a file on the ticket's messages

### API

- **Operation ID:** `message_file_holder_tickets__token__messages__message_uuid__evidence_get`
- **Access:** Role-controlled `holder tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |
| `message_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="schema-body_answer_holder_tickets_token_answer_post"></a>
#### `Body_answer_holder_tickets__token__answer_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `summary` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `outcome` | `string` | Yes | — | done, partial or failed |
| `evidence` | `string` or `null` | No | — | Optional proof, max 25 MB |

<a id="schema-body_write_holder_tickets_token_messages_post"></a>
#### `Body_write_holder_tickets__token__messages_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `body` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional file, max 25 MB |

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

<a id="schema-holderlinkout"></a>
#### `HolderLinkOut`

What the link alone shows: whose ticket, and where the code goes.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `holder_label` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `code_goes_to` | `string` or `null` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `state_label` | `string` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `signed_in` | `boolean` | Yes | — | — |

<a id="schema-ticketdetailout"></a>
#### `TicketDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket` | [`TicketOut`](#schema-ticketout) | Yes | — | — |
| `messages` | array of [`cmp__api__routers__v1__rights__MessageOut`](#schema-cmp_api_routers_v1_rights_messageout) | Yes | — | — |
| `items` | array of [`TicketItemOut`](#schema-ticketitemout) | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-ticketout"></a>
#### `TicketOut`

A ticket as its respondent sees it: what is asked, of whom, by when.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `holder_uuid` | `string` | Yes | format: `uuid` | — |
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `request_status` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `subject_name` | `string` or `null` | Yes | — | — |
| `instruction` | `string` or `null` | Yes | — | — |
| `ticket_status` | `string` | Yes | — | — |
| `issued_at` | `string` or `null` | Yes | format: `date-time` | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `escalated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `returned_at` | `string` or `null` | Yes | format: `date-time` | — |
| `return_summary` | `string` or `null` | Yes | — | — |
| `return_outcome` | `string` or `null` | Yes | — | — |
| `return_evidence_hash` | `string` or `null` | Yes | — | — |
| `brief` | `object` or `null` | No | — | — |
| `message_count` | `integer` | No | default: `0` | — |
| `unread_for_holder` | `integer` | No | default: `0` | — |
| `last_reminded_at` | `string` or `null` | No | format: `date-time` | — |
| `reminders_sent` | `integer` | No | default: `0` | — |
| `return_evidence_name` | `string` or `null` | No | — | — |
| `sent_back_at` | `string` or `null` | No | format: `date-time` | — |
| `sent_back_reason` | `string` or `null` | No | — | — |
| `sent_back_count` | `integer` | No | default: `0` | — |
| `accepted_at` | `string` or `null` | No | format: `date-time` | — |
| `state` | `string` | No | default: `` | — |
| `state_label` | `string` | No | default: `` | — |
| `overdue` | `boolean` | No | default: `False` | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `consent_notice_code` | `string` or `null` | No | — | — |
| `consent_notice_version` | `integer` or `null` | No | — | — |
| `consent_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_purposes` | array of `string` or `null` | No | — | — |

<a id="schema-cmp_api_routers_v1_rights_messageout"></a>
#### `cmp__api__routers__v1__rights__MessageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `message_uuid` | `string` | Yes | format: `uuid` | — |
| `author_side` | `string` | Yes | — | — |
| `author_name` | `string` or `null` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `body` | `string` | Yes | — | — |
| `evidence_hash` | `string` or `null` | Yes | — | — |
| `evidence_name` | `string` or `null` | No | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-ticketitemout"></a>
#### `TicketItemOut`

One item an erasure ticket asks its holder to act on (2026-10-08):
which asset, and what to do with it. The legal basis stays the office's.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `item_uuid` | `string` | Yes | format: `uuid` | — |
| `decision` | `string` | Yes | — | — |
| `retain_until` | `string` or `null` | Yes | format: `date` | — |
| `other_subjects` | `integer` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `asset_type` | `string` | Yes | — | — |
| `source_asset_ref` | `string` | Yes | — | — |
| `source_name` | `string` | Yes | — | — |
| `project_name` | `string` | Yes | — | — |
| `collected_on` | `string` | Yes | format: `date` | — |
