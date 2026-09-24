# Audit API

Generated from `backend/api/openapi.json`. **7 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /audit`](#1_get_audit)
2. [`GET /audit/summary`](#2_get_audit_summary)
3. [`GET /audit/vocabulary`](#3_get_audit_vocabulary)
4. [`GET /audit/lookup`](#4_get_audit_lookup)
5. [`GET /audit/export.csv`](#5_get_audit_export_csv)
6. [`GET /audit/verify`](#6_get_audit_verify)
7. [`GET /audit/{log_uuid}`](#7_get_audit_log_uuid)

<a id="1_get_audit"></a>
## 1. `GET /audit` — Search the trail

### API

- **Operation ID:** `search_audit_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `actor` | query | No | `string` or `null` | format: `uuid` | — |
| `actor_role` | query | No | `string` or `null` | max length: `20` | — |
| `subject` | query | No | `string` or `null` | format: `uuid` | — |
| `entity_type` | query | No | `string` or `null` | max length: `60` | — |
| `entity_id` | query | No | `integer` or `null` | minimum: `1` | — |
| `entity` | query | No | `string` or `null` | format: `uuid` | The entity's public uuid; needs entity_type |
| `event_type` | query | No | `string` or `null` | max length: `80` | — |
| `event_group` | query | No | `string` or `null` | max length: `40`; pattern: `^[a-z_]+$` | — |
| `from` | query | No | `string` or `null` | format: `date-time` | — |
| `to` | query | No | `string` or `null` | format: `date-time` | — |
| `q` | query | No | `string` or `null` | max length: `120` | — |
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
      "entity_label_parts": "…",
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

<a id="2_get_audit_summary"></a>
## 2. `GET /audit/summary` — The shape of the rows a filter selects

### API

- **Operation ID:** `summary_audit_summary_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

Counts by event, by group, by the actor's role and by day, over exactly
the rows the same filters would list.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `actor` | query | No | `string` or `null` | format: `uuid` | — |
| `actor_role` | query | No | `string` or `null` | max length: `20` | — |
| `subject` | query | No | `string` or `null` | format: `uuid` | — |
| `entity_type` | query | No | `string` or `null` | max length: `60` | — |
| `entity_id` | query | No | `integer` or `null` | minimum: `1` | — |
| `entity` | query | No | `string` or `null` | format: `uuid` | The entity's public uuid; needs entity_type |
| `event_type` | query | No | `string` or `null` | max length: `80` | — |
| `event_group` | query | No | `string` or `null` | max length: `40`; pattern: `^[a-z_]+$` | — |
| `from` | query | No | `string` or `null` | format: `date-time` | — |
| `to` | query | No | `string` or `null` | format: `date-time` | — |
| `q` | query | No | `string` or `null` | max length: `120` | — |
| `days` | query | No | `integer` | minimum: `1`; maximum: `365`; default: `30` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`AuditSummary`](#schema-auditsummary) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "total": 1,
  "first_at": "2026-09-17T12:00:00Z",
  "last_at": "2026-09-17T12:00:00Z",
  "by_event": [
    {
      "key": "string",
      "count": 1
    }
  ],
  "by_group": [
    {
      "key": "string",
      "count": 1
    }
  ],
  "by_actor_role": [
    {
      "key": "string",
      "count": 1
    }
  ],
  "by_day": [
    {
      "day": "string",
      "count": 1
    }
  ],
  "days": 1
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

<a id="3_get_audit_vocabulary"></a>
## 3. `GET /audit/vocabulary` — What the trail can be filtered by

### API

- **Operation ID:** `vocabulary_audit_vocabulary_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

Every entity type and event type the trail may carry, with labels, and
the pickers the console offers. Served rather than hard-coded on the
client, so a new event appears in the filters the day it lands.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Vocabulary`](#schema-vocabulary) |

**Example `200` `application/json` response:**

```json
{
  "entity_types": [
    {
      "value": "string",
      "label": "string",
      "filterable_by_uuid": true
    }
  ],
  "event_groups": [
    {
      "value": "string",
      "label": "string"
    }
  ],
  "event_types": [
    {
      "value": "string",
      "group": "string",
      "group_label": "string",
      "label": "string"
    }
  ],
  "lookups": [
    {
      "kind": "string",
      "label": "string",
      "filter": "string"
    }
  ]
}
```

<a id="4_get_audit_lookup"></a>
## 4. `GET /audit/lookup` — Find a record to filter on

### API

- **Operation ID:** `lookup_audit_lookup_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

