# Notices API

Generated from `backend/api/openapi.json`. **22 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /notices`](#1_get_notices)
2. [`GET /projects/{project_uuid}/notices`](#2_get_projects_project_uuid_notices)
3. [`POST /projects/{project_uuid}/notices`](#3_post_projects_project_uuid_notices)
4. [`POST /projects/{project_uuid}/notices/copy`](#4_post_projects_project_uuid_notices_copy)
5. [`GET /notices/{notice_uuid}`](#5_get_notices_notice_uuid)
6. [`PUT /notices/{notice_uuid}`](#6_put_notices_notice_uuid)
7. [`GET /notices/{notice_uuid}/versions`](#7_get_notices_notice_uuid_versions)
8. [`GET /notices/{notice_uuid}/purposes`](#8_get_notices_notice_uuid_purposes)
9. [`POST /notices/{notice_uuid}/purposes`](#9_post_notices_notice_uuid_purposes)
10. [`PUT /notices/{notice_uuid}/purposes/{purpose_uuid}`](#10_put_notices_notice_uuid_purposes_purpose_uuid)
11. [`DELETE /notices/{notice_uuid}/purposes/{purpose_uuid}`](#11_delete_notices_notice_uuid_purposes_purpose_uuid)
12. [`GET /notices/{notice_uuid}/languages`](#12_get_notices_notice_uuid_languages)
13. [`POST /notices/{notice_uuid}/languages`](#13_post_notices_notice_uuid_languages)
14. [`PUT /notices/{notice_uuid}/languages/{code}`](#14_put_notices_notice_uuid_languages_code)
15. [`POST /notices/{notice_uuid}/languages/{code}/approve`](#15_post_notices_notice_uuid_languages_code_approve)
16. [`GET /notices/{notice_uuid}/checklist`](#16_get_notices_notice_uuid_checklist)
17. [`GET /notices/{notice_uuid}/preview`](#17_get_notices_notice_uuid_preview)
18. [`POST /notices/{notice_uuid}/publish`](#18_post_notices_notice_uuid_publish)
19. [`POST /projects/{project_uuid}/notices/import/validate`](#19_post_projects_project_uuid_notices_import_validate)
20. [`POST /projects/{project_uuid}/notices/import`](#20_post_projects_project_uuid_notices_import)
21. [`POST /notices/{notice_uuid}/purposes/activate`](#21_post_notices_notice_uuid_purposes_activate)
22. [`GET /notices/import/template`](#22_get_notices_import_template)

<a id="1_get_notices"></a>
## 1. `GET /notices` — All notices in scope

### API

- **Operation ID:** `list_all_notices_notices_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

Cross-project notice list.

The per-project route answers "what does this project have". The console's
Notices section asks "what is outstanding anywhere", which cannot be
assembled client-side without one request per project.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `project` | query | No | `string` or `null` | format: `uuid` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_NoticeListRow_`](#schema-page_noticelistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "status": "string",
      "published_at": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "updated_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "purpose_count": 1,
      "language_count": 1,
      "unapproved_languages": 1
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

<a id="2_get_projects_project_uuid_notices"></a>
## 2. `GET /projects/{project_uuid}/notices` — List Notices

### API

- **Operation ID:** `list_notices_projects__project_uuid__notices_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "notice_uuid": "00000000-0000-4000-8000-000000000000",
    "notice_code": "string",
    "version": 1,
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string",
    "withdraw_url": "string",
    "exercise_rights_url": "string",
    "board_complaint_url": "string",
    "dpo_contact": "string",
    "recipients_text": "string",
    "status": "string",
    "note": "string",
    "applicable_to": "string",
    "change_class": "string",
    "published_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "updated_at": "2026-09-17T12:00:00Z",
    "purpose_count": 1,
    "language_count": 1
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

<a id="3_post_projects_project_uuid_notices"></a>
## 3. `POST /projects/{project_uuid}/notices` — Create Notice

### API

