# Breach Settings API

Generated from `backend/api/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /breach-settings`](#1_get_breach_settings)
2. [`PUT /breach-settings/intake-roles`](#2_put_breach_settings_intake_roles)
3. [`POST /breach-settings/board-recipients`](#3_post_breach_settings_board_recipients)
4. [`DELETE /breach-settings/board-recipients/{recipient_uuid}`](#4_delete_breach_settings_board_recipients_recipient_uuid)
5. [`PUT /breach-settings/board-recipients/{recipient_uuid}/mandatory`](#5_put_breach_settings_board_recipients_recipient_uuid_mandatory)

<a id="1_get_breach_settings"></a>
## 1. `GET /breach-settings` — Who hears of a breach, and how

### API

- **Operation ID:** `get_settings_breach_settings_get`
- **Access:** Role-controlled `breach settings` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachSettingsOut`](#schema-breachsettingsout) |

**Example `200` `application/json` response:**

```json
{
  "intake_roles": [
    "string"
  ],
  "roles": [
    {
      "role": "string",
      "title": "string"
    }
  ],
  "officers": [
    "string"
  ],
  "board_recipients": [
    {
      "recipient_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…",
      "mandatory": true,
      "mandatory_changed_at": "…",
      "mandatory_changed_by_name": "…"
    }
  ],
  "report_link": "string"
}
```

<a id="2_put_breach_settings_intake_roles"></a>
## 2. `PUT /breach-settings/intake-roles` — Which roles are told of a report from the public link

### API

- **Operation ID:** `set_intake_roles_breach_settings_intake_roles_put`
- **Access:** Role-controlled `breach settings` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`IntakeRolesIn`](#schema-intakerolesin)

```json
{
  "roles": [
    "string"
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachSettingsOut`](#schema-breachsettingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "intake_roles": [
    "string"
  ],
  "roles": [
    {
      "role": "string",
      "title": "string"
    }
  ],
  "officers": [
    "string"
  ],
  "board_recipients": [
    {
      "recipient_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…",
      "mandatory": true,
      "mandatory_changed_at": "…",
      "mandatory_changed_by_name": "…"
    }
  ],
  "report_link": "string"
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

<a id="3_post_breach_settings_board_recipients"></a>
## 3. `POST /breach-settings/board-recipients` — Add an address to the organisation's board

### API

- **Operation ID:** `add_board_recipient_breach_settings_board_recipients_post`
- **Access:** Role-controlled `breach settings` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BoardRecipientIn`](#schema-boardrecipientin)

```json
{
  "full_name": "string",
  "email": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachSettingsOut`](#schema-breachsettingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "intake_roles": [
    "string"
  ],
  "roles": [
    {
      "role": "string",
      "title": "string"
    }
  ],
  "officers": [
    "string"
  ],
  "board_recipients": [
    {
      "recipient_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…",
      "mandatory": true,
      "mandatory_changed_at": "…",
      "mandatory_changed_by_name": "…"
    }
  ],
  "report_link": "string"
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

<a id="4_delete_breach_settings_board_recipients_recipient_uuid"></a>
## 4. `DELETE /breach-settings/board-recipients/{recipient_uuid}` — Take an address off the organisation's board

### API

- **Operation ID:** `remove_board_recipient_breach_settings_board_recipients__recipient_uuid__delete`
- **Access:** Role-controlled `breach settings` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `recipient_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachSettingsOut`](#schema-breachsettingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "intake_roles": [
    "string"
  ],
  "roles": [
    {
      "role": "string",
      "title": "string"
    }
  ],
  "officers": [
    "string"
  ],
  "board_recipients": [
    {
      "recipient_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…",
      "mandatory": true,
      "mandatory_changed_at": "…",
      "mandatory_changed_by_name": "…"
    }
  ],
  "report_link": "string"
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

<a id="5_put_breach_settings_board_recipients_recipient_uuid_mandatory"></a>
## 5. `PUT /breach-settings/board-recipients/{recipient_uuid}/mandatory` — Make an address on the organisation's board mandatory, or optional again

### API

- **Operation ID:** `set_board_recipient_mandatory_breach_settings_board_recipients__recipient_uuid__mandatory_put`
- **Access:** Role-controlled `breach settings` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `recipient_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BoardRecipientMandatoryIn`](#schema-boardrecipientmandatoryin)

```json
{
  "mandatory": true
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachSettingsOut`](#schema-breachsettingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "intake_roles": [
    "string"
  ],
  "roles": [
    {
      "role": "string",
      "title": "string"
    }
  ],
  "officers": [
    "string"
  ],
  "board_recipients": [
    {
      "recipient_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…",
      "mandatory": true,
      "mandatory_changed_at": "…",
      "mandatory_changed_by_name": "…"
    }
  ],
  "report_link": "string"
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

<a id="schema-boardrecipientin"></a>
#### `BoardRecipientIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` or `null` | No | max length: `200` | — |
| `email` | `string` | Yes | min length: `3`; max length: `255` | — |

<a id="schema-boardrecipientmandatoryin"></a>
#### `BoardRecipientMandatoryIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `mandatory` | `boolean` | Yes | — | — |

<a id="schema-breachsettingsout"></a>
#### `BreachSettingsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `intake_roles` | array of `string` | Yes | — | — |
| `roles` | array of [`BreachRoleOut`](#schema-breachroleout) | Yes | — | — |
| `officers` | array of `string` | Yes | — | — |
| `board_recipients` | array of [`BoardRecipientOut`](#schema-boardrecipientout) | Yes | — | — |
| `report_link` | `string` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-intakerolesin"></a>
#### `IntakeRolesIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `roles` | array of `string` | Yes | — | — |

<a id="schema-breachroleout"></a>
#### `BreachRoleOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `role` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |

<a id="schema-boardrecipientout"></a>
#### `BoardRecipientOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `recipient_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |
| `email` | `string` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |
| `mandatory` | `boolean` | Yes | — | — |
| `mandatory_changed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `mandatory_changed_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
