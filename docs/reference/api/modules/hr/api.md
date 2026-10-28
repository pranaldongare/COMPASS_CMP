# Hr API

Generated from `backend/api/openapi.json`. **13 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /hr/categories`](#1_get_hr_categories)
2. [`POST /hr/categories`](#2_post_hr_categories)
3. [`GET /hr/categories/{category_uuid}`](#3_get_hr_categories_category_uuid)
4. [`PATCH /hr/categories/{category_uuid}`](#4_patch_hr_categories_category_uuid)
5. [`POST /hr/categories/{category_uuid}/status`](#5_post_hr_categories_category_uuid_status)
6. [`GET /hr/categories/{category_uuid}/processors`](#6_get_hr_categories_category_uuid_processors)
7. [`PUT /hr/categories/{category_uuid}/processors`](#7_put_hr_categories_category_uuid_processors)
8. [`GET /hr/activities`](#8_get_hr_activities)
9. [`POST /hr/activities`](#9_post_hr_activities)
10. [`GET /hr/activities/options`](#10_get_hr_activities_options)
11. [`GET /hr/activities/{activity_uuid}`](#11_get_hr_activities_activity_uuid)
12. [`POST /hr/activities/{activity_uuid}/upgrade`](#12_post_hr_activities_activity_uuid_upgrade)
13. [`POST /hr/activities/{activity_uuid}/close`](#13_post_hr_activities_activity_uuid_close)

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
    "default_person_type": "string",
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
  "default_person_type": "string",
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
  "default_person_type": "string",
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
  "description": "string",
  "default_person_type": "external"
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
  "default_person_type": "string",
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
  "default_person_type": "string",
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

<a id="8_get_hr_activities"></a>
## 8. `GET /hr/activities` — HR activities in scope

### API

- **Operation ID:** `list_activities_hr_activities_get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