- **Operation ID:** `create_notice_projects__project_uuid__notices_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NoticeIn`](#schema-noticein)

```json
{
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "data_subject",
  "note": "string",
  "notice_code": "string",
  "change_class": "string",
  "rendered_text": "string",
  "language_code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="4_post_projects_project_uuid_notices_copy"></a>
## 4. `POST /projects/{project_uuid}/notices/copy` — Copy an existing notice into this project

### API

- **Operation ID:** `copy_notice_projects__project_uuid__notices_copy_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

A copy, never a shared row.

`notice.project_id` is single-valued and every consent artefact records the
notice it was served from, so two projects sharing one notice row would make
"which text did she agree to, for which project" unanswerable. The copy
arrives as a fresh draft with its own code, carrying the purposes and the
renditions but not the legal approvals.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NoticeCopyIn`](#schema-noticecopyin)

```json
{
  "source_notice_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="5_get_notices_notice_uuid"></a>
## 5. `GET /notices/{notice_uuid}` — Get Notice

### API

- **Operation ID:** `get_notice_notices__notice_uuid__get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="6_put_notices_notice_uuid"></a>
## 6. `PUT /notices/{notice_uuid}` — Draft only

### API

- **Operation ID:** `update_notice_notices__notice_uuid__put`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NoticeUpdate`](#schema-noticeupdate)

```json
{
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "applicable_to": "data_subject",
  "note": "string",
  "change_class": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="7_get_notices_notice_uuid_versions"></a>
## 7. `GET /notices/{notice_uuid}/versions` — Notice Versions

### API

- **Operation ID:** `notice_versions_notices__notice_uuid__versions_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "notice_uuid": "00000000-0000-4000-8000-000000000000",
    "notice_code": "string",
    "version": 1,
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string",
    "withdraw_url": "string",
    "exercise_rights_url": "string",
    "board_complaint_url": "string",
    "dpo_contact": "string",
    "recipients_text": "string",
    "status": "string",
    "note": "string",
    "applicable_to": "string",
    "change_class": "string",
    "published_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "updated_at": "2026-09-17T12:00:00Z",
    "purpose_count": 1,
    "language_count": 1
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

<a id="8_get_notices_notice_uuid_purposes"></a>
## 8. `GET /notices/{notice_uuid}/purposes` — List Notice Purposes

### API

- **Operation ID:** `list_notice_purposes_notices__notice_uuid__purposes_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`PurposeOnNotice`](#schema-purposeonnotice) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "purpose_uuid": "00000000-0000-4000-8000-000000000000",
    "purpose_code": "string",
    "name": "string",
    "description": "string",
    "uses": "string",
    "lawful_basis": "string",
    "s7_clause": "string",
    "data_categories": [
      "string"
    ],
    "retention_period": "string",
    "retention_basis": "string",
    "erasure_trigger": "string",
    "cross_border_permitted": true,
    "permitted_for_minors": true,
    "status": "string",
    "display_order": 1,
    "is_mandatory": true,
    "purpose_data_categories": [
      "string"
    ],
    "purpose_uses": "string",
    "is_overridden": false,
    "overridden_at": "2026-09-17T12:00:00Z",
    "overridden_by_name": "string"
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

<a id="9_post_notices_notice_uuid_purposes"></a>
## 9. `POST /notices/{notice_uuid}/purposes` — Attach Purpose

### API

- **Operation ID:** `attach_purpose_notices__notice_uuid__purposes_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

`is_mandatory = true` should be rare and should make you uncomfortable.

If a purpose cannot be refused, ask whether it belongs in this notice at all.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`AttachPurpose`](#schema-attachpurpose)

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

<a id="10_put_notices_notice_uuid_purposes_purpose_uuid"></a>
## 10. `PUT /notices/{notice_uuid}/purposes/{purpose_uuid}` — Narrow Rule 3(b) for this notice

### API

- **Operation ID:** `override_purpose_notices__notice_uuid__purposes__purpose_uuid__put`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

State Rule 3(b) more narrowly on this notice than the purpose does.

A purpose is shared reference data: the same "Loyalty enrolment" is attached
to every notice that needs it, and its `data_categories` list covers every
collection it might serve. A specific project usually takes less than that,
and until now the only way to say so was to edit the shared purpose - which
changed every other notice using it.

**The override may only narrow.** `data_categories` must be a subset of the
purpose's, and the check is here rather than in a constraint because "is
this list contained in that one" is not a CHECK worth writing in SQL. The
rule matters: a notice that promised *more* than its purpose permits would
be collecting outside the basis it cites, which is the failure this whole
system exists to prevent.

`uses` is free text and cannot be checked mechanically, so it is attributed
instead - `overridden_by` and `overridden_at` are recorded, and the audit
event carries both texts. A human reviews it; the record says who.

Draft notices only. A published notice is frozen and hashed; changing what
it says is a new version, not an edit.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PurposeOverride`](#schema-purposeoverride)

```json
{
  "data_categories": [
    "string"
  ],
  "uses": "string"
}
```

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

<a id="11_delete_notices_notice_uuid_purposes_purpose_uuid"></a>
## 11. `DELETE /notices/{notice_uuid}/purposes/{purpose_uuid}` — Draft only

### API

- **Operation ID:** `detach_purpose_notices__notice_uuid__purposes__purpose_uuid__delete`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="12_get_notices_notice_uuid_languages"></a>
## 12. `GET /notices/{notice_uuid}/languages` — List Languages

### API

- **Operation ID:** `list_languages_notices__notice_uuid__languages_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

Every rendition of this notice, with its text.

The text is included, and its absence was a real gap rather than a saving:
without it there was nowhere in the console to *read* a notice, and the
editor opened blank because the form had nothing to prefill from. Both
symptoms, one missing column.

It is not sensitive - this is the text a data principal is shown, and anyone
reaching this endpoint can already read the notice. Volume is not a concern
either: a notice has at most a handful of renditions, and they are the
content of the page asking for them.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {}
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

<a id="13_post_notices_notice_uuid_languages"></a>
## 13. `POST /notices/{notice_uuid}/languages` — Add Language

### API

- **Operation ID:** `add_language_notices__notice_uuid__languages_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `language_code` | query | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`LanguageIn`](#schema-languagein)

```json
{
  "rendered_text": "string"
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

<a id="14_put_notices_notice_uuid_languages_code"></a>
## 14. `PUT /notices/{notice_uuid}/languages/{code}` — Draft only

### API

- **Operation ID:** `update_language_notices__notice_uuid__languages__code__put`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

Replacing the text clears the approval.

Text that changed after a lawyer signed it off has not been signed off.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `code` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`LanguageIn`](#schema-languagein)

```json
{
  "rendered_text": "string"
}
```

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

<a id="15_post_notices_notice_uuid_languages_code_approve"></a>
## 15. `POST /notices/{notice_uuid}/languages/{code}/approve` — Approve Language

### API

- **Operation ID:** `approve_language_notices__notice_uuid__languages__code__approve_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

Approval is per language, not once per notice.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `code` | path | Yes | `string` | — | — |

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

<a id="16_get_notices_notice_uuid_checklist"></a>
## 16. `GET /notices/{notice_uuid}/checklist` — Checklist

### API

- **Operation ID:** `checklist_notices__notice_uuid__checklist_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Checklist`](#schema-checklist) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "publishable": true,
  "blocking": [
    "string"
  ],
  "purpose_count": 1,
  "language_count": 1,
  "approved_language_count": 1,
  "site_count": 1
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

<a id="17_get_notices_notice_uuid_preview"></a>
## 17. `GET /notices/{notice_uuid}/preview` — Preview

### API

- **Operation ID:** `preview_notices__notice_uuid__preview_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |
| `language_code` | query | No | `string` or `null` | — | — |

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

<a id="18_post_notices_notice_uuid_publish"></a>
## 18. `POST /notices/{notice_uuid}/publish` — Publish

### API

- **Operation ID:** `publish_notices__notice_uuid__publish_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="19_post_projects_project_uuid_notices_import_validate"></a>
## 19. `POST /projects/{project_uuid}/notices/import/validate` — Dry run - reports what the document says, writes nothing

### API

- **Operation ID:** `validate_notice_document_projects__project_uuid__notices_import_validate_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_validate_notice_document_projects__project_uuid__notices_import_validate_post`](#schema-body_validate_notice_document_projects_project_uuid_notices_import_validate_post)

```json
{
  "document": "string"
}
```

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

<a id="20_post_projects_project_uuid_notices_import"></a>
## 20. `POST /projects/{project_uuid}/notices/import` — Create the notice and its purposes from an uploaded document

### API

- **Operation ID:** `import_notice_document_projects__project_uuid__notices_import_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

The purposes arrive as drafts and the notice cannot publish until the DPO
activates them - see `attach_purpose` for why that is not a deadlock.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_import_notice_document_projects__project_uuid__notices_import_post`](#schema-body_import_notice_document_projects_project_uuid_notices_import_post)

```json
{
  "document": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`NoticeOut`](#schema-noticeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "withdraw_url": "string",
  "exercise_rights_url": "string",
  "board_complaint_url": "string",
  "dpo_contact": "string",
  "recipients_text": "string",
  "status": "string",
  "note": "string",
  "applicable_to": "string",
  "change_class": "string",
  "published_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "purpose_count": 1,
  "language_count": 1
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

<a id="21_post_notices_notice_uuid_purposes_activate"></a>
## 21. `POST /notices/{notice_uuid}/purposes/activate` — Activate every draft purpose on this notice

### API

- **Operation ID:** `activate_notice_purposes_notices__notice_uuid__purposes_activate_post`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

The DPO's sign-off on purposes that arrived with an uploaded document.

One call rather than one per purpose: a notice imported from a template
carries nine of them, and nine identical approvals is a click count, not a
review. What is being approved is the set, which is how the DPO reads it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="22_get_notices_import_template"></a>
## 22. `GET /notices/import/template` — The notice document to fill in

### API

- **Operation ID:** `notice_document_template_notices_import_template_get`
- **Access:** Role-controlled `notices` operation. See [`../../roles/README.md`](../../roles/README.md).

The .docx an R&D User fills in and uploads back.

Shipped rather than described. The parser needs a header block, a
data-category table and a purpose table carrying particular columns, and a
person given that as a list of requirements produces a document that fails
on the first upload. Handing them the file removes the guessing.

Not cached: the columns in it are the columns the parser requires, and a
stale copy in a proxy is a template that disagrees with the validator.

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
"string"
```

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-attachpurpose"></a>
#### `AttachPurpose`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purpose_uuid` | `string` | Yes | format: `uuid` | — |
| `display_order` | `integer` | No | minimum: `0.0`; maximum: `999.0`; default: `0` | — |
| `is_mandatory` | `boolean` | No | default: `False` | — |

<a id="schema-body_import_notice_document_projects_project_uuid_notices_import_post"></a>
#### `Body_import_notice_document_projects__project_uuid__notices_import_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | .docx notice template, max 25 MB |

<a id="schema-body_validate_notice_document_projects_project_uuid_notices_import_validate_post"></a>
#### `Body_validate_notice_document_projects__project_uuid__notices_import_validate_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | .docx notice template, max 25 MB |

<a id="schema-checklist"></a>
#### `Checklist`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `publishable` | `boolean` | Yes | — | — |
| `blocking` | array of `string` | Yes | — | — |
| `purpose_count` | `integer` | Yes | — | — |
| `language_count` | `integer` | Yes | — | — |
| `approved_language_count` | `integer` | Yes | — | — |
| `site_count` | `integer` | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-languagein"></a>
#### `LanguageIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `rendered_text` | `string` | Yes | min length: `1` | — |

<a id="schema-noticecopyin"></a>
#### `NoticeCopyIn`

Start this project's notice from one that already exists.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source_notice_uuid` | `string` | Yes | format: `uuid` | — |

<a id="schema-noticein"></a>
#### `NoticeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `withdraw_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `exercise_rights_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `board_complaint_url` | `string` | Yes | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | The Data Protection Board portal, NOT the internal grievance form |
| `dpo_contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `applicable_to` | [`NoticeAudience`](#schema-noticeaudience) or `null` | No | — | — |
| `note` | `string` or `null` | No | max length: `4000` | — |
| `notice_code` | `string` or `null` | No | min length: `1`; max length: `80`; pattern: `^[A-Za-z0-9][A-Za-z0-9._-]*$` | — |
| `change_class` | `string` or `null` | No | — | — |
| `rendered_text` | `string` or `null` | No | min length: `1` | — |
| `language_code` | `string` or `null` | No | max length: `40` | — |

<a id="schema-noticeout"></a>
#### `NoticeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `withdraw_url` | `string` | Yes | — | — |
| `exercise_rights_url` | `string` | Yes | — | — |
| `board_complaint_url` | `string` | Yes | — | — |
| `dpo_contact` | `string` | Yes | — | — |
| `recipients_text` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `note` | `string` or `null` | No | — | — |
| `applicable_to` | `string` or `null` | No | — | — |
| `change_class` | `string` or `null` | Yes | — | — |
| `published_at` | `string` or `null` | Yes | format: `date-time` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `purpose_count` | `integer` or `null` | No | — | — |
| `language_count` | `integer` or `null` | No | — | — |

<a id="schema-noticeupdate"></a>
#### `NoticeUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `withdraw_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `exercise_rights_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `board_complaint_url` | `string` or `null` | No | min length: `8`; max length: `2000`; pattern: `^https?://[^\s<>\"]+$` | — |
| `dpo_contact` | `string` or `null` | No | max length: `255` | — |
| `applicable_to` | [`NoticeAudience`](#schema-noticeaudience) or `null` | No | — | — |
| `note` | `string` or `null` | No | max length: `4000` | — |
| `change_class` | `string` or `null` | No | — | — |

<a id="schema-page_noticelistrow"></a>
#### `Page_NoticeListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`NoticeListRow`](#schema-noticelistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-purposeoverride"></a>
#### `PurposeOverride`

Rule 3(b), for this notice only.

Both fields null clears the override and the notice reverts to the purpose's
own wording. That is the same operation as "reset", so there is no separate
endpoint for it.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `data_categories` | array of `string` or `null` | No | — | — |
| `uses` | `string` or `null` | No | max length: `20000` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-noticeaudience"></a>
#### `NoticeAudience`

Who a notice addresses.

Deliberately separate from `PersonType`: that records what somebody *is*,
this records who a document *speaks to*, and the two answer different
questions even where the words overlap. A notice carries exactly one — a
document written for employees and for the public at once is two documents
with different obligations wearing one name.

Type: enum: `data_subject`, `employee`, `ex_employee`, `others`

<a id="schema-noticelistrow"></a>
#### `NoticeListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `published_at` | `string` or `null` | Yes | format: `date-time` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `purpose_count` | `integer` | Yes | — | — |
| `language_count` | `integer` | Yes | — | — |
| `unapproved_languages` | `integer` | Yes | — | — |
