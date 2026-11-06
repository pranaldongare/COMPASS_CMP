# Incident Reports API

Generated from `backend/api/openapi.json`. **2 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`POST /incident-reports/code`](#1_post_incident_reports_code)
2. [`POST /incident-reports`](#2_post_incident_reports)

<a id="1_post_incident_reports_code"></a>
## 1. `POST /incident-reports/code` — A code to the address given

### API

- **Operation ID:** `report_code_incident_reports_code_post`
- **Access:** Role-controlled `incident reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`IncidentCodeIn`](#schema-incidentcodein)

```json
{
  "email": "string"
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

<a id="2_post_incident_reports"></a>
## 2. `POST /incident-reports` — Report an incident, with the code

### API

- **Operation ID:** `report_incident_incident_reports_post`
- **Access:** Role-controlled `incident reports` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`IncidentReportIn`](#schema-incidentreportin)

```json
{
  "name": "string",
  "email": "string",
  "code": "string",
  "title": "string",
  "incident_details": "string",
  "noticed_at": "2026-09-17T12:00:00Z",
  "origin": "string",
  "discovery": "string",
  "affected_systems": "string",
  "impact_scale": "string",
  "countries_involved": "string",
  "data_nature": "string",
  "subject_types": "string",
  "entities_involved": "string",
  "third_parties": "string",
  "cyber_attack": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`IncidentReportReceivedOut`](#schema-incidentreportreceivedout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "reference": "string",
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

<a id="schema-incidentcodein"></a>
#### `IncidentCodeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `email` | `string` | Yes | max length: `255`; format: `email` | — |

<a id="schema-incidentreportin"></a>
#### `IncidentReportIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `email` | `string` | Yes | max length: `255`; format: `email` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |
| `title` | `string` | Yes | min length: `1`; max length: `300` | — |
| `incident_details` | `string` | Yes | min length: `1`; max length: `8000` | — |
| `noticed_at` | `string` or `null` | No | format: `date-time` | — |
| `origin` | `string` or `null` | No | max length: `8000` | — |
| `discovery` | `string` or `null` | No | max length: `8000` | — |
| `affected_systems` | `string` or `null` | No | max length: `8000` | — |
| `impact_scale` | `string` or `null` | No | max length: `8000` | — |
| `countries_involved` | `string` or `null` | No | max length: `8000` | — |
| `data_nature` | `string` or `null` | No | max length: `8000` | — |
| `subject_types` | `string` or `null` | No | max length: `8000` | — |
| `entities_involved` | `string` or `null` | No | max length: `8000` | — |
| `third_parties` | `string` or `null` | No | max length: `8000` | — |
| `cyber_attack` | `string` or `null` | No | pattern: `^(yes|no|unknown)$` | — |

<a id="schema-incidentreportreceivedout"></a>
#### `IncidentReportReceivedOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reference` | `string` | Yes | — | — |
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
