# Public Consent API

Generated from `backend/api/openapi.json`. **6 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /c/{token}`](#1_get_c_token)
2. [`POST /c/{token}/register`](#2_post_c_token_register)
3. [`POST /c/{token}/otp`](#3_post_c_token_otp)
4. [`POST /c/{token}/otp/verify`](#4_post_c_token_otp_verify)
5. [`GET /c/{token}/notice`](#5_get_c_token_notice)
6. [`POST /c/{token}/consent`](#6_post_c_token_consent)

<a id="1_get_c_token"></a>
## 1. `GET /c/{token}` — Validate the link

### API

- **Operation ID:** `open_link_c__token__get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

An invalid link returns a plain message and renders no notice content.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`LinkView`](#schema-linkview) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "valid": true,
  "project_name": "string",
  "site_label": "string",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "available_languages": [
    "string"
  ],
  "already_registered": false
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

<a id="2_post_c_token_register"></a>
## 2. `POST /c/{token}/register` — Register

### API

- **Operation ID:** `register_c__token__register_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Create the person and set `registered_via_link_id`.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`cmp__api__routers__public__consent__RegisterBody`](#schema-cmp_api_routers_public_consent_registerbody)

```json
{
  "full_name": "string",
  "mobile": "string",
  "email": "string",
  "organization_id": "string",
  "person_type": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

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

<a id="3_post_c_token_otp"></a>
## 3. `POST /c/{token}/otp` — 6-digit code, 10 minutes

### API

- **Operation ID:** `request_code_c__token__otp_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`OtpBody`](#schema-otpbody)

```json
{
  "contact": "string"
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

<a id="4_post_c_token_otp_verify"></a>
## 4. `POST /c/{token}/otp/verify` — 5 attempts, then the code is discarded

### API

- **Operation ID:** `verify_code_c__token__otp_verify_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Establishes the subject session that `POST /c/{token}/consent` relies on.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`OtpVerifyBody`](#schema-otpverifybody)

```json
{
  "contact": "string",
  "code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ContactVerified`](#schema-contactverified) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string",
  "complete": true,
  "remaining": [
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

<a id="5_get_c_token_notice"></a>
## 5. `GET /c/{token}/notice` — Render the notice - stamps served_at

### API

- **Operation ID:** `serve_notice_c__token__notice_get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Renders the text and records, on the server, that it was served.

The `served_at` in the response is informational. The consent call does
not take it back: the server keeps its own record of the serving, bound to
the person, the link and the rendition, and refuses a consent for which
there is none. A client-supplied timestamp could claim the notice was
shown at any convenient moment, and s.5(1) would become unfalsifiable.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |
| `language_code` | query | No | `string` | default: `english` | — |

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

<a id="6_post_c_token_consent"></a>
## 6. `POST /c/{token}/consent` — Give Consent

### API

- **Operation ID:** `give_consent_c__token__consent_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Write the artefact and its grants.

The subject is taken from the session, never from the body.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | min length: `20`; max length: `64`; pattern: `^[A-Za-z0-9_-]+$` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ConsentBody`](#schema-consentbody)

```json
{
  "language_code": "string",
  "served_at": "2026-09-17T12:00:00Z",
  "grants": {},
  "action_type": "checkbox_click"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-consentbody"></a>
#### `ConsentBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `language_code` | `string` | Yes | — | — |
| `served_at` | `string` or `null` | No | format: `date-time` | Ignored. The server records when it served the notice. |
| `grants` | `object` | Yes | — | Every purpose on the notice must carry an explicit answer |
| `action_type` | `string` | No | default: `checkbox_click` | — |

<a id="schema-contactverified"></a>
#### `ContactVerified`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |
| `complete` | `boolean` | No | default: `True` | — |
| `remaining` | array of `string` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-linkview"></a>
#### `LinkView`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `valid` | `boolean` | Yes | — | — |
| `project_name` | `string` | Yes | — | — |
| `site_label` | `string` | Yes | — | — |
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `available_languages` | array of `string` | Yes | — | — |
| `already_registered` | `boolean` | No | default: `False` | — |

<a id="schema-otpbody"></a>
#### `OtpBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |

<a id="schema-otpverifybody"></a>
#### `OtpVerifyBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-cmp_api_routers_public_consent_registerbody"></a>
#### `cmp__api__routers__public__consent__RegisterBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `mobile` | `string` | Yes | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `email` | `string` or `null` | No | format: `email` | — |
| `organization_id` | `string` or `null` | No | max length: `60` | — |
| `person_type` | `string` or `null` | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
