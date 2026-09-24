# Delegations API

Generated from `backend/api/openapi.json`. **6 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /delegations/candidates`](#1_get_delegations_candidates)
2. [`GET /delegations`](#2_get_delegations)
3. [`POST /delegations`](#3_post_delegations)
4. [`DELETE /delegations/{delegation_uuid}`](#4_delete_delegations_delegation_uuid)
5. [`GET /delegations/mine`](#5_get_delegations_mine)
6. [`GET /delegations/held`](#6_get_delegations_held)

<a id="1_get_delegations_candidates"></a>
## 1. `GET /delegations/candidates` — Who I can hand my work to: the active accounts in my role

### API

- **Operation ID:** `candidates_delegations_candidates_get`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

The cover form's one question, answered for whoever may arrange cover.

It used to read the users register, which only the DPO and the
administrator may - so everyone else was told there was nobody to delegate
to. Same role, active, not the caller: the rules `grant` enforces.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CoverCandidateOut`](#schema-covercandidateout) |

**Example `200` `application/json` response:**

```json
[
  {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "full_name": "string",
    "email": "string"
  }
]
```

<a id="2_get_delegations"></a>
## 2. `GET /delegations` — Every live arrangement

### API

- **Operation ID:** `current_delegations_get`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

Who is covering what, right now.

Restricted to DPO and administrator: it names who is standing in for whom
across the organisation, which is oversight rather than everyday work.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`DelegationOut`](#schema-delegationout) |

**Example `200` `application/json` response:**

```json
[
  {
    "delegation_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_name": "string",
    "delegator_email": "string",
    "delegator_role": "string",
    "delegate_uuid": "00000000-0000-4000-8000-000000000000",
    "delegate_name": "string",
    "delegate_email": "string",
    "delegate_role": "string",
    "reason": "string",
    "starts_at": "2026-09-17T12:00:00Z",
    "ends_at": "2026-09-17T12:00:00Z",
    "revoked_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "is_active": true
  }
]
```

<a id="3_post_delegations"></a>
## 3. `POST /delegations` — Arrange cover

### API

- **Operation ID:** `grant_delegations_post`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

Arrange for somebody to cover your work, in the same role.

Same role only, and only for yourself unless you are an administrator. Both
rules are in the service, with the reasoning; the short version is that
either one relaxed turns this into a way to acquire access rather than a way
to hand it over.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`DelegationIn`](#schema-delegationin)

```json
{
  "delegate_user_uuid": "00000000-0000-4000-8000-000000000000",
  "delegator_user_uuid": "00000000-0000-4000-8000-000000000000",
  "reason": "string",
  "starts_at": "2026-09-17T12:00:00Z",
  "ends_at": "2026-09-17T12:00:00Z"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`DelegationGranted`](#schema-delegationgranted) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "delegation_uuid": "00000000-0000-4000-8000-000000000000",
  "grants_access": true,
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

<a id="4_delete_delegations_delegation_uuid"></a>
## 4. `DELETE /delegations/{delegation_uuid}` — End cover now

### API

- **Operation ID:** `revoke_delegations__delegation_uuid__delete`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

Either party may end it, and so may an administrator.

The delegate as well as the delegator, because being handed access one does
not want is a real situation and refusing it should not need a ticket.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `delegation_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="5_get_delegations_mine"></a>
## 5. `GET /delegations/mine` — Cover I have arranged

### API

- **Operation ID:** `mine_delegations_mine_get`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

Arrangements where the caller is the one being covered for.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`DelegationOut`](#schema-delegationout) |

**Example `200` `application/json` response:**

```json
[
  {
    "delegation_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_name": "string",
    "delegator_email": "string",
    "delegator_role": "string",
    "delegate_uuid": "00000000-0000-4000-8000-000000000000",
    "delegate_name": "string",
    "delegate_email": "string",
    "delegate_role": "string",
    "reason": "string",
    "starts_at": "2026-09-17T12:00:00Z",
    "ends_at": "2026-09-17T12:00:00Z",
    "revoked_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "is_active": true
  }
]
```

<a id="6_get_delegations_held"></a>
## 6. `GET /delegations/held` — Cover I am providing

### API

- **Operation ID:** `held_delegations_held_get`
- **Access:** Role-controlled `delegations` operation. See [`../../roles/README.md`](../../roles/README.md).

Arrangements where the caller is the one covering.

Worth its own endpoint rather than a filter: "whose work am I answerable for
this week" is a different question from "who is covering mine", and somebody
asking it is usually about to act on somebody else's rows.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`DelegationOut`](#schema-delegationout) |

**Example `200` `application/json` response:**

```json
[
  {
    "delegation_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_uuid": "00000000-0000-4000-8000-000000000000",
    "delegator_name": "string",
    "delegator_email": "string",
    "delegator_role": "string",
    "delegate_uuid": "00000000-0000-4000-8000-000000000000",
    "delegate_name": "string",
    "delegate_email": "string",
    "delegate_role": "string",
    "reason": "string",
    "starts_at": "2026-09-17T12:00:00Z",
    "ends_at": "2026-09-17T12:00:00Z",
    "revoked_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "is_active": true
  }
]
```

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-delegationgranted"></a>
#### `DelegationGranted`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `delegation_uuid` | `string` | Yes | format: `uuid` | — |
| `grants_access` | `boolean` | Yes | — | — |
| `message` | `string` | Yes | — | — |

<a id="schema-delegationin"></a>
#### `DelegationIn`

Who is covering for whom, and until when.

`delegator_user_uuid` is optional and defaults to the caller: the common
case is arranging your own cover, and making the caller name themselves is a
step that only exists to be got wrong. An administrator arranging cover for
somebody already unreachable names them explicitly.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `delegate_user_uuid` | `string` | Yes | format: `uuid` | — |
| `delegator_user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `reason` | `string` or `null` | No | max length: `1000` | — |
| `starts_at` | `string` or `null` | No | format: `date-time` | — |
| `ends_at` | `string` or `null` | No | format: `date-time` | — |

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
