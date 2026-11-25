# Employee-Check API

Generated from `backend/api/openapi.json`. **5 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /employee-check`](#1_get_employee_check)
2. [`PUT /employee-check`](#2_put_employee_check)
3. [`POST /employee-check/domains`](#3_post_employee_check_domains)
4. [`DELETE /employee-check/domains/{domain}`](#4_delete_employee_check_domains_domain)
5. [`POST /employee-check/test`](#5_post_employee_check_test)

<a id="1_get_employee_check"></a>
## 1. `GET /employee-check` — VerifyEmail and the domains

### API

- **Operation ID:** `get_settings_employee_check_get`
- **Access:** Role-controlled `employee-check` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`EmployeeCheckOut`](#schema-employeecheckout) |

**Example `200` `application/json` response:**

```json
{
  "base_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
  "allow_other_domains": true,
  "domains": [
    {
      "domain": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
    }
  ],
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
}
```

<a id="2_put_employee_check"></a>
## 2. `PUT /employee-check` — Set VerifyEmail's address, key and switches

### API

- **Operation ID:** `put_settings_employee_check_put`
- **Access:** Role-controlled `employee-check` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`EmployeeCheckIn`](#schema-employeecheckin)

```json
{
  "base_url": "string",
  "api_key": "string",
  "clear_api_key": false,
  "api_key_header": "string",
  "enabled": false,
  "allow_other_domains": true
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`EmployeeCheckOut`](#schema-employeecheckout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "base_url": "string",
  "api_key_set": true,
  "api_key_header": "string",
  "enabled": true,
  "allow_other_domains": true,
  "domains": [
    {
      "domain": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
    }
  ],
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string"
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

<a id="3_post_employee_check_domains"></a>
## 3. `POST /employee-check/domains` — Add a domain

### API

- **Operation ID:** `add_domain_employee_check_domains_post`
- **Access:** Role-controlled `employee-check` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`DomainIn`](#schema-domainin)

```json
{
  "domain": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | array of [`DomainOut`](#schema-domainout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
[
  {
    "domain": "string",
    "added_at": "2026-09-17T12:00:00Z",
    "added_by_name": "string"
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

<a id="4_delete_employee_check_domains_domain"></a>
## 4. `DELETE /employee-check/domains/{domain}` — Remove a domain

### API

- **Operation ID:** `remove_domain_employee_check_domains__domain__delete`
- **Access:** Role-controlled `employee-check` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `domain` | path | Yes | `string` | — | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`DomainOut`](#schema-domainout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "domain": "string",
    "added_at": "2026-09-17T12:00:00Z",
    "added_by_name": "string"
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

<a id="5_post_employee_check_test"></a>
## 5. `POST /employee-check/test` — Ask VerifyEmail about one address now

### API

- **Operation ID:** `test_address_employee_check_test_post`
- **Access:** Role-controlled `employee-check` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TestIn`](#schema-testin)

```json
{
  "email": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TestOut`](#schema-testout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "result": "string",
  "message": "string",
  "on_company_domain": true
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

<a id="schema-domainin"></a>
#### `DomainIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `domain` | `string` | Yes | min length: `3`; max length: `253` | — |

<a id="schema-employeecheckin"></a>
#### `EmployeeCheckIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `base_url` | `string` or `null` | No | max length: `500` | — |
| `api_key` | `string` or `null` | No | min length: `1`; max length: `4000` | — |
| `clear_api_key` | `boolean` | No | default: `False` | — |
| `api_key_header` | `string` or `null` | No | min length: `1`; max length: `64` | — |
| `enabled` | `boolean` | No | default: `False` | — |
| `allow_other_domains` | `boolean` | No | default: `True` | — |

<a id="schema-employeecheckout"></a>
#### `EmployeeCheckOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `base_url` | `string` or `null` | Yes | — | — |
| `api_key_set` | `boolean` | Yes | — | — |
| `api_key_header` | `string` | Yes | — | — |
| `enabled` | `boolean` | Yes | — | — |
| `allow_other_domains` | `boolean` | Yes | — | — |
| `domains` | array of [`DomainOut`](#schema-domainout) | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-testin"></a>
#### `TestIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `email` | `string` | Yes | min length: `3`; max length: `320` | — |

<a id="schema-testout"></a>
#### `TestOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `result` | `string` | Yes | — | — |
| `message` | `string` | Yes | — | — |
| `on_company_domain` | `boolean` | Yes | — | — |

<a id="schema-domainout"></a>
#### `DomainOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `domain` | `string` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
