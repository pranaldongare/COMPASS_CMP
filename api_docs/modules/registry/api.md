# Registry API

Generated from `cmp_backend/openapi.json`. **23 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /purposes`](#1_get_purposes)
2. [`POST /purposes`](#2_post_purposes)
3. [`GET /purposes/{purpose_uuid}`](#3_get_purposes_purpose_uuid)
4. [`PUT /purposes/{purpose_uuid}`](#4_put_purposes_purpose_uuid)
5. [`POST /purposes/{purpose_uuid}/activate`](#5_post_purposes_purpose_uuid_activate)
6. [`POST /purposes/{purpose_uuid}/retire`](#6_post_purposes_purpose_uuid_retire)
7. [`GET /purposes/{purpose_uuid}/versions`](#7_get_purposes_purpose_uuid_versions)
8. [`GET /purposes/{purpose_uuid}/usage`](#8_get_purposes_purpose_uuid_usage)
9. [`GET /processors`](#9_get_processors)
10. [`POST /processors`](#10_post_processors)
11. [`GET /processors/{processor_uuid}/respondents`](#11_get_processors_processor_uuid_respondents)
12. [`POST /processors/{processor_uuid}/respondents`](#12_post_processors_processor_uuid_respondents)
13. [`DELETE /processors/{processor_uuid}/respondents/{respondent_uuid}`](#13_delete_processors_processor_uuid_respondents_respondent_uuid)
14. [`GET /processors/{processor_uuid}`](#14_get_processors_processor_uuid)
15. [`PUT /processors/{processor_uuid}`](#15_put_processors_processor_uuid)
16. [`POST /processors/{processor_uuid}/suspend`](#16_post_processors_processor_uuid_suspend)
17. [`GET /sources`](#17_get_sources)
18. [`POST /sources`](#18_post_sources)
19. [`GET /sources/{source_uuid}`](#19_get_sources_source_uuid)
20. [`PUT /sources/{source_uuid}`](#20_put_sources_source_uuid)
21. [`PUT /sources/{source_uuid}/owner`](#21_put_sources_source_uuid_owner)
22. [`POST /sources/{source_uuid}/suspend`](#22_post_sources_source_uuid_suspend)
23. [`GET /sources/{source_uuid}/batches`](#23_get_sources_source_uuid_batches)

<a id="1_get_purposes"></a>
## 1. `GET /purposes` — List Purposes

### API

- **Operation ID:** `list_purposes_purposes_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `lawful_basis` | query | No | `string` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_PurposeOut_`](#schema-page_purposeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "purpose_uuid": "00000000-0000-4000-8000-000000000000",
      "purpose_code": "string",
      "version": 1,
      "status": "string",
      "name": "string",
      "description": "string",
      "uses": "string",
      "lawful_basis": "string",
      "s7_clause": "…",
      "data_categories": [
        "…"
      ],
      "retention_period": "string",
      "retention_basis": "string",
      "erasure_trigger": "string",
      "consent_validity_period": "string",
      "cross_border_permitted": true,
      "permitted_for_minors": true,
      "lapse_behaviour": "string",
      "created_at": "string",
      "updated_at": "string"
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

<a id="2_post_purposes"></a>
## 2. `POST /purposes` — Create Purpose

### API

- **Operation ID:** `create_purpose_purposes_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PurposeIn`](#schema-purposein)

```json
{
  "purpose_code": "string",
  "name": "string",
  "description": "string",
  "uses": "string",
  "lawful_basis": "string",
  "s7_clause": "string",
  "data_categories": [
    "string"
  ],
  "retention_days": 1.0,
  "retention_basis": "string",
  "erasure_trigger": "string",
  "consent_validity_days": 1.0,
  "cross_border_permitted": false,
  "permitted_for_minors": false,
  "lapse_behaviour": "quarantine"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`PurposeOut`](#schema-purposeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "purpose_uuid": "00000000-0000-4000-8000-000000000000",
  "purpose_code": "string",
  "version": 1,
  "status": "string",
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
  "consent_validity_period": "string",
  "cross_border_permitted": true,
  "permitted_for_minors": true,
  "lapse_behaviour": "string",
  "created_at": "string",
  "updated_at": "string"
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

<a id="3_get_purposes_purpose_uuid"></a>
## 3. `GET /purposes/{purpose_uuid}` — Get Purpose

### API

- **Operation ID:** `get_purpose_purposes__purpose_uuid__get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PurposeOut`](#schema-purposeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "purpose_uuid": "00000000-0000-4000-8000-000000000000",
  "purpose_code": "string",
  "version": 1,
  "status": "string",
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
  "consent_validity_period": "string",
  "cross_border_permitted": true,
  "permitted_for_minors": true,
  "lapse_behaviour": "string",
  "created_at": "string",
  "updated_at": "string"
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

<a id="4_put_purposes_purpose_uuid"></a>
## 4. `PUT /purposes/{purpose_uuid}` — Draft only

### API

- **Operation ID:** `update_purpose_purposes__purpose_uuid__put`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PurposeUpdate`](#schema-purposeupdate)

```json
{
  "name": "string",
  "description": "string",
  "uses": "string",
  "lawful_basis": "string",
  "s7_clause": "string",
  "data_categories": [
    "string"
  ],
  "retention_days": 1.0,
  "retention_basis": "string",
  "erasure_trigger": "string",
  "consent_validity_days": 1.0,
  "cross_border_permitted": true,
  "permitted_for_minors": true,
  "lapse_behaviour": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`PurposeOut`](#schema-purposeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "purpose_uuid": "00000000-0000-4000-8000-000000000000",
  "purpose_code": "string",
  "version": 1,
  "status": "string",
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
  "consent_validity_period": "string",
  "cross_border_permitted": true,
  "permitted_for_minors": true,
  "lapse_behaviour": "string",
  "created_at": "string",
  "updated_at": "string"
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

<a id="5_post_purposes_purpose_uuid_activate"></a>
## 5. `POST /purposes/{purpose_uuid}/activate` — Activate Purpose

### API

- **Operation ID:** `activate_purpose_purposes__purpose_uuid__activate_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="6_post_purposes_purpose_uuid_retire"></a>
## 6. `POST /purposes/{purpose_uuid}/retire` — Retire Purpose

### API

- **Operation ID:** `retire_purpose_purposes__purpose_uuid__retire_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

Blocked while the purpose is attached to a published notice.

Retiring it would leave a live notice offering a purpose the registry says
no longer exists, and the consents already given against it unexplainable.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="7_get_purposes_purpose_uuid_versions"></a>
## 7. `GET /purposes/{purpose_uuid}/versions` — Purpose Versions

### API

- **Operation ID:** `purpose_versions_purposes__purpose_uuid__versions_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`PurposeOut`](#schema-purposeout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "purpose_uuid": "00000000-0000-4000-8000-000000000000",
    "purpose_code": "string",
    "version": 1,
    "status": "string",
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
    "consent_validity_period": "string",
    "cross_border_permitted": true,
    "permitted_for_minors": true,
    "lapse_behaviour": "string",
    "created_at": "string",
    "updated_at": "string"
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

<a id="8_get_purposes_purpose_uuid_usage"></a>
## 8. `GET /purposes/{purpose_uuid}/usage` — Notices referencing this purpose

### API

- **Operation ID:** `purpose_usage_purposes__purpose_uuid__usage_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

How the UI knows retirement is blocked before the user tries.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `purpose_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="9_get_processors"></a>
## 9. `GET /processors` — List Processors

### API

- **Operation ID:** `list_processors_processors_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_ProcessorOut_`](#schema-page_processorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "processor_uuid": "00000000-0000-4000-8000-000000000000",
      "legal_name": "string",
      "type": "string",
      "contract_ref": "string",
      "security_confirmed_at": "2026-09-17",
      "status": "string",
      "is_in_house": false,
      "created_at": "string"
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

<a id="10_post_processors"></a>
## 10. `POST /processors` — Create Processor

### API

- **Operation ID:** `create_processor_processors_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProcessorIn`](#schema-processorin)

```json
{
  "legal_name": "string",
  "type": "string",
  "contract_ref": "string",
  "security_confirmed_at": "2026-09-17",
  "is_in_house": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`ProcessorOut`](#schema-processorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "legal_name": "string",
  "type": "string",
  "contract_ref": "string",
  "security_confirmed_at": "2026-09-17",
  "status": "string",
  "is_in_house": false,
  "created_at": "string"
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

<a id="11_get_processors_processor_uuid_respondents"></a>
## 11. `GET /processors/{processor_uuid}/respondents` — Who answers a rights-request ticket for this processor

### API

- **Operation ID:** `list_respondents_processors__processor_uuid__respondents_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`RespondentOut`](#schema-respondentout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "name": "string",
    "contact": "string",
    "user_uuid": "00000000-0000-4000-8000-000000000000",
    "user_role": "string",
    "created_at": "string"
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

<a id="12_post_processors_processor_uuid_respondents"></a>
## 12. `POST /processors/{processor_uuid}/respondents` — Name a respondent for this processor

### API

- **Operation ID:** `add_respondent_processors__processor_uuid__respondents_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

A respondent is how a holder's ticket gets answered.

An account answers on the portal: the ticket is in front of them when they
sign in, and they return it there. A name and an address are mailed, and
the Privacy Office tracks the exchange by hand.

An in-house processor's respondent must be an account - our own team has
no reason to be reached by mail. A third party's may be either. Usually it
is somebody at the third party, reached by mail; sometimes one of our own
people represents that third party here, and naming their account puts the
ticket on the portal like any internal one. The rule is held here rather
than left to whoever fills the form.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RespondentIn`](#schema-respondentin)

```json
{
  "name": "string",
  "contact": "string",
  "user_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`RespondentOut`](#schema-respondentout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "name": "string",
  "contact": "string",
  "user_uuid": "00000000-0000-4000-8000-000000000000",
  "user_role": "string",
  "created_at": "string"
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

<a id="13_delete_processors_processor_uuid_respondents_respondent_uuid"></a>
## 13. `DELETE /processors/{processor_uuid}/respondents/{respondent_uuid}` — Remove a respondent

### API

- **Operation ID:** `remove_respondent_processors__processor_uuid__respondents__respondent_uuid__delete`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |
| `respondent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="14_get_processors_processor_uuid"></a>
## 14. `GET /processors/{processor_uuid}` — Get Processor

### API

- **Operation ID:** `get_processor_processors__processor_uuid__get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ProcessorOut`](#schema-processorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "legal_name": "string",
  "type": "string",
  "contract_ref": "string",
  "security_confirmed_at": "2026-09-17",
  "status": "string",
  "is_in_house": false,
  "created_at": "string"
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

<a id="15_put_processors_processor_uuid"></a>
## 15. `PUT /processors/{processor_uuid}` — Update Processor

### API

- **Operation ID:** `update_processor_processors__processor_uuid__put`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProcessorUpdate`](#schema-processorupdate)

```json
{
  "legal_name": "string",
  "contract_ref": "string",
  "security_confirmed_at": "2026-09-17"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ProcessorOut`](#schema-processorout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "legal_name": "string",
  "type": "string",
  "contract_ref": "string",
  "security_confirmed_at": "2026-09-17",
  "status": "string",
  "is_in_house": false,
  "created_at": "string"
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

<a id="16_post_processors_processor_uuid_suspend"></a>
## 16. `POST /processors/{processor_uuid}/suspend` — Suspend Processor

### API

- **Operation ID:** `suspend_processor_processors__processor_uuid__suspend_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="17_get_sources"></a>
## 17. `GET /sources` — List Sources

### API

- **Operation ID:** `list_sources_sources_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

`processor` narrows the list to the sources one processor operates.

That filter is what makes the collection-site form a cascade rather than two
unrelated dropdowns: pick who operates the site, then pick from what they
actually run, instead of scrolling a registry-wide list and hoping.

`unmapped` is the opposite question: which sources has nobody said who
operates. A source the organisation runs itself legitimately has no
processor - requiring one would mean inventing a processor record for your
own organisation - so this is a gap to review rather than an error to
prevent, and a filter is how a reviewable gap is surfaced.

`unowned` is the DCO Admin's and the R&D owner's working list: sources nobody
is accountable for yet. `in_house` splits the registry the way routing does -
what we collect ourselves from what somebody else collects for us.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `source_role` | query | No | `string` or `null` | — | — |
| `processor` | query | No | `string` or `null` | format: `uuid` | — |
| `unmapped` | query | No | `boolean` | default: `False` | — |
| `unowned` | query | No | `boolean` | default: `False` | — |
| `in_house` | query | No | `boolean` or `null` | — | — |
| `q` | query | No | `string` or `null` | max length: `100` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_SourceOut_`](#schema-page_sourceout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "source_uuid": "00000000-0000-4000-8000-000000000000",
      "source_code": "string",
      "name": "string",
      "source_role": "string",
      "exchange_mode": "string",
      "id_scheme": "…",
      "is_authoritative_for": [
        "…"
      ],
      "status": "string",
      "processor_uuid": "…",
      "processor_name": "…",
      "is_in_house": "…",
      "has_owner": false,
      "owner_user_uuid": "…",
      "owner_name": "…",
      "owner_role": "…",
      "created_at": "string"
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

<a id="18_post_sources"></a>
## 18. `POST /sources` — Create Source

### API

- **Operation ID:** `create_source_sources_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

`is_authoritative_for` lists the data elements this source owns.

Without it, a nightly identity sync will overwrite a value corrected under a
rights request and nobody will notice.

**A collection owner may only register under their own kind of processor.**
A DCO is accountable for what a third party collects and an RCO for what the
R&D team collects itself, so a DCO registering an in-house rig - or the
reverse - would be creating a source they could never be given. Everyone
else (DPO, administrator, DCO Admin, R&D User) is unconstrained: they are
registering on somebody's behalf rather than for themselves.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SourceIn`](#schema-sourcein)

```json
{
  "source_code": "string",
  "name": "string",
  "source_role": "string",
  "exchange_mode": "string",
  "id_scheme": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "is_authoritative_for": [
    "string"
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`SourceOut`](#schema-sourceout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "source_code": "string",
  "name": "string",
  "source_role": "string",
  "exchange_mode": "string",
  "id_scheme": "string",
  "is_authoritative_for": [
    "string"
  ],
  "status": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "has_owner": false,
  "owner_user_uuid": "00000000-0000-4000-8000-000000000000",
  "owner_name": "string",
  "owner_role": "string",
  "created_at": "string"
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

<a id="19_get_sources_source_uuid"></a>
## 19. `GET /sources/{source_uuid}` — Get Source

### API

- **Operation ID:** `get_source_sources__source_uuid__get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SourceOut`](#schema-sourceout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "source_code": "string",
  "name": "string",
  "source_role": "string",
  "exchange_mode": "string",
  "id_scheme": "string",
  "is_authoritative_for": [
    "string"
  ],
  "status": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "has_owner": false,
  "owner_user_uuid": "00000000-0000-4000-8000-000000000000",
  "owner_name": "string",
  "owner_role": "string",
  "created_at": "string"
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

<a id="20_put_sources_source_uuid"></a>
## 20. `PUT /sources/{source_uuid}` — Update Source

### API

- **Operation ID:** `update_source_sources__source_uuid__put`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SourceUpdate`](#schema-sourceupdate)

```json
{
  "name": "string",
  "id_scheme": "string",
  "is_authoritative_for": [
    "string"
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SourceOut`](#schema-sourceout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "source_code": "string",
  "name": "string",
  "source_role": "string",
  "exchange_mode": "string",
  "id_scheme": "string",
  "is_authoritative_for": [
    "string"
  ],
  "status": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "has_owner": false,
  "owner_user_uuid": "00000000-0000-4000-8000-000000000000",
  "owner_name": "string",
  "owner_role": "string",
  "created_at": "string"
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

<a id="21_put_sources_source_uuid_owner"></a>
## 21. `PUT /sources/{source_uuid}/owner` — Assign the person accountable for a source

### API

- **Operation ID:** `assign_source_owner_sources__source_uuid__owner_put`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

Hand a source to a DCO or an RCO. Every project using it follows.

This is where a person is named, and it is the *only* place. Everywhere else
- registering a site, routing an approved project - picks a source, and the
owner comes with it. One answer to "who is accountable for CIT", recorded
once, rather than one per project that used it.

Which role fits which source is checked, because the distinction carries
meaning: an RCO is accountable for collection the R&D team does itself, a
DCO for a third party's. Assigning an RCO to a third-party source would
record that in-house staff are answerable for work they are not doing.

`trg_source_owner` re-derives the routing of every project deploying this
source, so this one write is the whole change. `projects_moved` says how many
that was - reassigning a rig used by three studies moves three studies, and
somebody should see that before they close the dialog.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SourceOwnerIn`](#schema-sourceownerin)

```json
{
  "owner_user_uuid": "00000000-0000-4000-8000-000000000000"
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

<a id="22_post_sources_source_uuid_suspend"></a>
## 22. `POST /sources/{source_uuid}/suspend` — Suspend Source

### API

- **Operation ID:** `suspend_source_sources__source_uuid__suspend_post`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="23_get_sources_source_uuid_batches"></a>
## 23. `GET /sources/{source_uuid}/batches` — Source Batches

### API

- **Operation ID:** `source_batches_sources__source_uuid__batches_get`
- **Access:** Role-controlled `registry` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `source_uuid` | path | Yes | `string` | format: `uuid` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

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

<a id="schema-page_processorout"></a>
#### `Page_ProcessorOut_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ProcessorOut`](#schema-processorout) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_purposeout"></a>
#### `Page_PurposeOut_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`PurposeOut`](#schema-purposeout) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_sourceout"></a>
#### `Page_SourceOut_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`SourceOut`](#schema-sourceout) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-processorin"></a>
#### `ProcessorIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `legal_name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `type` | `string` | Yes | — | — |
| `contract_ref` | `string` | Yes | min length: `1`; max length: `120` | — |
| `security_confirmed_at` | `string` | Yes | format: `date` | — |
| `is_in_house` | `boolean` | No | default: `False` | — |

<a id="schema-processorout"></a>
#### `ProcessorOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processor_uuid` | `string` | Yes | format: `uuid` | — |
| `legal_name` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `contract_ref` | `string` | Yes | — | — |
| `security_confirmed_at` | `string` | Yes | format: `date` | — |
| `status` | `string` | Yes | — | — |
| `is_in_house` | `boolean` | No | default: `False` | — |
| `created_at` | `object` | Yes | — | — |

<a id="schema-processorupdate"></a>
#### `ProcessorUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `legal_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `contract_ref` | `string` or `null` | No | max length: `120` | — |
| `security_confirmed_at` | `string` or `null` | No | format: `date` | — |

<a id="schema-purposein"></a>
#### `PurposeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purpose_code` | `string` | Yes | min length: `1`; max length: `80`; pattern: `^[A-Za-z0-9][A-Za-z0-9._-]*$` | — |
| `name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `description` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `uses` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `lawful_basis` | `string` | Yes | — | — |
| `s7_clause` | `string` or `null` | No | — | — |
| `data_categories` | array of `string` | Yes | — | — |
| `retention_days` | `integer` | Yes | minimum: `1.0`; maximum: `36500.0` | — |
| `retention_basis` | `string` | Yes | — | — |
| `erasure_trigger` | `string` | Yes | — | — |
| `consent_validity_days` | `integer` or `null` | No | minimum: `1.0`; maximum: `36500.0` | — |
| `cross_border_permitted` | `boolean` | No | default: `False` | — |
| `permitted_for_minors` | `boolean` | No | default: `False` | — |
| `lapse_behaviour` | `string` | No | default: `quarantine` | — |

<a id="schema-purposeout"></a>
#### `PurposeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purpose_uuid` | `string` | Yes | format: `uuid` | — |
| `purpose_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |
| `uses` | `string` | Yes | — | — |
| `lawful_basis` | `string` | Yes | — | — |
| `s7_clause` | `string` or `null` | Yes | — | — |
| `data_categories` | array of `string` | Yes | — | — |
| `retention_period` | `object` | Yes | — | — |
| `retention_basis` | `string` | Yes | — | — |
| `erasure_trigger` | `string` | Yes | — | — |
| `consent_validity_period` | `object` | No | — | — |
| `cross_border_permitted` | `boolean` | Yes | — | — |
| `permitted_for_minors` | `boolean` | Yes | — | — |
| `lapse_behaviour` | `string` | Yes | — | — |
| `created_at` | `object` | Yes | — | — |
| `updated_at` | `object` | Yes | — | — |

<a id="schema-purposeupdate"></a>
#### `PurposeUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `description` | `string` or `null` | No | min length: `1`; max length: `20000` | — |
| `uses` | `string` or `null` | No | min length: `1`; max length: `20000` | — |
| `lawful_basis` | `string` or `null` | No | — | — |
| `s7_clause` | `string` or `null` | No | — | — |
| `data_categories` | array of `string` or `null` | No | — | — |
| `retention_days` | `integer` or `null` | No | minimum: `1.0`; maximum: `36500.0` | — |
| `retention_basis` | `string` or `null` | No | — | — |
| `erasure_trigger` | `string` or `null` | No | — | — |
| `consent_validity_days` | `integer` or `null` | No | minimum: `1.0`; maximum: `36500.0` | — |
| `cross_border_permitted` | `boolean` or `null` | No | — | — |
| `permitted_for_minors` | `boolean` or `null` | No | — | — |
| `lapse_behaviour` | `string` or `null` | No | — | — |

<a id="schema-respondentin"></a>
#### `RespondentIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `contact` | `string` or `null` | No | max length: `255`; format: `email` | — |
| `user_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-respondentout"></a>
#### `RespondentOut`

Who answers a rights-request ticket for a processor.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `respondent_uuid` | `string` | Yes | format: `uuid` | — |
| `name` | `string` | Yes | — | — |
| `contact` | `string` | Yes | — | — |
| `user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `user_role` | `string` or `null` | No | — | — |
| `created_at` | `object` | Yes | — | — |

<a id="schema-sourcein"></a>
#### `SourceIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source_code` | `string` | Yes | min length: `1`; max length: `80`; pattern: `^[A-Za-z0-9][A-Za-z0-9._-]*$` | — |
| `name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `source_role` | `string` | Yes | — | — |
| `exchange_mode` | `string` | Yes | — | — |
| `id_scheme` | `string` or `null` | No | max length: `120` | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `site_uuid` | `string` or `null` | No | format: `uuid` | — |
| `is_authoritative_for` | array of `string` | No | — | — |

<a id="schema-sourceout"></a>
#### `SourceOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source_uuid` | `string` | Yes | format: `uuid` | — |
| `source_code` | `string` | Yes | — | — |
| `name` | `string` | Yes | — | — |
| `source_role` | `string` | Yes | — | — |
| `exchange_mode` | `string` | Yes | — | — |
| `id_scheme` | `string` or `null` | Yes | — | — |
| `is_authoritative_for` | array of `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `processor_name` | `string` or `null` | No | — | — |
| `is_in_house` | `boolean` or `null` | No | — | — |
| `has_owner` | `boolean` | No | default: `False` | — |
| `owner_user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `owner_name` | `string` or `null` | No | — | — |
| `owner_role` | `string` or `null` | No | — | — |
| `created_at` | `object` | Yes | — | — |

<a id="schema-sourceownerin"></a>
#### `SourceOwnerIn`

Who is accountable for collection from this source.

`null` takes it back, which is a real operation: somebody leaves and their
sources have to sit unowned until they are picked up, rather than being
silently parked with whoever happens to be assigned next.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `owner_user_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-sourceupdate"></a>
#### `SourceUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `id_scheme` | `string` or `null` | No | max length: `120` | — |
| `is_authoritative_for` | array of `string` or `null` | No | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |
