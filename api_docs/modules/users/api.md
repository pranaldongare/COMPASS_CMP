# Users API

Generated from `cmp_backend/openapi.json`. **13 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /users/staff`](#1_get_users_staff)
2. [`GET /users/collection-owners`](#2_get_users_collection_owners)
3. [`GET /users`](#3_get_users)
4. [`POST /users`](#4_post_users)
5. [`POST /users/{user_uuid}/invite`](#5_post_users_user_uuid_invite)
6. [`GET /users/{user_uuid}`](#6_get_users_user_uuid)
7. [`PATCH /users/{user_uuid}`](#7_patch_users_user_uuid)
8. [`POST /users/{user_uuid}/role`](#8_post_users_user_uuid_role)
9. [`POST /users/{user_uuid}/deactivate`](#9_post_users_user_uuid_deactivate)
10. [`POST /users/{user_uuid}/reactivate`](#10_post_users_user_uuid_reactivate)
11. [`DELETE /users/{user_uuid}/sessions`](#11_delete_users_user_uuid_sessions)
12. [`POST /users/{user_uuid}/mfa/reset`](#12_post_users_user_uuid_mfa_reset)
13. [`GET /users/{user_uuid}/person-type-history`](#13_get_users_user_uuid_person_type_history)

<a id="1_get_users_staff"></a>
## 1. `GET /users/staff` — Active staff, for naming a processor's respondent

### API

- **Operation ID:** `staff_directory_users_staff_get`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

Naming who answers a rights-request ticket for an in-house processor
means picking an account. Four fields, active staff only, and only for the
two roles that manage the registry - not a way around the register.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CollectionOwner`](#schema-collectionowner) |

**Example `200` `application/json` response:**

```json
[
  {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "full_name": "string",
    "email": "string",
    "role": "string"
  }
]
```

<a id="2_get_users_collection_owners"></a>
## 2. `GET /users/collection-owners` — Active DCOs and RCOs, for source ownership

### API

- **Operation ID:** `collection_owners_users_collection_owners_get`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

The ownership lookup.

Making somebody accountable for a data source means picking a person, and
the people who do it - a DCO Admin routing a project, an R&D owner naming an
RCO - cannot read the account register. Without this the operation is
unsatisfiable: the form has nothing to offer.

Scoped to exactly what the choice needs - active DCOs and RCOs, four fields -
so it is not a way around the register's own restrictions. Declared before
`/users/{uuid}` so the literal path is matched first.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CollectionOwner`](#schema-collectionowner) |

**Example `200` `application/json` response:**

```json
[
  {
    "uuid": "00000000-0000-4000-8000-000000000000",
    "full_name": "string",
    "email": "string",
    "role": "string"
  }
]
```

<a id="3_get_users"></a>
## 3. `GET /users` — The staff and subject register

### API

- **Operation ID:** `list_users_users_get`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `role` | query | No | `string` or `null` | — | — |
| `status` | query | No | `string` or `null` | — | — |
| `person_type` | query | No | `string` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_UserOut_`](#schema-page_userout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "uuid": "00000000-0000-4000-8000-000000000000",
      "username": "…",
      "full_name": "string",
      "email": "…",
      "mobile": "…",
      "organization_id": "…",
      "role": "string",
      "person_type": "…",
      "status": "string",
      "created_at": "string",
      "updated_at": "string",
      "sources": "…"
    }
  ],
  "next_cursor": "string",
  "total": 1
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

<a id="4_post_users"></a>
## 4. `POST /users` — Create User

### API

