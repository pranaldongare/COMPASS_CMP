# Analytics API

Generated from `backend/api/openapi.json`. **8 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /analytics/catalogue`](#1_get_analytics_catalogue)
2. [`GET /analytics/figures`](#2_get_analytics_figures)
3. [`GET /analytics/inventory`](#3_get_analytics_inventory)
4. [`GET /analytics/audit-reports/{key}`](#4_get_analytics_audit_reports_key)
5. [`GET /analytics/settings`](#5_get_analytics_settings)
6. [`PUT /analytics/targets/{key}`](#6_put_analytics_targets_key)
7. [`DELETE /analytics/targets/{key}`](#7_delete_analytics_targets_key)
8. [`PUT /analytics/settings/threshold`](#8_put_analytics_settings_threshold)

<a id="1_get_analytics_catalogue"></a>
## 1. `GET /analytics/catalogue` — What this reader may see

### API

- **Operation ID:** `get_catalogue_analytics_catalogue_get`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`CatalogueOut`](#schema-catalogueout) |

**Example `200` `application/json` response:**

```json
{
  "role": "string",
  "office": "string",
  "may_choose_office": true,
  "sections": [
    "string"
  ],
  "metrics": [
    {
      "key": "string",
      "title": "string",
      "definition": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "kind": "string",
      "dims": [
        "…"
      ],
      "people": true,
      "numerator": "…",
      "denominator": "…",
      "higher_is_better": true
    }
  ],
  "dimensions": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "periods": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "cadences": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "reports": [
    {
      "key": "string",
      "title": "string",
      "description": "string",
      "formats": [
        "…"
      ],
      "schedulable": true,
      "recipient_roles": [
        "…"
      ]
    }
  ],
  "audit_reports": [
    {
      "key": "string",
      "title": "string",
      "description": "string"
    }
  ]
}
```

<a id="2_get_analytics_figures"></a>
## 2. `GET /analytics/figures` — Figures for a period

### API

- **Operation ID:** `get_figures_analytics_figures_get`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

The figures of a section, or the metrics named, for the period, with
the previous period, the target and its status, a line and a breakdown.
`grain` draws the line by day, week or month instead of the period's own
choice; a day line is refused past 92 days.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `section` | query | No | `string` or `null` | max length: `24` | — |
| `keys` | query | No | array of `string` or `null` | — | — |
| `period` | query | No | `string` | default: `this_month` | A preset: last_7_days, last_30_days, this_month, last_month, this_quarter, last_quarter, this_year, last_year, this_fy, last_fy, custom |
| `start` | query | No | `string` or `null` | format: `date` | custom: the first or last day, India time |
| `end` | query | No | `string` or `null` | format: `date` | custom: the first or last day, India time |
| `office` | query | No | `string` or `null` | pattern: `^(rnd|hr)$` | Management only: one office |
| `dim` | query | No | `string` or `null` | max length: `24` | — |
| `compare` | query | No | `boolean` | default: `True` | — |
| `trend` | query | No | `boolean` | default: `True` | — |
| `grain` | query | No | enum: `day`, `week`, `month` or `null` | — | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`FiguresOut`](#schema-figuresout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "period": {
    "preset": "string",
    "start": "2026-09-17T12:00:00Z",
    "end": "2026-09-17T12:00:00Z",
    "label": "string",
    "start_date": "2026-09-17",
    "end_date": "2026-09-17"
  },
  "previous": {
    "preset": "string",
    "start": "2026-09-17T12:00:00Z",
    "end": "2026-09-17T12:00:00Z",
    "label": "string",
    "start_date": "2026-09-17",
    "end_date": "2026-09-17"
  },
  "office": "string",
  "dim": "string",
  "grain": "string",
  "threshold": 1,
  "metrics": [
    {
      "key": "string",
      "title": "string",
      "definition": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "kind": "string",
      "dims": [
        "…"
      ],
      "numerator": "…",
      "denominator": "…",
      "value": "…",
      "suppressed": true,
      "previous": "…",
      "previous_suppressed": true,
      "change": "…",
      "target": "…",
      "amber": "…",
      "higher_is_better": true,
      "status": "…",
      "series": [
        "…"
      ],
      "breakdown": [
        "…"
      ]
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

<a id="3_get_analytics_inventory"></a>
## 3. `GET /analytics/inventory` — The record of processing

### API

- **Operation ID:** `get_inventory_analytics_inventory_get`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `office` | query | No | `string` or `null` | pattern: `^(rnd|hr)$` | Management only: one office |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`InventoryOut`](#schema-inventoryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "purposes": [
    {}
  ],
  "processors": [
    {}
  ],
  "sources": [
    {}
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

<a id="4_get_analytics_audit_reports_key"></a>
## 4. `GET /analytics/audit-reports/{key}` — One ready-made audit report

### API

- **Operation ID:** `get_audit_report_analytics_audit_reports__key__get`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | max length: `32` | — |
| `period` | query | No | `string` | default: `last_30_days` | A preset: last_7_days, last_30_days, this_month, last_month, this_quarter, last_quarter, this_year, last_year, this_fy, last_fy, custom |
| `start` | query | No | `string` or `null` | format: `date` | custom: the first or last day, India time |
| `end` | query | No | `string` or `null` | format: `date` | custom: the first or last day, India time |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`AuditReportOut`](#schema-auditreportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "key": "string",
  "title": "string",
  "description": "string",
  "events": [
    "string"
  ],
  "period": {
    "preset": "string",
    "start": "2026-09-17T12:00:00Z",
    "end": "2026-09-17T12:00:00Z",
    "label": "string",
    "start_date": "2026-09-17",
    "end_date": "2026-09-17"
  },
  "items": [
    {
      "log_uuid": "00000000-0000-4000-8000-000000000000",
      "event_type": "string",
      "entity_type": "…",
      "occurred_at": "2026-09-17T12:00:00Z",
      "actor_uuid": "…",
      "actor_name": "…",
      "actor_role": "…",
      "subject_uuid": "…",
      "subject_name": "…",
      "detail": "…"
    }
  ],
  "next_cursor": "string",
  "total": 1,
  "summary": {}
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

<a id="5_get_analytics_settings"></a>
## 5. `GET /analytics/settings` — Targets and the threshold

### API

- **Operation ID:** `get_settings_analytics_settings_get`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SettingsOut`](#schema-settingsout) |

**Example `200` `application/json` response:**

```json
{
  "small_number_threshold": 1,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string",
  "targets": [
    {
      "key": "string",
      "title": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "higher_is_better": true,
      "default_target": "…",
      "default_amber": "…",
      "target": "…",
      "amber": "…",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
    }
  ]
}
```

<a id="6_put_analytics_targets_key"></a>
## 6. `PUT /analytics/targets/{key}` — Set a metric's target

### API

- **Operation ID:** `put_target_analytics_targets__key__put`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | max length: `64` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TargetIn`](#schema-targetin)

```json
{
  "target": 0.0,
  "amber": 0.0
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SettingsOut`](#schema-settingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "small_number_threshold": 1,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string",
  "targets": [
    {
      "key": "string",
      "title": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "higher_is_better": true,
      "default_target": "…",
      "default_amber": "…",
      "target": "…",
      "amber": "…",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="7_delete_analytics_targets_key"></a>
## 7. `DELETE /analytics/targets/{key}` — Back to the default target

### API

- **Operation ID:** `delete_target_analytics_targets__key__delete`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `key` | path | Yes | `string` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SettingsOut`](#schema-settingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "small_number_threshold": 1,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string",
  "targets": [
    {
      "key": "string",
      "title": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "higher_is_better": true,
      "default_target": "…",
      "default_amber": "…",
      "target": "…",
      "amber": "…",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="8_put_analytics_settings_threshold"></a>
## 8. `PUT /analytics/settings/threshold` — The small-number threshold

### API

- **Operation ID:** `put_threshold_analytics_settings_threshold_put`
- **Access:** Role-controlled `analytics` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ThresholdIn`](#schema-thresholdin)

```json
{
  "small_number_threshold": 1.0
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SettingsOut`](#schema-settingsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "small_number_threshold": 1,
  "updated_at": "2026-09-17T12:00:00Z",
  "updated_by_name": "string",
  "targets": [
    {
      "key": "string",
      "title": "string",
      "unit": "string",
      "section": "string",
      "group": "string",
      "higher_is_better": true,
      "default_target": "…",
      "default_amber": "…",
      "target": "…",
      "amber": "…",
      "customised": true,
      "updated_at": "…",
      "updated_by_name": "…"
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

<a id="schema-auditreportout"></a>
#### `AuditReportOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |
| `events` | array of `string` | Yes | — | — |
| `period` | [`PeriodOut`](#schema-periodout) | Yes | — | — |
| `items` | array of [`AuditRowOut`](#schema-auditrowout) | Yes | — | — |
| `next_cursor` | `string` or `null` | Yes | — | — |
| `total` | `integer` | Yes | — | — |
| `summary` | `object` | Yes | — | — |

<a id="schema-catalogueout"></a>
#### `CatalogueOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `role` | `string` | Yes | — | — |
| `office` | `string` or `null` | Yes | — | — |
| `may_choose_office` | `boolean` | Yes | — | — |
| `sections` | array of `string` | Yes | — | — |
| `metrics` | array of [`MetricInfo`](#schema-metricinfo) | Yes | — | — |
| `dimensions` | array of [`Choice`](#schema-choice) | Yes | — | — |
| `periods` | array of [`Choice`](#schema-choice) | Yes | — | — |
| `cadences` | array of [`Choice`](#schema-choice) | Yes | — | — |
| `reports` | array of [`ReportKindInfo`](#schema-reportkindinfo) | Yes | — | — |
| `audit_reports` | array of [`AuditReportInfo`](#schema-auditreportinfo) | Yes | — | — |

<a id="schema-figuresout"></a>
#### `FiguresOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `period` | [`PeriodOut`](#schema-periodout) | Yes | — | — |
| `previous` | [`PeriodOut`](#schema-periodout) or `null` | Yes | — | — |
| `office` | `string` or `null` | Yes | — | — |
| `dim` | `string` or `null` | Yes | — | — |
| `grain` | `string` or `null` | Yes | — | — |
| `threshold` | `integer` | Yes | — | — |
| `metrics` | array of [`FigureOut`](#schema-figureout) | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-inventoryout"></a>
#### `InventoryOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purposes` | array of `object` | Yes | — | — |
| `processors` | array of `object` | Yes | — | — |
| `sources` | array of `object` | Yes | — | — |

<a id="schema-settingsout"></a>
#### `SettingsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `small_number_threshold` | `integer` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |
| `targets` | array of [`TargetOut`](#schema-targetout) | Yes | — | — |

<a id="schema-targetin"></a>
#### `TargetIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `target` | `number` | Yes | minimum: `0.0` | — |
| `amber` | `number` or `null` | No | minimum: `0.0` | — |

<a id="schema-thresholdin"></a>
#### `ThresholdIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `small_number_threshold` | `integer` | Yes | minimum: `1.0`; maximum: `100.0` | — |

<a id="schema-periodout"></a>
#### `PeriodOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `preset` | `string` | Yes | — | — |
| `start` | `string` | Yes | format: `date-time` | — |
| `end` | `string` | Yes | format: `date-time` | — |
| `label` | `string` | Yes | — | — |
| `start_date` | `string` | Yes | format: `date` | — |
| `end_date` | `string` | Yes | format: `date` | — |

<a id="schema-auditrowout"></a>
#### `AuditRowOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `log_uuid` | `string` | Yes | format: `uuid` | — |
| `event_type` | `string` | Yes | — | — |
| `entity_type` | `string` or `null` | No | — | — |
| `occurred_at` | `string` | Yes | format: `date-time` | — |
| `actor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `actor_name` | `string` or `null` | No | — | — |
| `actor_role` | `string` or `null` | No | — | — |
| `subject_uuid` | `string` or `null` | No | format: `uuid` | — |
| `subject_name` | `string` or `null` | No | — | — |
| `detail` | `object` or `null` | No | — | — |

<a id="schema-metricinfo"></a>
#### `MetricInfo`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `definition` | `string` | Yes | — | — |
| `unit` | `string` | Yes | — | — |
| `section` | `string` | Yes | — | — |
| `group` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `dims` | array of `string` | Yes | — | — |
| `people` | `boolean` | Yes | — | — |
| `numerator` | `string` or `null` | No | — | — |
| `denominator` | `string` or `null` | No | — | — |
| `higher_is_better` | `boolean` | No | default: `True` | — |

<a id="schema-choice"></a>
#### `Choice`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

<a id="schema-reportkindinfo"></a>
#### `ReportKindInfo`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |
| `formats` | array of `string` | Yes | — | — |
| `schedulable` | `boolean` | Yes | — | — |
| `recipient_roles` | array of `string` | Yes | — | — |

<a id="schema-auditreportinfo"></a>
#### `AuditReportInfo`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `description` | `string` | Yes | — | — |

<a id="schema-figureout"></a>
#### `FigureOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `definition` | `string` | Yes | — | — |
| `unit` | `string` | Yes | — | — |
| `section` | `string` | Yes | — | — |
| `group` | `string` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `dims` | array of `string` | Yes | — | — |
| `numerator` | `string` or `null` | No | — | — |
| `denominator` | `string` or `null` | No | — | — |
| `value` | `number` or `null` | Yes | — | — |
| `suppressed` | `boolean` | Yes | — | — |
| `previous` | `number` or `null` | Yes | — | — |
| `previous_suppressed` | `boolean` | Yes | — | — |
| `change` | `number` or `null` | Yes | — | — |
| `target` | `number` or `null` | Yes | — | — |
| `amber` | `number` or `null` | Yes | — | — |
| `higher_is_better` | `boolean` | Yes | — | — |
| `status` | `string` or `null` | Yes | — | — |
| `series` | array of [`PointOut`](#schema-pointout) | Yes | — | — |
| `breakdown` | array of [`PartOut`](#schema-partout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-targetout"></a>
#### `TargetOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `unit` | `string` | Yes | — | — |
| `section` | `string` | Yes | — | — |
| `group` | `string` | Yes | — | — |
| `higher_is_better` | `boolean` | Yes | — | — |
| `default_target` | `number` or `null` | Yes | — | — |
| `default_amber` | `number` or `null` | Yes | — | — |
| `target` | `number` or `null` | Yes | — | — |
| `amber` | `number` or `null` | Yes | — | — |
| `customised` | `boolean` | Yes | — | — |
| `updated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `updated_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-pointout"></a>
#### `PointOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `bucket` | `string` or `null` | Yes | format: `date` | — |
| `value` | `number` or `null` | Yes | — | — |
| `suppressed` | `boolean` | Yes | — | — |

<a id="schema-partout"></a>
#### `PartOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` or `null` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `value` | `number` or `null` | Yes | — | — |
| `suppressed` | `boolean` | Yes | — | — |
