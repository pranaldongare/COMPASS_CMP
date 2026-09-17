# Tickets API

Generated from `cmp_backend/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /tickets`](#1_get_tickets)
2. [`GET /tickets/{holder_uuid}`](#2_get_tickets_holder_uuid)
3. [`POST /tickets/{holder_uuid}/messages`](#3_post_tickets_holder_uuid_messages)
4. [`GET /tickets/{holder_uuid}/messages/{message_uuid}/evidence`](#4_get_tickets_holder_uuid_messages_message_uuid_evidence)
5. [`POST /tickets/{holder_uuid}/return`](#5_post_tickets_holder_uuid_return)

<a id="1_get_tickets"></a>
## 1. `GET /tickets` — Tickets addressed to me

### API

- **Operation ID:** `my_tickets_tickets_get`
- **Access:** Role-controlled `tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

The portal channel's inbox: the holders of a rights request that are one
of our own teams answer here, not by email. Scope OWN - only what is
addressed to this account, and only what the instruction says.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`TicketOut`](#schema-ticketout) |

**Example `200` `application/json` response:**

```json
[
  {
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
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_project": "string",
    "consent_notice_code": "string",
    "consent_notice_version": 1,
    "consent_at": "2026-09-17T12:00:00Z",
    "consent_purposes": [
      "string"
    ]
  }
]
```

<a id="2_get_tickets_holder_uuid"></a>
## 2. `GET /tickets/{holder_uuid}` — One ticket, with its brief and thread

### API

- **Operation ID:** `my_ticket_tickets__holder_uuid__get`
- **Access:** Role-controlled `tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

Reading it marks the office's messages read.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="3_post_tickets_holder_uuid_messages"></a>
## 3. `POST /tickets/{holder_uuid}/messages` — Write to the Privacy Office on my ticket, with a file if it helps

### API

- **Operation ID:** `message_office_tickets__holder_uuid__messages_post`
- **Access:** Role-controlled `tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

Kept on the thread, and every DPO is told.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_message_office_tickets__holder_uuid__messages_post`](#schema-body_message_office_tickets_holder_uuid_messages_post)

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

<a id="4_get_tickets_holder_uuid_messages_message_uuid_evidence"></a>
## 4. `GET /tickets/{holder_uuid}/messages/{message_uuid}/evidence` — Download a file attached to a message on my ticket

### API

- **Operation ID:** `my_message_attachment_tickets__holder_uuid__messages__message_uuid__evidence_get`
- **Access:** Role-controlled `tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |
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

<a id="5_post_tickets_holder_uuid_return"></a>
## 5. `POST /tickets/{holder_uuid}/return` — Return a ticket addressed to me

### API

- **Operation ID:** `return_my_ticket_tickets__holder_uuid__return_post`
- **Access:** Role-controlled `tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_return_my_ticket_tickets__holder_uuid__return_post`](#schema-body_return_my_ticket_tickets_holder_uuid_return_post)

```json
{
  "summary": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TicketOut`](#schema-ticketout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
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
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_purposes": [
    "string"
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

<a id="schema-body_message_office_tickets_holder_uuid_messages_post"></a>
#### `Body_message_office_tickets__holder_uuid__messages_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `body` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional file, max 25 MB |

<a id="schema-body_return_my_ticket_tickets_holder_uuid_return_post"></a>
#### `Body_return_my_ticket_tickets__holder_uuid__return_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `summary` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional evidence, max 25 MB |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-ticketdetailout"></a>
#### `TicketDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket` | [`TicketOut`](#schema-ticketout) | Yes | — | — |
| `messages` | array of [`cmp__api__routers__v1__rights__MessageOut`](#schema-cmp_api_routers_v1_rights_messageout) | Yes | — | — |

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
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `consent_notice_code` | `string` or `null` | No | — | — |
| `consent_notice_version` | `integer` or `null` | No | — | — |
| `consent_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_purposes` | array of `string` or `null` | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

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