A few letters of a name, and up to ten records of that kind. Each answer
says which filter it feeds: a person is a subject or an actor, everything
else is the entity an event was recorded against.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `kind` | query | Yes | `string` | max length: `30` | — |
| `q` | query | Yes | `string` | min length: `1`; max length: `100` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`LookupHit`](#schema-lookuphit) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "kind": "string",
    "entity_type": "string",
    "filter": "string",
    "uuid": "string",
    "label": "string",
    "hint": "string"
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

<a id="5_get_audit_export_csv"></a>
## 5. `GET /audit/export.csv` — Download the rows a filter selects, as CSV

### API

- **Operation ID:** `export_csv_audit_export_csv_get`
- **Access:** Role-controlled `audit` operation. See [`../../roles/README.md`](../../roles/README.md).

Newest first, at most `EXPORT_LIMIT` rows, free-text cells neutralised
against spreadsheet formulas. The download is itself recorded in the
trail, with the filters used: reading the evidence is an act on it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `actor` | query | No | `string` or `null` | format: `uuid` | — |
| `actor_role` | query | No | `string` or `null` | max length: `20` | — |
| `subject` | query | No | `string` or `null` | format: `uuid` | — |
| `entity_type` | query | No | `string` or `null` | max length: `60` | — |
| `entity_id` | query | No | `integer` or `null` | minimum: `1` | — |
| `entity` | query | No | `string` or `null` | format: `uuid` | The entity's public uuid; needs entity_type |
| `event_type` | query | No | `string` or `null` | max length: `80` | — |
| `event_group` | query | No | `string` or `null` | max length: `40`; pattern: `^[a-z_]+$` | — |
| `from` | query | No | `string` or `null` | format: `date-time` | — |
| `to` | query | No | `string` or `null` | format: `date-time` | — |
| `q` | query | No | `string` or `null` | max length: `120` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | `object` |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
"string"
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

<a id="6_get_audit_verify"></a>
## 6. `GET /audit/verify` — Verify the hash chain

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

<a id="7_get_audit_log_uuid"></a>
## 7. `GET /audit/{log_uuid}` — Get Entry

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
  "entity_label_parts": [
    "string"
  ],
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
| `entity_label_parts` | array of `string` or `null` | No | — | — |
| `entity_noun` | `string` or `null` | No | — | — |
| `entity_href` | `string` or `null` | No | — | — |

<a id="schema-auditsummary"></a>
#### `AuditSummary`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `total` | `integer` | Yes | — | — |
| `first_at` | `string` or `null` | Yes | format: `date-time` | — |
| `last_at` | `string` or `null` | Yes | format: `date-time` | — |
| `by_event` | array of [`Count`](#schema-count) | Yes | — | — |
| `by_group` | array of [`Count`](#schema-count) | Yes | — | — |
| `by_actor_role` | array of [`Count`](#schema-count) | Yes | — | — |
| `by_day` | array of [`DayCount`](#schema-daycount) | Yes | — | — |
| `days` | `integer` | Yes | — | — |

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

<a id="schema-vocabulary"></a>
#### `Vocabulary`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `entity_types` | array of [`VocabularyEntityType`](#schema-vocabularyentitytype) | Yes | — | — |
| `event_groups` | array of [`VocabularyGroup`](#schema-vocabularygroup) | Yes | — | — |
| `event_types` | array of [`VocabularyEventType`](#schema-vocabularyeventtype) | Yes | — | — |
| `lookups` | array of [`VocabularyLookup`](#schema-vocabularylookup) | Yes | — | — |

<a id="schema-count"></a>
#### `Count`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `count` | `integer` | Yes | — | — |

<a id="schema-daycount"></a>
#### `DayCount`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `day` | `string` | Yes | — | — |
| `count` | `integer` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-vocabularyentitytype"></a>
#### `VocabularyEntityType`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `value` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `filterable_by_uuid` | `boolean` | Yes | — | — |

<a id="schema-vocabularygroup"></a>
#### `VocabularyGroup`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `value` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

<a id="schema-vocabularyeventtype"></a>
#### `VocabularyEventType`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `value` | `string` | Yes | — | — |
| `group` | `string` | Yes | — | — |
| `group_label` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

<a id="schema-vocabularylookup"></a>
#### `VocabularyLookup`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `filter` | `string` | Yes | — | — |
