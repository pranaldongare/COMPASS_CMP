# Breach Tickets API

Generated from `backend/api/openapi.json`. **6 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /breach-tickets`](#1_get_breach_tickets)
2. [`GET /breach-tickets/{ticket_uuid}`](#2_get_breach_tickets_ticket_uuid)
3. [`POST /breach-tickets/{ticket_uuid}/messages`](#3_post_breach_tickets_ticket_uuid_messages)
4. [`GET /breach-tickets/{ticket_uuid}/messages/{message_uuid}/evidence`](#4_get_breach_tickets_ticket_uuid_messages_message_uuid_evidence)
5. [`POST /breach-tickets/{ticket_uuid}/colleagues`](#5_post_breach_tickets_ticket_uuid_colleagues)
6. [`POST /breach-tickets/{ticket_uuid}/return`](#6_post_breach_tickets_ticket_uuid_return)

<a id="1_get_breach_tickets"></a>
## 1. `GET /breach-tickets` — Breach tickets addressed to me

### API

- **Operation ID:** `my_breach_tickets_breach_tickets_get`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`MyBreachTicketOut`](#schema-mybreachticketout) |

**Example `200` `application/json` response:**

```json
[
  {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "breach_reference": "string",
    "instruction": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "moves": [
      {
        "move": "…",
        "reason_required": "…"
      }
    ],
    "may_add_colleague": true
  }
]
```

<a id="2_get_breach_tickets_ticket_uuid"></a>
## 2. `GET /breach-tickets/{ticket_uuid}` — One breach ticket addressed to me, with its thread

### API

- **Operation ID:** `my_breach_ticket_breach_tickets__ticket_uuid__get`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

Reading it marks the Privacy Office's messages read.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MyBreachTicketDetailOut`](#schema-mybreachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "breach_reference": "string",
    "instruction": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "moves": [
      "…"
    ],
    "may_add_colleague": true
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

<a id="3_post_breach_tickets_ticket_uuid_messages"></a>
## 3. `POST /breach-tickets/{ticket_uuid}/messages` — Write to the Privacy Office on my breach ticket, with a file if it helps

### API

- **Operation ID:** `message_office_breach_tickets__ticket_uuid__messages_post`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_message_office_breach_tickets__ticket_uuid__messages_post`](#schema-body_message_office_breach_tickets_ticket_uuid_messages_post)

```json
{
  "body": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MyBreachTicketDetailOut`](#schema-mybreachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "breach_reference": "string",
    "instruction": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "moves": [
      "…"
    ],
    "may_add_colleague": true
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

<a id="4_get_breach_tickets_ticket_uuid_messages_message_uuid_evidence"></a>
## 4. `GET /breach-tickets/{ticket_uuid}/messages/{message_uuid}/evidence` — Download a file attached to a message on my breach ticket

### API

- **Operation ID:** `my_ticket_file_breach_tickets__ticket_uuid__messages__message_uuid__evidence_get`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |
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

<a id="5_post_breach_tickets_ticket_uuid_colleagues"></a>
## 5. `POST /breach-tickets/{ticket_uuid}/colleagues` — Bring a colleague into my breach ticket: they get their own

### API

- **Operation ID:** `add_colleague_breach_tickets__ticket_uuid__colleagues_post`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

The answer is your own ticket whatever happened to theirs, so it says
nothing about whether an address has an account.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ColleagueIn`](#schema-colleaguein)

```json
{
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MyBreachTicketDetailOut`](#schema-mybreachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "breach_reference": "string",
    "instruction": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "moves": [
      "…"
    ],
    "may_add_colleague": true
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

<a id="6_post_breach_tickets_ticket_uuid_return"></a>
## 6. `POST /breach-tickets/{ticket_uuid}/return` — Return my breach ticket: what was done, and how it went

### API

- **Operation ID:** `return_my_breach_ticket_breach_tickets__ticket_uuid__return_post`
- **Access:** Role-controlled `breach tickets` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_return_my_breach_ticket_breach_tickets__ticket_uuid__return_post`](#schema-body_return_my_breach_ticket_breach_tickets_ticket_uuid_return_post)

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
| `200` | Successful Response | `application/json` | [`MyBreachTicketDetailOut`](#schema-mybreachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "breach_reference": "string",
    "instruction": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "moves": [
      "…"
    ],
    "may_add_colleague": true
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

# Referenced schemas

<a id="schema-body_message_office_breach_tickets_ticket_uuid_messages_post"></a>
#### `Body_message_office_breach_tickets__ticket_uuid__messages_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `body` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional file, max 25 MB |

<a id="schema-body_return_my_breach_ticket_breach_tickets_ticket_uuid_return_post"></a>
#### `Body_return_my_breach_ticket_breach_tickets__ticket_uuid__return_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `summary` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `outcome` | `string` | Yes | — | done, partial or failed |
| `evidence` | `string` or `null` | No | — | Optional evidence, max 25 MB |

<a id="schema-colleaguein"></a>
#### `ColleagueIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` or `null` | No | max length: `200` | — |
| `email` | `string` | Yes | min length: `3`; max length: `320` | — |
| `mobile` | `string` or `null` | No | max length: `32` | — |
| `note` | `string` | Yes | min length: `1`; max length: `20000` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-mybreachticketdetailout"></a>
#### `MyBreachTicketDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket` | [`MyBreachTicketOut`](#schema-mybreachticketout) | Yes | — | — |
| `messages` | array of [`BreachTicketMessageOut`](#schema-breachticketmessageout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-mybreachticketout"></a>
#### `MyBreachTicketOut`

Exactly what a holder is given (BD-13), and nothing else.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket_uuid` | `string` | Yes | format: `uuid` | — |
| `breach_reference` | `string` | Yes | — | — |
| `instruction` | `string` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `answer_by` | `string` or `null` | Yes | format: `date` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `unread` | `integer` | Yes | — | — |
| `last_activity_at` | `string` or `null` | Yes | format: `date-time` | — |
| `moves` | array of [`BreachTicketMoveOut`](#schema-breachticketmoveout) | Yes | — | — |
| `may_add_colleague` | `boolean` | Yes | — | — |

<a id="schema-breachticketmessageout"></a>
#### `BreachTicketMessageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `message_uuid` | `string` | Yes | format: `uuid` | — |
| `author_side` | `string` | Yes | — | — |
| `author_name` | `string` or `null` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `body` | `string` | Yes | — | — |
| `evidence_hash` | `string` or `null` | Yes | — | — |
| `evidence_name` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-breachticketmoveout"></a>
#### `BreachTicketMoveOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `move` | `string` | Yes | — | — |
| `reason_required` | `boolean` | Yes | — | — |
