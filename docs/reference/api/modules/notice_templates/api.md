# Notice Templates API

Generated from `backend/api/openapi.json`. **10 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /notice-templates`](#1_get_notice_templates)
2. [`POST /notice-templates`](#2_post_notice_templates)
3. [`GET /notice-templates/by-code/{template_code}`](#3_get_notice_templates_by_code_template_code)
4. [`GET /notice-templates/{template_uuid}`](#4_get_notice_templates_template_uuid)
5. [`PUT /notice-templates/{template_uuid}`](#5_put_notice_templates_template_uuid)
6. [`POST /notice-templates/{template_uuid}/status`](#6_post_notice_templates_template_uuid_status)
7. [`POST /notice-templates/{template_uuid}/purposes`](#7_post_notice_templates_template_uuid_purposes)
8. [`DELETE /notice-templates/{template_uuid}/purposes/{purpose_uuid}`](#8_delete_notice_templates_template_uuid_purposes_purpose_uuid)
9. [`PUT /notice-templates/{template_uuid}/languages/{code}`](#9_put_notice_templates_template_uuid_languages_code)
10. [`DELETE /notice-templates/{template_uuid}/languages/{code}`](#10_delete_notice_templates_template_uuid_languages_code)

<a id="1_get_notice_templates"></a>
## 1. `GET /notice-templates` — The DPO's notice templates, newest first

### API

- **Operation ID:** `list_templates_notice_templates_get`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`TemplateOut`](#schema-templateout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "template_uuid": "00000000-0000-4000-8000-000000000000",
    "template_code": "string",
    "title": "string",
    "withdraw_url": "string",
    "exercise_rights_url": "string",
    "board_complaint_url": "string",
    "dpo_contact": "string",
    "applicable_to": "string",
    "note": "string",
    "status": "string",
    "created_by_name": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "updated_at": "2026-09-17T12:00:00Z",
    "retired_at": "2026-09-17T12:00:00Z",
    "purpose_count": 1,
    "language_count": 1,
    "used_count": 1
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

<a id="2_post_notice_templates"></a>
## 2. `POST /notice-templates` — Write a notice template, before any project exists

### API

- **Operation ID:** `create_template_notice_templates_post`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`cmp__api__routers__v1__notice_templates__TemplateIn`](#schema-cmp_api_routers_v1_notice_templates_templatein)

```json
{
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "data_subject",
  "note": "string",
  "rendered_text": "string",
  "language_code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="3_get_notice_templates_by_code_template_code"></a>
## 3. `GET /notice-templates/by-code/{template_code}` — Look up a template by the ID the DPO gave out, before attaching it

### API

- **Operation ID:** `find_template_notice_templates_by_code__template_code__get`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_code` | path | Yes | `string` | — | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateFound`](#schema-templatefound) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
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

<a id="4_get_notice_templates_template_uuid"></a>
## 4. `GET /notice-templates/{template_uuid}` — Get Template

### API

- **Operation ID:** `get_template_notice_templates__template_uuid__get`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="5_put_notice_templates_template_uuid"></a>
## 5. `PUT /notice-templates/{template_uuid}` — Update Template

### API

- **Operation ID:** `update_template_notice_templates__template_uuid__put`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplateUpdate`](#schema-templateupdate)

```json
{
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "data_subject",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="6_post_notice_templates_template_uuid_status"></a>
## 6. `POST /notice-templates/{template_uuid}/status` — Retire a template, or bring it back

### API

- **Operation ID:** `set_template_status_notice_templates__template_uuid__status_post`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplateStatusIn`](#schema-templatestatusin)

```json
{
  "status": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="7_post_notice_templates_template_uuid_purposes"></a>
## 7. `POST /notice-templates/{template_uuid}/purposes` — Attach Template Purpose

### API

- **Operation ID:** `attach_template_purpose_notice_templates__template_uuid__purposes_post`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplatePurposeIn`](#schema-templatepurposein)

```json
{
  "purpose_uuid": "00000000-0000-4000-8000-000000000000",
  "display_order": 0,
  "is_mandatory": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="8_delete_notice_templates_template_uuid_purposes_purpose_uuid"></a>
## 8. `DELETE /notice-templates/{template_uuid}/purposes/{purpose_uuid}` — Detach Template Purpose

### API

- **Operation ID:** `detach_template_purpose_notice_templates__template_uuid__purposes__purpose_uuid__delete`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="9_put_notice_templates_template_uuid_languages_code"></a>
## 9. `PUT /notice-templates/{template_uuid}/languages/{code}` — The template's text in one language, added or replaced

### API

- **Operation ID:** `set_template_language_notice_templates__template_uuid__languages__code__put`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |
| `code` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TemplateLanguageIn`](#schema-templatelanguagein)

```json
{
  "rendered_text": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="10_delete_notice_templates_template_uuid_languages_code"></a>
## 10. `DELETE /notice-templates/{template_uuid}/languages/{code}` — Remove Template Language

### API

- **Operation ID:** `remove_template_language_notice_templates__template_uuid__languages__code__delete`
- **Access:** Role-controlled `notice templates` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `template_uuid` | path | Yes | `string` | format: `uuid` | — |
| `code` | path | Yes | `string` | — | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`TemplateDetail`](#schema-templatedetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "template_uuid": "00000000-0000-4000-8000-000000000000",
  "template_code": "string",
  "title": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "string",
  "note": "string",
  "status": "string",
  "created_by_name": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "retired_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1,
  "used_count": 1,
  "purposes": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "name": "string",
      "status": "string",
      "lawful_basis": "string",
      "data_categories": [
        "…"
      ],
      "display_order": 1,
      "is_mandatory": true
    }
  ],
  "languages": [
    {
      "language_code": "string",
      "rendered_text": "string",
      "updated_at": "2026-09-17T12:00:00Z",
      "updated_by_name": "string"
    }
  ],
  "notices": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

# Referenced schemas

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-templatedetail"></a>
#### `TemplateDetail`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `template_uuid` | `string` | Yes | format: `uuid` | — |
| `template_code` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `withdraw_url` | `string` | Yes | — | — |
| `exercise_rights_url` | `string` | Yes | — | — |
| `board_complaint_url` | `string` | Yes | — | — |
| `dpo_contact` | `string` | Yes | — | — |
| `applicable_to` | `string` or `null` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_by_name` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `retired_at` | `string` or `null` | Yes | format: `date-time` | — |
| `purpose_count` | `integer` | Yes | — | — |
| `language_count` | `integer` | Yes | — | — |
| `used_count` | `integer` | Yes | — | — |
| `purposes` | array of [`TemplatePurposeOut`](#schema-templatepurposeout) | Yes | — | — |
| `languages` | array of [`TemplateLanguageOut`](#schema-templatelanguageout) | Yes | — | — |
| `notices` | array of [`TemplateNoticeOut`](#schema-templatenoticeout) | Yes | — | — |

<a id="schema-templatefound"></a>
#### `TemplateFound`

What the R&D User sees before attaching one: what it carries, not where
else it was used.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `template_uuid` | `string` | Yes | format: `uuid` | — |
| `template_code` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `withdraw_url` | `string` | Yes | — | — |
| `exercise_rights_url` | `string` | Yes | — | — |
| `board_complaint_url` | `string` | Yes | — | — |
| `dpo_contact` | `string` | Yes | — | — |
| `applicable_to` | `string` or `null` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_by_name` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `retired_at` | `string` or `null` | Yes | format: `date-time` | — |
| `purpose_count` | `integer` | Yes | — | — |
| `language_count` | `integer` | Yes | — | — |
| `used_count` | `integer` | Yes | — | — |
| `purposes` | array of [`TemplatePurposeOut`](#schema-templatepurposeout) | Yes | — | — |
| `languages` | array of [`TemplateLanguageOut`](#schema-templatelanguageout) | Yes | — | — |

<a id="schema-templatelanguagein"></a>
#### `TemplateLanguageIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `rendered_text` | `string` | Yes | min length: `1` | — |

<a id="schema-templatepurposein"></a>
#### `TemplatePurposeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purpose_uuid` | `string` | Yes | format: `uuid` | — |
| `display_order` | `integer` | No | minimum: `0.0`; maximum: `999.0`; default: `0` | — |
| `is_mandatory` | `boolean` | No | default: `False` | — |

<a id="schema-templatestatusin"></a>
#### `TemplateStatusIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `status` | `string` | Yes | — | active or retired |

<a id="schema-templateupdate"></a>
#### `TemplateUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `title` | `string` or `null` | No | min length: `3`; max length: `200` | — |
| `withdraw_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `exercise_rights_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `board_complaint_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `dpo_contact` | `string` or `null` | No | min length: `3`; max length: `255` | — |
| `applicable_to` | [`NoticeAudience`](#schema-noticeaudience) or `null` | No | — | — |
| `note` | `string` or `null` | No | max length: `4000` | — |

<a id="schema-cmp_api_routers_v1_notice_templates_templatein"></a>
#### `cmp__api__routers__v1__notice_templates__TemplateIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `title` | `string` | Yes | min length: `3`; max length: `200` | — |
| `withdraw_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `exercise_rights_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `board_complaint_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | The Data Protection Board portal, NOT the internal grievance form |
| `dpo_contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `applicable_to` | [`NoticeAudience`](#schema-noticeaudience) or `null` | No | — | — |
| `note` | `string` or `null` | No | max length: `4000` | — |
| `rendered_text` | `string` or `null` | No | min length: `1` | — |
| `language_code` | `string` or `null` | No | max length: `40` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-templatepurposeout"></a>
#### `TemplatePurposeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purpose_uuid` | `string` | Yes | format: `uuid` | — |
| `purpose_code` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `lawful_basis` | `string` | Yes | — | — |
| `data_categories` | array of `string` | Yes | — | — |
| `display_order` | `integer` | Yes | — | — |
| `is_mandatory` | `boolean` | Yes | — | — |

<a id="schema-templatelanguageout"></a>
#### `TemplateLanguageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `language_code` | `string` | Yes | — | — |
| `rendered_text` | `string` | Yes | — | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` | Yes | — | — |

<a id="schema-templatenoticeout"></a>
#### `TemplateNoticeOut`

A project notice made from the template.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |

<a id="schema-noticeaudience"></a>
#### `NoticeAudience`

Who a notice addresses.

Deliberately separate from `PersonType`: that records what somebody *is*,
this records who a document *speaks to*, and the two answer different
questions even where the words overlap. A notice carries exactly one — a
document written for employees and for the public at once is two documents
with different obligations wearing one name.

Type: enum: `data_subject`, `employee`, `ex_employee`, `others`