- **Operation ID:** `create_user_users_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

Provision a staff account. Administrators only - no self-registration.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CreateUser`](#schema-createuser)

```json
{
  "full_name": "string",
  "email": "string",
  "role": "string",
  "username": "string",
  "mobile": "string",
  "organization_id": "string",
  "person_type": "string",
  "source_uuids": [
    "00000000-0000-4000-8000-000000000000"
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`UserOut`](#schema-userout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "username": "string",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "organization_id": "string",
  "role": "string",
  "person_type": "string",
  "status": "string",
  "created_at": "string",
  "updated_at": "string",
  "sources": [
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

<a id="5_post_users_user_uuid_invite"></a>
## 5. `POST /users/{user_uuid}/invite` — Send the invitation again

### API

- **Operation ID:** `resend_invitation_users__user_uuid__invite_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

Write to somebody again about the account waiting for them.

Needed because the invitation is dispatched optionally - the account is
created whether or not the message could be queued - and a message nobody
received is invisible to everybody except the person waiting for it.

Only for an account that has not been activated. Sending one to an active
account would be an administrator resetting a colleague's password from a
distance; that is a different act, and its owner already has "Forgotten
your password?".

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="6_get_users_user_uuid"></a>
## 6. `GET /users/{user_uuid}` — Get User

### API

- **Operation ID:** `get_user_users__user_uuid__get`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`UserOut`](#schema-userout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "username": "string",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "organization_id": "string",
  "role": "string",
  "person_type": "string",
  "status": "string",
  "created_at": "string",
  "updated_at": "string",
  "sources": [
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

<a id="7_patch_users_user_uuid"></a>
## 7. `PATCH /users/{user_uuid}` — Update User

### API

- **Operation ID:** `update_user_users__user_uuid__patch`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`UpdateUser`](#schema-updateuser)

```json
{
  "full_name": "string",
  "mobile": "string",
  "organization_id": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`UserOut`](#schema-userout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "username": "string",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "organization_id": "string",
  "role": "string",
  "person_type": "string",
  "status": "string",
  "created_at": "string",
  "updated_at": "string",
  "sources": [
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

<a id="8_post_users_user_uuid_role"></a>
## 8. `POST /users/{user_uuid}/role` — Change a role

### API

- **Operation ID:** `change_role_users__user_uuid__role_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RoleChange`](#schema-rolechange)

```json
{
  "role": "string",
  "reason": "string"
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

<a id="9_post_users_user_uuid_deactivate"></a>
## 9. `POST /users/{user_uuid}/deactivate` — Deactivate

### API

- **Operation ID:** `deactivate_users__user_uuid__deactivate_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

End a member of staff's access, or switch a data principal's account off.

Two different acts behind one button, and the row's role says which. For
staff the role and the password go and the person stays, active, as a data
principal - the consents they gave and the rights they hold are theirs
under the Act whether or not they still work here. For a data principal
there is nothing to keep them as, and the account is switched off.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="10_post_users_user_uuid_reactivate"></a>
## 10. `POST /users/{user_uuid}/reactivate` — Reactivate

### API

- **Operation ID:** `reactivate_users__user_uuid__reactivate_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="11_delete_users_user_uuid_sessions"></a>
## 11. `DELETE /users/{user_uuid}/sessions` — Force logout

### API

- **Operation ID:** `force_logout_users__user_uuid__sessions_delete`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="12_post_users_user_uuid_mfa_reset"></a>
## 12. `POST /users/{user_uuid}/mfa/reset` — Reset Mfa

### API

- **Operation ID:** `reset_mfa_users__user_uuid__mfa_reset_post`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="13_get_users_user_uuid_person_type_history"></a>
## 13. `GET /users/{user_uuid}/person-type-history` — Person Type History

### API

- **Operation ID:** `person_type_history_users__user_uuid__person_type_history_get`
- **Access:** Role-controlled `users` operation. See [`../../roles/README.md`](../../roles/README.md).

A type change never creates a second account.

If an employee becomes a volunteer and gets a new row, her rights requests
return half her data and nobody notices until she complains.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `user_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`PersonTypeHistoryOut`](#schema-persontypehistoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "history_uuid": "00000000-0000-4000-8000-000000000000",
    "from_type": "string",
    "to_type": "string",
    "reason": "string",
    "changed_at": "string",
    "changed_by_uuid": "00000000-0000-4000-8000-000000000000",
    "changed_by_name": "string"
  }
]
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

<a id="schema-createuser"></a>
#### `CreateUser`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `email` | `string` | Yes | max length: `255`; format: `email` | — |
| `role` | `string` | Yes | — | — |
| `username` | `string` or `null` | No | max length: `120` | — |
| `mobile` | `string` or `null` | No | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `organization_id` | `string` or `null` | No | max length: `60` | — |
| `person_type` | `string` or `null` | No | — | — |
| `source_uuids` | array of `string` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-page_userout"></a>
#### `Page_UserOut_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`UserOut`](#schema-userout) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-rolechange"></a>
#### `RoleChange`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `role` | `string` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `500` | — |

<a id="schema-updateuser"></a>
#### `UpdateUser`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `mobile` | `string` or `null` | No | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `organization_id` | `string` or `null` | No | max length: `60` | — |

<a id="schema-userout"></a>
#### `UserOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `uuid` | `string` | Yes | format: `uuid` | — |
| `username` | `string` or `null` | Yes | — | — |
| `full_name` | `string` | Yes | — | — |
| `email` | `string` or `null` | Yes | — | — |
| `mobile` | `string` or `null` | Yes | — | — |
| `organization_id` | `string` or `null` | Yes | — | — |
| `role` | `string` | Yes | — | — |
| `person_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_at` | `object` | Yes | — | — |
| `updated_at` | `object` | Yes | — | — |
| `sources` | array of `string` or `null` | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
