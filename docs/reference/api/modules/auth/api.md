# Auth API

Generated from `backend/api/openapi.json`. **14 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`POST /auth/login`](#1_post_auth_login)
2. [`POST /auth/mfa/verify`](#2_post_auth_mfa_verify)
3. [`POST /auth/mfa/resend`](#3_post_auth_mfa_resend)
4. [`POST /auth/register`](#4_post_auth_register)
5. [`POST /auth/otp/request`](#5_post_auth_otp_request)
6. [`POST /auth/register/verify`](#6_post_auth_register_verify)
7. [`POST /auth/otp/verify`](#7_post_auth_otp_verify)
8. [`POST /auth/logout`](#8_post_auth_logout)
9. [`GET /auth/me`](#9_get_auth_me)
10. [`POST /auth/password/change`](#10_post_auth_password_change)
11. [`POST /auth/password/reset/request`](#11_post_auth_password_reset_request)
12. [`POST /auth/password/reset/confirm`](#12_post_auth_password_reset_confirm)
13. [`GET /auth/sessions`](#13_get_auth_sessions)
14. [`DELETE /auth/sessions/{session_uuid}`](#14_delete_auth_sessions_session_uuid)

<a id="1_post_auth_login"></a>
## 1. `POST /auth/login` — Staff sign-in

### API

- **Operation ID:** `login_auth_login_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`LoginRequest`](#schema-loginrequest)

```json
{
  "login": "string",
  "password": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`LoginResponse`](#schema-loginresponse) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "mfa_required": true,
  "user_uuid": "00000000-0000-4000-8000-000000000000",
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

<a id="2_post_auth_mfa_verify"></a>
## 2. `POST /auth/mfa/verify` — Complete stepped-up sign-in

### API

- **Operation ID:** `mfa_verify_auth_mfa_verify_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`MfaVerifyRequest`](#schema-mfaverifyrequest)

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

<a id="3_post_auth_mfa_resend"></a>
## 3. `POST /auth/mfa/resend` — Resend the MFA code

### API

- **Operation ID:** `mfa_resend_auth_mfa_resend_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string"
}
```

<a id="4_post_auth_register"></a>
## 4. `POST /auth/register` — Data-subject self-registration

### API

- **Operation ID:** `register_auth_register_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

Create a data-principal account and send a sign-in code.

202 rather than 201: the account is not usable until the code is verified,
and returning 201 Created would tell an unauthenticated caller that this
contact was new - which is the one thing the identical response below is
there to withhold.

Staff accounts are not created this way. An administrator invites them, and
this endpoint writes the role itself rather than reading it.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`cmp__api__routers__v1__auth__RegisterBody`](#schema-cmp_api_routers_v1_auth_registerbody)

```json
{
  "full_name": "string",
  "mobile": "string",
  "dob": "2026-09-17",
  "email": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `202` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `202` `application/json` response:**

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

<a id="5_post_auth_otp_request"></a>
## 5. `POST /auth/otp/request` — Data-subject sign-in code

### API

- **Operation ID:** `otp_request_auth_otp_request_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`OtpRequestBody`](#schema-otprequestbody)

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

<a id="6_post_auth_register_verify"></a>
## 6. `POST /auth/register/verify` — Finish sign-up: every medium given answers with its code

### API

- **Operation ID:** `register_verify_auth_register_verify_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RegisterVerifyBody`](#schema-registerverifybody)

```json
{
  "mobile": "string",
  "mobile_code": "string",
  "email_code": "string"
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

<a id="7_post_auth_otp_verify"></a>
## 7. `POST /auth/otp/verify` — Data-subject sign-in

### API

- **Operation ID:** `otp_verify_auth_otp_verify_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

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

<a id="8_post_auth_logout"></a>
## 8. `POST /auth/logout` — End this session

### API

- **Operation ID:** `logout_auth_logout_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string"
}
```

<a id="9_get_auth_me"></a>
## 9. `GET /auth/me` — Who is signed in

### API

- **Operation ID:** `me_auth_me_get`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

The endpoint the SPA cannot work without.

Identity, role, permitted navigation and session expiry. Without it React
cannot decide what to render on first paint, and every other call becomes
guesswork.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MeResponse`](#schema-meresponse) |

**Example `200` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "secondary_email": "string",
  "mobile_verified_at": "2026-09-17T12:00:00Z",
  "email_verified_at": "2026-09-17T12:00:00Z",
  "secondary_email_verified_at": "2026-09-17T12:00:00Z",
  "role": "string",
  "account_role": "string",
  "person_type": "string",
  "status": "string",
  "dob": "string",
  "is_minor": true,
  "mfa_verified": true,
  "session_expires_at": "2026-09-17T12:00:00Z",
  "nav": [
    "string"
  ],
  "writes": [
    "string"
  ]
}
```

<a id="10_post_auth_password_change"></a>
## 10. `POST /auth/password/change` — Password Change

### API

- **Operation ID:** `password_change_auth_password_change_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PasswordChange`](#schema-passwordchange)

```json
{
  "current_password": "string",
  "new_password": "string"
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

<a id="11_post_auth_password_reset_request"></a>
## 11. `POST /auth/password/reset/request` — Password Reset Request

### API

- **Operation ID:** `password_reset_request_auth_password_reset_request_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ResetRequest`](#schema-resetrequest)

```json
{
  "email": "string"
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

<a id="12_post_auth_password_reset_confirm"></a>
## 12. `POST /auth/password/reset/confirm` — Password Reset Confirm

### API

- **Operation ID:** `password_reset_confirm_auth_password_reset_confirm_post`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ResetConfirm`](#schema-resetconfirm)

```json
{
  "email": "string",
  "code": "string",
  "new_password": "string"
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

<a id="13_get_auth_sessions"></a>
## 13. `GET /auth/sessions` — Your active sessions

### API

- **Operation ID:** `list_sessions_auth_sessions_get`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`SessionInfo`](#schema-sessioninfo) |

**Example `200` `application/json` response:**

```json
[
  {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "created_at": "2026-09-17T12:00:00Z",
    "last_seen_at": "2026-09-17T12:00:00Z",
    "expires_at": "2026-09-17T12:00:00Z",
    "ip_address": "string",
    "user_agent": "string",
    "mfa_verified": true,
    "current": false
  }
]
```

<a id="14_delete_auth_sessions_session_uuid"></a>
## 14. `DELETE /auth/sessions/{session_uuid}` — Revoke one of your sessions

### API

- **Operation ID:** `revoke_session_auth_sessions__session_uuid__delete`
- **Access:** Authentication endpoint; availability depends on the current sign-in or recovery step.

Scoped to the caller's own sessions.

Without the ownership predicate, knowing a session uuid would be enough to
sign anybody out.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `session_uuid` | path | Yes | `string` | format: `uuid` | — |

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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-loginrequest"></a>
#### `LoginRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `login` | `string` | Yes | min length: `3`; max length: `255` | Email or username |
| `password` | `string` | Yes | min length: `1`; max length: `128` | — |

<a id="schema-loginresponse"></a>
#### `LoginResponse`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `mfa_required` | `boolean` | Yes | — | — |
| `user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `message` | `string` | Yes | — | — |

<a id="schema-meresponse"></a>
#### `MeResponse`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` | Yes | — | — |
| `email` | `string` or `null` | Yes | — | — |
| `mobile` | `string` or `null` | No | — | — |
| `secondary_email` | `string` or `null` | Yes | — | — |
| `mobile_verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `email_verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `secondary_email_verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `role` | `string` | Yes | — | — |
| `account_role` | `string` | Yes | — | — |
| `person_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `dob` | `string` or `null` | No | — | — |
| `is_minor` | `boolean` or `null` | No | — | — |
| `mfa_verified` | `boolean` | Yes | — | — |
| `session_expires_at` | `string` | Yes | format: `date-time` | — |
| `nav` | array of `string` | Yes | — | — |
| `writes` | array of `string` | No | — | — |

<a id="schema-mfaverifyrequest"></a>
#### `MfaVerifyRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-otprequestbody"></a>
#### `OtpRequestBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | Registered email or mobile |

<a id="schema-otpverifybody"></a>
#### `OtpVerifyBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-passwordchange"></a>
#### `PasswordChange`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `current_password` | `string` | Yes | min length: `1`; max length: `128` | — |
| `new_password` | `string` | Yes | min length: `12`; max length: `128` | — |

<a id="schema-registerverifybody"></a>
#### `RegisterVerifyBody`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `mobile` | `string` | Yes | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `mobile_code` | `string` or `null` | No | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |
| `email_code` | `string` or `null` | No | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-resetconfirm"></a>
#### `ResetConfirm`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `email` | `string` | Yes | format: `email` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |
| `new_password` | `string` | Yes | min length: `12`; max length: `128` | — |

<a id="schema-resetrequest"></a>
#### `ResetRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `email` | `string` | Yes | format: `email` | — |

<a id="schema-cmp_api_routers_v1_auth_registerbody"></a>
#### `cmp__api__routers__v1__auth__RegisterBody`

Self-registration. Note what is *not* here: a role.

The role is written by the service as `data_subject`. Accepting one from an
unauthenticated body is how a sign-up form becomes a way to mint a DPO.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` | Yes | min length: `2`; max length: `120` | — |
| `mobile` | `string` | Yes | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `dob` | `string` | Yes | format: `date` | Date of birth, YYYY-MM-DD |
| `email` | `string` or `null` | No | format: `email` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
