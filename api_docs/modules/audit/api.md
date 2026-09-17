# Audit API

Generated from `cmp_backend/openapi.json`. **3 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /audit`](#1_get_audit)
2. [`GET /audit/verify`](#2_get_audit_verify)
3. [`GET /audit/{log_uuid}`](#3_get_audit_log_uuid)

<a id="1_get_audit"></a>
## 1. `GET /audit` — Search the trail

### API

- **Operation ID:** `search_audit_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `actor` | query | No | `string` or `null` | format: `uuid` | — |
| `subject` | query | No | `string` or `null` | format: `uuid` | — |
| `entity_type` | query | No | `string` or `null` | max length: `60` | — |
| `entity_id` | query | No | `integer` or `null` | minimum: `1` | — |
| `event_type` | query | No | `string` or `null` | max length: `80` | — |
| `from` | query | No | `string` or `null` | format: `date-time` | — |
| `to` | query | No | `string` or `null` | format: `date-time` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_AuditEntry_`](#schema-page_auditentry) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "log_uuid": "00000000-0000-4000-8000-000000000000",
      "event_type": "string",
      "entity_type": "string",
      "entity_id": 1,
      "occurred_at": "2026-09-17T12:00:00Z",
      "detail": "…",
      "actor_uuid": "…",
      "actor_name": "…",
      "actor_role": "…",
      "subject_uuid": "…",
      "subject_name": "…",
      "entity_uuid": "…",
      "entity_label": "…",
      "entity_noun": "…",
      "entity_href": "…"
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

<a id="2_get_audit_verify"></a>
## 2. `GET /audit/verify` — Verify the hash chain

### API

- **Operation ID:** `verify_audit_verify_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

Recompute the chain and report the first row that does not verify.

Every row carries a digest over its own content and its predecessor's digest.
Editing row N changes its digest, which no longer matches what N+1 recorded,
so the answer is not "something changed" but "the trail is sound up to
exactly here".

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `from_log_id` | query | No | `integer` | minimum: `0`; default: `0` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`VerifyResult`](#schema-verifyresult) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "intact": true,
  "rows_checked": 1,
  "last_log_id": 1,
  "first_break": {},
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

<a id="3_get_audit_log_uuid"></a>
## 3. `GET /audit/{log_uuid}` — Get Entry

### API

- **Operation ID:** `get_entry_audit__log_uuid__get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `log_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`AuditEntry`](#schema-auditentry) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "log_uuid": "00000000-0000-4000-8000-000000000000",
  "event_type": "string",
  "entity_type": "string",
  "entity_id": 1,
  "occurred_at": "2026-09-17T12:00:00Z",
  "detail": {},
  "actor_uuid": "00000000-0000-4000-8000-000000000000",
  "actor_name": "string",
  "actor_role": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "entity_uuid": "string",
  "entity_label": "string",
  "entity_noun": "string",
  "entity_href": "string"
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

<a id="schema-auditentry"></a>
#### `AuditEntry`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `log_uuid` | `string` | Yes | format: `uuid` | — |
| `event_type` | `string` | Yes | — | — |
| `entity_type` | `string` | Yes | — | — |
| `entity_id` | `integer` | Yes | — | — |
| `occurred_at` | `string` | Yes | format: `date-time` | — |
| `detail` | `object` or `null` | No | — | — |
| `actor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `actor_name` | `string` or `null` | No | — | — |
| `actor_role` | `string` or `null` | No | — | — |
| `subject_uuid` | `string` or `null` | No | format: `uuid` | — |
| `subject_name` | `string` or `null` | No | — | — |
| `entity_uuid` | `string` or `null` | No | — | — |
| `entity_label` | `string` or `null` | No | — | — |
| `entity_noun` | `string` or `null` | No | — | — |
| `entity_href` | `string` or `null` | No | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-page_auditentry"></a>
#### `Page_AuditEntry_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`AuditEntry`](#schema-auditentry) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-verifyresult"></a>
#### `VerifyResult`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `intact` | `boolean` | Yes | — | — |
| `rows_checked` | `integer` | Yes | — | — |
| `last_log_id` | `integer` or `null` | Yes | — | — |
| `first_break` | `object` or `null` | Yes | — | — |
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