Legal's all; an HR PoC's, of the categories assigned to them.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `category` | query | No | `string` or `null` | format: `uuid` | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ActivityOut`](#schema-activityout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "activity_uuid": "00000000-0000-4000-8000-000000000000",
    "name": "string",
    "description": "string",
    "status": "string",
    "category_uuid": "00000000-0000-4000-8000-000000000000",
    "category_code": "string",
    "category_name": "string",
    "version_uuid": "00000000-0000-4000-8000-000000000000",
    "template_version": 1,
    "version_status": "string",
    "reconsent_required": true,
    "template_uuid": "00000000-0000-4000-8000-000000000000",
    "template_code": "string",
    "template_title": "string",
    "created_by_uuid": "00000000-0000-4000-8000-000000000000",
    "created_by_name": "string",
    "notice_uuid": "00000000-0000-4000-8000-000000000000",
    "notice_code": "string",
    "notice_version": 1,
    "consent_count": 1,
    "link_status": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "updated_at": "2026-09-17T12:00:00Z"
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

<a id="9_post_hr_activities"></a>
## 9. `POST /hr/activities` — Create an activity, live, with its link

### API

- **Operation ID:** `create_activity_hr_activities_post`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

One transaction: project, site, notice composed and published, link.
A purpose off the version's list or a mandatory one left out, a
description outside the slot: 422 and nothing written. A retired version:
409.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ActivityIn`](#schema-activityin)

```json
{
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "template_version_uuid": "00000000-0000-4000-8000-000000000000",
  "purpose_uuids": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "name": "string",
  "description": "string",
  "audience_mode": "sso",
  "link_expires_at": "2026-09-17T12:00:00Z"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`ActivityCreated`](#schema-activitycreated) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "activity_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "link_uuid": "00000000-0000-4000-8000-000000000000",
  "url_path": "string",
  "expires_at": "2026-09-17T12:00:00Z",
  "audience_mode": "string"
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

<a id="10_get_hr_activities_options"></a>
## 10. `GET /hr/activities/options` — What an activity can be made from

### API

- **Operation ID:** `activity_options_hr_activities_options_get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

The HR PoC's active categories, each with its templates' approved
versions and their purposes, the mandatory ones marked.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`OptionCategory`](#schema-optioncategory) |

**Example `200` `application/json` response:**

```json
[
  {
    "category_uuid": "00000000-0000-4000-8000-000000000000",
    "category_code": "string",
    "name": "string",
    "versions": [
      {
        "version_uuid": "…",
        "version": "…",
        "template_uuid": "…",
        "template_code": "…",
        "template_title": "…",
        "slot_guidance": "…",
        "slot_max_length": "…",
        "reconsent_required": "…",
        "purposes": "…"
      }
    ]
  }
]
```

<a id="11_get_hr_activities_activity_uuid"></a>
## 11. `GET /hr/activities/{activity_uuid}` — Get Activity

### API

- **Operation ID:** `get_activity_hr_activities__activity_uuid__get`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `activity_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ActivityDetail`](#schema-activitydetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "activity_uuid": "00000000-0000-4000-8000-000000000000",
  "name": "string",
  "description": "string",
  "status": "string",
  "category_uuid": "00000000-0000-4000-8000-000000000000",
  "category_code": "string",
  "category_name": "string",
  "version_uuid": "00000000-0000-4000-8000-000000000000",
  "template_version": 1,
  "version_status": "string",
  "reconsent_required": true,
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "template_title": "string",
  "created_by_uuid": "00000000-0000-4000-8000-000000000000",
  "created_by_name": "string",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "notice_version": 1,
  "consent_count": 1,
  "link_status": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "link": {
    "link_uuid": "00000000-0000-4000-8000-000000000000",
    "status": "string",
    "expires_at": "2026-09-17T12:00:00Z",
    "use_count": 1,
    "audience_mode": "string",
    "url_path": "…"
  }
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

<a id="12_post_hr_activities_activity_uuid_upgrade"></a>
## 12. `POST /hr/activities/{activity_uuid}/upgrade` — Move an activity to another approved version

### API

- **Operation ID:** `upgrade_activity_hr_activities__activity_uuid__upgrade_post`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

A new notice version, published; the live link moves to it. A version
flagged for re-consent asks every participant again, after commit.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `activity_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`UpgradeIn`](#schema-upgradein)

```json
{
  "template_version_uuid": "00000000-0000-4000-8000-000000000000",
  "purpose_uuids": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "description": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`UpgradeOut`](#schema-upgradeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "activity_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "version": 1,
  "reconsent_requested": 1
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

<a id="13_post_hr_activities_activity_uuid_close"></a>
## 13. `POST /hr/activities/{activity_uuid}/close` — Close an activity

### API

- **Operation ID:** `close_activity_hr_activities__activity_uuid__close_post`
- **Access:** Role-controlled `hr` operation. See [`../../roles/README.md`](../../roles/README.md).

Its link stops resolving; consents given stand.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `activity_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CloseIn`](#schema-closein)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Closed`](#schema-closed) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "to": "string",
  "links_revoked": 1
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

<a id="schema-activitycreated"></a>
#### `ActivityCreated`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `activity_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `link_uuid` | `string` | Yes | format: `uuid` | — |
| `url_path` | `string` | Yes | — | — |
| `expires_at` | `string` | Yes | format: `date-time` | — |
| `audience_mode` | `string` | Yes | — | — |

<a id="schema-activitydetail"></a>
#### `ActivityDetail`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `activity_uuid` | `string` | Yes | format: `uuid` | — |
| `name` | `string` | Yes | — | — |
| `description` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `category_uuid` | `string` | Yes | format: `uuid` | — |
| `category_code` | `string` | Yes | — | — |
| `category_name` | `string` | Yes | — | — |
| `version_uuid` | `string` | Yes | format: `uuid` | — |
| `template_version` | `integer` | Yes | — | — |
| `version_status` | `string` | Yes | — | — |
| `reconsent_required` | `boolean` | Yes | — | — |
| `template_uuid` | `string` | Yes | format: `uuid` | — |
| `template_code` | `string` | Yes | — | — |
| `template_title` | `string` | Yes | — | — |
| `created_by_uuid` | `string` | Yes | format: `uuid` | — |
| `created_by_name` | `string` | Yes | — | — |
| `notice_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `notice_code` | `string` or `null` | Yes | — | — |
| `notice_version` | `integer` or `null` | Yes | — | — |
| `consent_count` | `integer` | Yes | — | — |
| `link_status` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `link` | [`ActivityLink`](#schema-activitylink) or `null` | Yes | — | — |

<a id="schema-activityin"></a>
#### `ActivityIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category_uuid` | `string` | Yes | format: `uuid` | — |
| `template_version_uuid` | `string` | Yes | format: `uuid` | — |
| `purpose_uuids` | array of `string` | Yes | — | — |
| `name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `description` | `string` | Yes | min length: `1`; max length: `4000` | — |
| `audience_mode` | enum: `sso`, `otp` | Yes | — | — |
| `link_expires_at` | `string` | Yes | format: `date-time` | — |

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
| `default_person_type` | `string` or `null` | No | — | — |
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
| `default_person_type` | `string` or `null` | No | — | — |
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
| `default_person_type` | enum: `external`, `vendor`, `candidate`, `visitor` or `null` | No | — | — |

<a id="schema-closein"></a>
#### `CloseIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` or `null` | No | max length: `2000` | — |

<a id="schema-closed"></a>
#### `Closed`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `to` | `string` | Yes | — | — |
| `links_revoked` | `integer` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-upgradein"></a>
#### `UpgradeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `template_version_uuid` | `string` | Yes | format: `uuid` | — |
| `purpose_uuids` | array of `string` | Yes | — | — |
| `description` | `string` | Yes | min length: `1`; max length: `4000` | — |

<a id="schema-upgradeout"></a>
#### `UpgradeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `activity_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `version` | `integer` | Yes | — | — |
| `reconsent_requested` | `integer` | Yes | — | — |

<a id="schema-activitylink"></a>
#### `ActivityLink`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `link_uuid` | `string` | Yes | format: `uuid` | — |
| `status` | `string` | Yes | — | — |
| `expires_at` | `string` | Yes | format: `date-time` | — |
| `use_count` | `integer` | Yes | — | — |
| `audience_mode` | `string` | Yes | — | — |
| `url_path` | `string` or `null` | Yes | — | — |

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
