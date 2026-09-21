# Public Information API

Generated from `backend/api/openapi.json`. **10 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /notice/{notice_uuid}`](#1_get_notice_notice_uuid)
2. [`GET /rights`](#2_get_rights)
3. [`POST /rights/requests`](#3_post_rights_requests)
4. [`POST /rights/requests/verify`](#4_post_rights_requests_verify)
5. [`GET /rights/nominations/{token}`](#5_get_rights_nominations_token)
6. [`POST /rights/nominations/{token}/code`](#6_post_rights_nominations_token_code)
7. [`POST /rights/nominations/{token}/accept`](#7_post_rights_nominations_token_accept)
8. [`POST /rights/nominations/{token}/decline`](#8_post_rights_nominations_token_decline)
9. [`POST /rights/nominee/start`](#9_post_rights_nominee_start)
10. [`POST /rights/nominee/requests`](#10_post_rights_nominee_requests)

<a id="1_get_notice_notice_uuid"></a>
## 1. `GET /notice/{notice_uuid}` — Public notice viewer

### API

- **Operation ID:** `public_notice_notice__notice_uuid__get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

A published notice is a public document. Drafts are not visible here.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
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

<a id="2_get_rights"></a>
## 2. `GET /rights` — How to make a rights request - Rule 9, Rule 14(1)

### API

- **Operation ID:** `rights_rights_get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Published so a data subject who has lost her notice can still find us.

The Board complaint route is stated alongside ours, not instead of it: telling
someone only about the internal grievance process misstates the remedy
available to her.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |

**Example `200` `application/json` response:**

```json
{}
```

<a id="3_post_rights_requests"></a>
## 3. `POST /rights/requests` — Make a request without an account

### API

- **Operation ID:** `public_request_rights_requests_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Recorded either way. A code goes to the channel we already hold - if we hold one.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PublicRequestIn`](#schema-publicrequestin)

```json
{
  "request_type": "string",
  "contact": "string",
  "name": "string",
  "request_text": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`PublicRequestOut`](#schema-publicrequestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "reference": "string",
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

<a id="4_post_rights_requests_verify"></a>
## 4. `POST /rights/requests/verify` — Confirm the code

### API

- **Operation ID:** `public_verify_rights_requests_verify_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PublicVerifyIn`](#schema-publicverifyin)

```json
{
  "reference": "string",
  "code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PublicVerifyOut`](#schema-publicverifyout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "reference": "string",
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

<a id="5_get_rights_nominations_token"></a>
## 5. `GET /rights/nominations/{token}` — The acceptance link

### API

- **Operation ID:** `nomination_view_rights_nominations__token__get`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

What he is being asked to accept. Every failure is the same 404.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | — | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`NominationView`](#schema-nominationview) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "principal_name": "string",
  "nominee_name": "string",
  "rights": [
    "string"
  ],
  "accept_expires_at": "string",
  "mediums": [
    {}
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

<a id="6_post_rights_nominations_token_code"></a>
## 6. `POST /rights/nominations/{token}/code` — A code to one of the contacts recorded on the nomination

### API

- **Operation ID:** `nomination_code_rights_nominations__token__code_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NominationCodeIn`](#schema-nominationcodein)

```json
{
  "medium": "string"
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

<a id="7_post_rights_nominations_token_accept"></a>
## 7. `POST /rights/nominations/{token}/accept` — Accept a nomination

### API

- **Operation ID:** `nomination_accept_rights_nominations__token__accept_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NominationActIn`](#schema-nominationactin)

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

<a id="8_post_rights_nominations_token_decline"></a>
## 8. `POST /rights/nominations/{token}/decline` — Decline a nomination

### API

- **Operation ID:** `nomination_decline_rights_nominations__token__decline_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `token` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NominationActIn`](#schema-nominationactin)

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

<a id="9_post_rights_nominee_start"></a>
## 9. `POST /rights/nominee/start` — A nominee identifies himself

### API

- **Operation ID:** `nominee_start_rights_nominee_start_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

The code goes to the contact *she* recorded, not the one he types now.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NomineeStartIn`](#schema-nomineestartin)

```json
{
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
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

<a id="10_post_rights_nominee_requests"></a>
## 10. `POST /rights/nominee/requests` — A nominee makes a request on her behalf

### API

- **Operation ID:** `nominee_request_rights_nominee_requests_post`
- **Access:** Public or operator endpoint; see the endpoint description and deployment controls.

Runs as normal once the DPO has decided the event is evidenced.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_nominee_request_rights_nominee_requests_post`](#schema-body_nominee_request_rights_nominee_requests_post)

```json
{
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "code": "string",
  "request_type": "string",
  "request_text": "string",
  "trigger_event": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`NomineeRequestOut`](#schema-nomineerequestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "reference": "string",
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

<a id="schema-body_nominee_request_rights_nominee_requests_post"></a>
#### `Body_nominee_request_rights_nominee_requests_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `nomination_uuid` | `string` | Yes | format: `uuid` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10` | — |
| `request_type` | `string` | Yes | — | — |
| `request_text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `trigger_event` | `string` | Yes | — | — |
| `evidence` | `string` or `null` | No | — | Evidence of death or incapacity |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-nominationactin"></a>
#### `NominationActIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-nominationcodein"></a>
#### `NominationCodeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `medium` | `string` | Yes | — | — |

<a id="schema-nominationview"></a>
#### `NominationView`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `nomination_uuid` | `string` | Yes | format: `uuid` | — |
| `principal_name` | `string` | Yes | — | — |
| `nominee_name` | `string` | Yes | — | — |
| `rights` | array of `string` | Yes | — | — |
| `accept_expires_at` | `object` | Yes | — | — |
| `mediums` | array of `object` | Yes | — | — |

<a id="schema-nomineerequestout"></a>
#### `NomineeRequestOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `message` | `string` | Yes | — | — |

<a id="schema-nomineestartin"></a>
#### `NomineeStartIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `nomination_uuid` | `string` | Yes | format: `uuid` | — |
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |

<a id="schema-publicrequestin"></a>
#### `PublicRequestIn`

From the notice link. Nothing here identifies anyone to the caller.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_type` | `string` | Yes | — | — |
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `request_text` | `string` | Yes | min length: `1`; max length: `20000` | — |

<a id="schema-publicrequestout"></a>
#### `PublicRequestOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
| `message` | `string` | Yes | — | — |

<a id="schema-publicverifyin"></a>
#### `PublicVerifyIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | min length: `6`; max length: `24` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-publicverifyout"></a>
#### `PublicVerifyOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | Yes | — | — |
| `reference` | `string` | Yes | — | — |
| `message` | `string` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
