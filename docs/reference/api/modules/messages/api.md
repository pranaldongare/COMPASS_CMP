# Messages API

Generated from `backend/api/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /messages`](#1_get_messages)
2. [`GET /messages/{key}`](#2_get_messages_key)
3. [`POST /messages/{key}/{channel}/preview`](#3_post_messages_key_channel_preview)
4. [`PUT /messages/{key}/{channel}`](#4_put_messages_key_channel)
5. [`DELETE /messages/{key}/{channel}`](#5_delete_messages_key_channel)

<a id="1_get_messages"></a>
## 1. `GET /messages` — Every message, with the words in force

### API

- **Operation ID:** `list_messages_messages_get`
- **Access:** Role-controlled `messages` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`cmp__api__routers__v1__messages__MessageOut`](#schema-cmp_api_routers_v1_messages_messageout) |

**Example `200` `application/json` response:**

```json
[
  {
    "key": "string",
    "title": "string",
    "description": "string",
    "group": "string",
    "variables": [
      {
        "name": "…",
        "description": "…",
        "sample": "…"
      }
    ],
    "channels": [
      {
        "channel": "…",
        "default_subject": "…",
        "default_body": "…",
        "subject": "…",
        "body": "…",
        "customised": "…",
        "updated_at": "…",
        "updated_by_name": "…"
      }
    ]
  }
]
```

<a id="2_get_messages_key"></a>
## 2. `GET /messages/{key}` — One message

### API

- **Operation ID:** `get_message_messages__key__get`
- **Access:** Role-controlled `messages` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | pattern: `^[a-z_]{1,64}$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`cmp__api__routers__v1__messages__MessageOut`](#schema-cmp_api_routers_v1_messages_messageout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "key": "string",
  "title": "string",
  "description": "string",
  "group": "string",
  "variables": [
    {
      "name": "string",
      "description": "string",
      "sample": "string"
    }
  ],
  "channels": [
    {
      "channel": "string",
      "default_subject": "…",
      "default_body": "string",
      "subject": "…",
      "body": "string",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="3_post_messages_key_channel_preview"></a>
## 3. `POST /messages/{key}/{channel}/preview` — Render words with sample values, saving nothing

### API

- **Operation ID:** `preview_message_messages__key___channel__preview_post`
- **Access:** Role-controlled `messages` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | pattern: `^[a-z_]{1,64}$` | — |
| `channel` | path | Yes | `string` | pattern: `^(email|sms)$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplateIn`](#schema-templatein)

```json
{
  "subject": "string",
  "body": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PreviewOut`](#schema-previewout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "channel": "string",
  "subject": "string",
  "body": "string"
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

<a id="4_put_messages_key_channel"></a>
## 4. `PUT /messages/{key}/{channel}` — Replace the words

### API

- **Operation ID:** `save_message_messages__key___channel__put`
- **Access:** Role-controlled `messages` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | pattern: `^[a-z_]{1,64}$` | — |
| `channel` | path | Yes | `string` | pattern: `^(email|sms)$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplateIn`](#schema-templatein)

```json
{
  "subject": "string",
  "body": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`cmp__api__routers__v1__messages__MessageOut`](#schema-cmp_api_routers_v1_messages_messageout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "key": "string",
  "title": "string",
  "description": "string",
  "group": "string",
  "variables": [
    {
      "name": "string",
      "description": "string",
      "sample": "string"
    }
  ],
  "channels": [
    {
      "channel": "string",
      "default_subject": "…",
      "default_body": "string",
      "subject": "…",
      "body": "string",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="5_delete_messages_key_channel"></a>
## 5. `DELETE /messages/{key}/{channel}` — Back to the default

### API

- **Operation ID:** `reset_message_messages__key___channel__delete`
- **Access:** Role-controlled `messages` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | pattern: `^[a-z_]{1,64}$` | — |
| `channel` | path | Yes | `string` | pattern: `^(email|sms)$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`cmp__api__routers__v1__messages__MessageOut`](#schema-cmp_api_routers_v1_messages_messageout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "key": "string",
  "title": "string",
  "description": "string",
  "group": "string",
  "variables": [
    {
      "name": "string",
      "description": "string",
      "sample": "string"
    }
  ],
  "channels": [
    {
      "channel": "string",
      "default_subject": "…",
      "default_body": "string",
      "subject": "…",
      "body": "string",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-previewout"></a>
#### `PreviewOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `channel` | `string` | Yes | — | — |
| `subject` | `string` or `null` | Yes | — | — |
| `body` | `string` | Yes | — | — |

<a id="schema-templatein"></a>
#### `TemplateIn`

The words. `subject` is required for email and refused for SMS; the
service says which, with every other problem, in one answer.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `subject` | `string` or `null` | No | max length: `200` | — |
| `body` | `string` | Yes | min length: `1`; max length: `6000` | — |

<a id="schema-cmp_api_routers_v1_messages_messageout"></a>
#### `cmp__api__routers__v1__messages__MessageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |
| `group` | `string` | Yes | — | — |
| `variables` | array of [`VariableOut`](#schema-variableout) | Yes | — | — |
| `channels` | array of [`ChannelOut`](#schema-channelout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-variableout"></a>
#### `VariableOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |
| `sample` | `string` | Yes | — | — |

<a id="schema-channelout"></a>
#### `ChannelOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `channel` | `string` | Yes | — | — |
| `default_subject` | `string` or `null` | Yes | — | — |
| `default_body` | `string` | Yes | — | — |
| `subject` | `string` or `null` | Yes | — | — |
| `body` | `string` | Yes | — | — |
| `customised` | `boolean` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |
