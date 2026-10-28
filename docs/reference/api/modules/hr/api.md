# Hr API

Generated from `backend/api/openapi.json`. **7 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /hr/categories`](#1_get_hr_categories)
2. [`POST /hr/categories`](#2_post_hr_categories)
3. [`GET /hr/categories/{category_uuid}`](#3_get_hr_categories_category_uuid)
4. [`PATCH /hr/categories/{category_uuid}`](#4_patch_hr_categories_category_uuid)
5. [`POST /hr/categories/{category_uuid}/status`](#5_post_hr_categories_category_uuid_status)
6. [`GET /hr/categories/{category_uuid}/processors`](#6_get_hr_categories_category_uuid_processors)
7. [`PUT /hr/categories/{category_uuid}/processors`](#7_put_hr_categories_category_uuid_processors)

<a id="1_get_hr_categories"></a>
## 1. `GET /hr/categories` — The Legal office's categories

### API

- **Operation ID:** `list_categories_hr_categories_get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

An HR PoC's are the ones assigned to them.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | enum: `active`, `retired` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CategoryOut`](#schema-categoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "category_uuid": "00000000-0000-4000-8000-000000000000",
    "category_code": "string",
    "name": "string",
    "description": "string",
    "status": "string",
    "office_code": "string",
    "processor_count": 1,
    "poc_count": 1,
    "template_count": 1,
    "created_at": "2026-09-17T12:00:00Z",
    "updated_at": "2026-09-17T12:00:00Z",
    "retired_at": "2026-09-17T12:00:00Z"
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

<a id="2_post_hr_categories"></a>
## 2. `POST /hr/categories` — Create Category

### API

- **Operation ID:** `create_category_hr_categories_post`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

In the caller's office: the Legal office's.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CategoryIn`](#schema-categoryin)

```json
{
  "category_code": "string",
  "name": "string",
  "description": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`CategoryOut`](#schema-categoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "category_code": "string",
  "name": "string",
  "description": "string",
  "status": "string",
  "office_code": "string",
  "processor_count": 1,
  "poc_count": 1,
  "template_count": 1,
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z"
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

<a id="3_get_hr_categories_category_uuid"></a>
## 3. `GET /hr/categories/{category_uuid}` — Get Category

### API

- **Operation ID:** `get_category_hr_categories__category_uuid__get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `category_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`CategoryDetailOut`](#schema-categorydetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "category_code": "string",
  "name": "string",
  "description": "string",
  "status": "string",
  "office_code": "string",
  "processor_count": 1,
  "poc_count": 1,
  "template_count": 1,
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "processors": [
    {
      "processor_uuid": "00000000-0000-4000-8000-000000000000",
      "legal_name": "string",
      "is_in_house": true,
      "processor_status": "string",
      "processor_role": "string",
      "respondent_uuid": "…",
      "respondent_name": "…",
      "respondent_email": "…",
      "added_at": "2026-09-17T12:00:00Z"
    }
  ],
  "pocs": [
    {
      "uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "string",
      "email": "…",
      "status": "string",
      "assigned_at": "2026-09-17T12:00:00Z"
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

<a id="4_patch_hr_categories_category_uuid"></a>
## 4. `PATCH /hr/categories/{category_uuid}` — Update Category

### API

- **Operation ID:** `update_category_hr_categories__category_uuid__patch`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `category_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CategoryUpdate`](#schema-categoryupdate)

```json
{
  "name": "string",
  "description": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`CategoryOut`](#schema-categoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "category_code": "string",
  "name": "string",
  "description": "string",
  "status": "string",
  "office_code": "string",
  "processor_count": 1,
  "poc_count": 1,
  "template_count": 1,
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z"
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

<a id="5_post_hr_categories_category_uuid_status"></a>
## 5. `POST /hr/categories/{category_uuid}/status` — Retire or reactivate

### API

- **Operation ID:** `set_category_status_hr_categories__category_uuid__status_post`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

A retired category takes no new template; what was given under it stands.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `category_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CategoryStatusIn`](#schema-categorystatusin)

```json
{
  "status": "active"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`CategoryOut`](#schema-categoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "category_code": "string",
  "name": "string",
  "description": "string",
  "status": "string",
  "office_code": "string",
  "processor_count": 1,
  "poc_count": 1,
  "template_count": 1,
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z"
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

<a id="6_get_hr_categories_category_uuid_processors"></a>
## 6. `GET /hr/categories/{category_uuid}/processors` — List Category Processors

### API

- **Operation ID:** `list_category_processors_hr_categories__category_uuid__processors_get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `category_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CategoryProcessorOut`](#schema-categoryprocessorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "legal_name": "string",
    "is_in_house": true,
    "processor_status": "string",
    "processor_role": "string",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "respondent_name": "string",
    "respondent_email": "string",
    "added_at": "2026-09-17T12:00:00Z"
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

<a id="7_put_hr_categories_category_uuid_processors"></a>
## 7. `PUT /hr/categories/{category_uuid}/processors` — Set the processors that hold a category's data

### API

- **Operation ID:** `set_category_processors_hr_categories__category_uuid__processors_put`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

The whole set. One dropped is marked removed, not deleted; a respondent
must be an active member of staff of the Legal office.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `category_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CategoryProcessorsIn`](#schema-categoryprocessorsin)

```json
{
  "processors": [
    {
      "processor_uuid": "00000000-0000-4000-8000-000000000000",
      "processor_role": "hrms",
      "respondent_user_uuid": "…"
    }
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`CategoryProcessorOut`](#schema-categoryprocessorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "legal_name": "string",
    "is_in_house": true,
    "processor_status": "string",
    "processor_role": "string",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "respondent_name": "string",
    "respondent_email": "string",
    "added_at": "2026-09-17T12:00:00Z"
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

<a id="schema-categorydetailout"></a>
#### `CategoryDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category_uuid` | `string` | Yes | format: `uuid` | — |
| `category_code` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `description` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `office_code` | `string` | Yes | — | — |
| `processor_count` | `integer` | Yes | — | — |
| `poc_count` | `integer` | Yes | — | — |
| `template_count` | `integer` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `retired_at` | `string` or `null` | Yes | format: `date-time` | — |
| `processors` | array of [`CategoryProcessorOut`](#schema-categoryprocessorout) | Yes | — | — |
| `pocs` | array of [`CategoryPocOut`](#schema-categorypocout) | Yes | — | — |

<a id="schema-categoryin"></a>
#### `CategoryIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category_code` | `string` | Yes | pattern: `^[A-Z][A-Z0-9_]{1,23}$` | — |
| `name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `description` | `string` or `null` | No | min length: `1`; max length: `20000` | — |

<a id="schema-categoryout"></a>
#### `CategoryOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category_uuid` | `string` | Yes | format: `uuid` | — |
| `category_code` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `description` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `office_code` | `string` | Yes | — | — |
| `processor_count` | `integer` | Yes | — | — |
| `poc_count` | `integer` | Yes | — | — |
| `template_count` | `integer` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `retired_at` | `string` or `null` | Yes | format: `date-time` | — |

<a id="schema-categoryprocessorsin"></a>
#### `CategoryProcessorsIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processors` | array of [`CategoryProcessorIn`](#schema-categoryprocessorin) | No | — | — |

<a id="schema-categorystatusin"></a>
#### `CategoryStatusIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `status` | enum: `active`, `retired` | Yes | — | — |

<a id="schema-categoryupdate"></a>
#### `CategoryUpdate`

Name and description. The code is how templates, activities and the
trail name the category, so it does not change.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `description` | `string` or `null` | No | min length: `1`; max length: `20000` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-categoryprocessorout"></a>
#### `CategoryProcessorOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processor_uuid` | `string` | Yes | format: `uuid` | — |
| `legal_name` | `string` | Yes | — | — |
| `is_in_house` | `boolean` | Yes | — | — |
| `processor_status` | `string` | Yes | — | — |
| `processor_role` | `string` | Yes | — | — |
| `respondent_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `respondent_name` | `string` or `null` | Yes | — | — |
| `respondent_email` | `string` or `null` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-categorypocout"></a>
#### `CategoryPocOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` | Yes | — | — |
| `email` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `assigned_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-categoryprocessorin"></a>
#### `CategoryProcessorIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processor_uuid` | `string` | Yes | format: `uuid` | — |
| `processor_role` | enum: `hrms`, `database`, `vendor` | Yes | — | — |
| `respondent_user_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
