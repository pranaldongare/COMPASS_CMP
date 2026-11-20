# Breach Notices API

Generated from `backend/api/openapi.json`. **3 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /breach-notices/{token}`](#1_get_breach_notices_token)
2. [`POST /breach-notices/{token}/code`](#2_post_breach_notices_token_code)
3. [`POST /breach-notices/{token}/open`](#3_post_breach_notices_token_open)

<a id="1_get_breach_notices_token"></a>
## 1. `GET /breach-notices/{token}` — What the link opens, before the code

### API

- **Operation ID:** `open_link_breach_notices__token__get`
- **Access:** Role-controlled `breach notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `64`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticeLinkOut`](#schema-breachnoticelinkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "reference": "string",
  "code_goes_to": "string"
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

<a id="2_post_breach_notices_token_code"></a>
## 2. `POST /breach-notices/{token}/code` — Send a code to the mobile

### API

- **Operation ID:** `send_code_breach_notices__token__code_post`
- **Access:** Role-controlled `breach notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `64`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

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

<a id="3_post_breach_notices_token_open"></a>
## 3. `POST /breach-notices/{token}/open` — Enter the code: the notice

### API

- **Operation ID:** `open_notice_breach_notices__token__open_post`
- **Access:** Role-controlled `breach notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `64`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachNoticeCodeIn`](#schema-breachnoticecodein)

```json
{
  "code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticeByLinkOut`](#schema-breachnoticebylinkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "reference": "string",
  "version": 1,
  "approved_at": "2026-09-17T12:00:00Z",
  "what_happened": "string",
  "consequences": "string",
  "measures": "string",
  "protective_steps": "string",
  "contact": "string"
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

<a id="schema-breachnoticebylinkout"></a>
#### `BreachNoticeByLinkOut`

The notice, in full: the five things Rule 7(1) requires.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `approved_at` | `string` or `null` | Yes | format: `date-time` | — |
| `what_happened` | `string` | Yes | — | — |
| `consequences` | `string` | Yes | — | — |
| `measures` | `string` | Yes | — | — |
| `protective_steps` | `string` | Yes | — | — |
| `contact` | `string` | Yes | — | — |

<a id="schema-breachnoticecodein"></a>
#### `BreachNoticeCodeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-breachnoticelinkout"></a>
#### `BreachNoticeLinkOut`

What the link alone shows.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `code_goes_to` | `string` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
