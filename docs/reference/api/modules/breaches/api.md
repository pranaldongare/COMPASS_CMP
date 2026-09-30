# Breaches API

Generated from `backend/api/openapi.json`. **21 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /breaches`](#1_get_breaches)
2. [`POST /breaches`](#2_post_breaches)
3. [`GET /breaches/{breach_uuid}`](#3_get_breaches_breach_uuid)
4. [`POST /breaches/{breach_uuid}/determinations`](#4_post_breaches_breach_uuid_determinations)
5. [`GET /breaches/{breach_uuid}/assessments`](#5_get_breaches_breach_uuid_assessments)
6. [`POST /breaches/{breach_uuid}/assessments`](#6_post_breaches_breach_uuid_assessments)
7. [`POST /breaches/{breach_uuid}/cert-in`](#7_post_breaches_breach_uuid_cert_in)
8. [`POST /breaches/{breach_uuid}/obligations/{duty}/complete`](#8_post_breaches_breach_uuid_obligations_duty_complete)
9. [`POST /breaches/{breach_uuid}/obligations/board_report/extension`](#9_post_breaches_breach_uuid_obligations_board_report_extension)
10. [`GET /breaches/{breach_uuid}/transitions`](#10_get_breaches_breach_uuid_transitions)
11. [`POST /breaches/{breach_uuid}/transition`](#11_post_breaches_breach_uuid_transition)
12. [`GET /breaches/{breach_uuid}/affected`](#12_get_breaches_breach_uuid_affected)
13. [`POST /breaches/{breach_uuid}/affected`](#13_post_breaches_breach_uuid_affected)
14. [`POST /breaches/{breach_uuid}/affected/preview`](#14_post_breaches_breach_uuid_affected_preview)
15. [`GET /breaches/{breach_uuid}/notices`](#15_get_breaches_breach_uuid_notices)
16. [`POST /breaches/{breach_uuid}/notices`](#16_post_breaches_breach_uuid_notices)
17. [`PUT /breaches/{breach_uuid}/notices/{notice_uuid}`](#17_put_breaches_breach_uuid_notices_notice_uuid)
18. [`POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve`](#18_post_breaches_breach_uuid_notices_notice_uuid_approve)
19. [`POST /breaches/{breach_uuid}/notices/send`](#19_post_breaches_breach_uuid_notices_send)
20. [`GET /breaches/{breach_uuid}/board/intimation`](#20_get_breaches_breach_uuid_board_intimation)
21. [`GET /breaches/{breach_uuid}/board/report`](#21_get_breaches_breach_uuid_board_report)

<a id="1_get_breaches"></a>
## 1. `GET /breaches` — The register, open first

### API

- **Operation ID:** `list_breaches_breaches_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | open or closed |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`BreachSummaryOut`](#schema-breachsummaryout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "breach_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "title": "string",
    "status": "string",
    "detected_at": "2026-09-17T12:00:00Z",
    "location": {
      "kind": "string",
      "processor_uuid": "…",
      "processor_name": "…",
      "source_uuid": "…",
      "source_name": "…",
      "detail": "…"
    },
    "determination": "string",
    "obligations": [
      {
        "obligation_uuid": "…",
        "duty": "…",
        "label": "…",
        "basis": "…",
        "created_at": "…",
        "state": "…",
        "due_at": "…",
        "anchored_at": "…",
        "completed_at": "…",
        "reference": "…",
        "extended_until": "…",
        "extension_requested_at": "…",
        "clock": "…",
        "events": "…"
      }
    ]
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

<a id="2_post_breaches"></a>
## 2. `POST /breaches` — Record a breach as it was noticed

### API

- **Operation ID:** `record_breach_breaches_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachIn`](#schema-breachin)

```json
{
  "title": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "location_kind": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "location_detail": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="3_get_breaches_breach_uuid"></a>
## 3. `GET /breaches/{breach_uuid}` — One breach, with every duty

### API

- **Operation ID:** `get_breach_breaches__breach_uuid__get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="4_post_breaches_breach_uuid_determinations"></a>
## 4. `POST /breaches/{breach_uuid}/determinations` — Record whether it is a personal data breach

### API

- **Operation ID:** `determine_breaches__breach_uuid__determinations_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachDeterminationIn`](#schema-breachdeterminationin)

```json
{
  "outcome": "string",
  "reasoning": "string",
  "became_aware_at": "2026-09-17T12:00:00Z"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="5_get_breaches_breach_uuid_assessments"></a>
## 5. `GET /breaches/{breach_uuid}/assessments` — Every revision of the assessment, newest first

### API

- **Operation ID:** `list_assessments_breaches__breach_uuid__assessments_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`BreachAssessmentOut`](#schema-breachassessmentout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "2026-09-17T12:00:00Z",
    "nature_extent": "string",
    "likely_impact": "string",
    "consequences": "string",
    "categories": [
      {
        "category": "…",
        "sealed": "…",
        "key_exposed": "…"
      }
    ],
    "circumstances": "string",
    "mitigation": "string",
    "protective_steps": "string",
    "caused_by_findings": "string",
    "remedial_measures": "string",
    "contact_point": "string",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "string"
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

<a id="6_post_breaches_breach_uuid_assessments"></a>
## 6. `POST /breaches/{breach_uuid}/assessments` — Revise what is known; the previous revision stays

### API

- **Operation ID:** `assess_breaches__breach_uuid__assessments_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachAssessmentIn`](#schema-breachassessmentin)

```json
{
  "began_at": "2026-09-17T12:00:00Z",
  "nature_extent": "string",
  "likely_impact": "string",
  "consequences": "string",
  "categories": [
    {
      "category": "string",
      "sealed": true,
      "key_exposed": false
    }
  ],
  "circumstances": "string",
  "mitigation": "string",
  "protective_steps": "string",
  "caused_by_findings": "string",
  "remedial_measures": "string",
  "contact_point": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="7_post_breaches_breach_uuid_cert_in"></a>
## 7. `POST /breaches/{breach_uuid}/cert-in` — Mark as a reportable cyber incident: CERT-In in six hours from detection

### API

- **Operation ID:** `mark_cert_in_breaches__breach_uuid__cert_in_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="8_post_breaches_breach_uuid_obligations_duty_complete"></a>
## 8. `POST /breaches/{breach_uuid}/obligations/{duty}/complete` — Record a submission made, with the regulator's reference

### API

- **Operation ID:** `complete_duty_breaches__breach_uuid__obligations__duty__complete_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `duty` | path | Yes | `string` | — | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachCompletionIn`](#schema-breachcompletionin)

```json
{
  "occurred_at": "2026-09-17T12:00:00Z",
  "reference": "string",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="9_post_breaches_breach_uuid_obligations_board_report_extension"></a>
## 9. `POST /breaches/{breach_uuid}/obligations/board_report/extension` — Record the longer period the Board allowed for the detailed report

### API

- **Operation ID:** `extend_report_breaches__breach_uuid__obligations_board_report_extension_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachExtensionIn`](#schema-breachextensionin)

```json
{
  "requested_at": "2026-09-17T12:00:00Z",
  "allowed_until": "2026-09-17T12:00:00Z",
  "reference": "string",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="10_get_breaches_breach_uuid_transitions"></a>
## 10. `GET /breaches/{breach_uuid}/transitions` — Whether it may close, and what stands in the way

### API

- **Operation ID:** `transitions_breaches__breach_uuid__transitions_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTransitionsOut`](#schema-breachtransitionsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "current": "string",
  "available": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
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

<a id="11_post_breaches_breach_uuid_transition"></a>
## 11. `POST /breaches/{breach_uuid}/transition` — Close or reopen a breach

### API

- **Operation ID:** `transition_breaches__breach_uuid__transition_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTransitionIn`](#schema-breachtransitionin)

```json
{
  "to": "string",
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "title": "string",
  "status": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "began_at_recorded": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "recorded_at": "2026-09-17T12:00:00Z",
  "recorded_by_name": "string",
  "determination": "string",
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "obligations": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
        "…"
      ]
    }
  ],
  "status_history": [
    {
      "from_status": "…",
      "to_status": "string",
      "reason": "…",
      "changed_at": "2026-09-17T12:00:00Z",
      "changed_by_name": "…"
    }
  ],
  "transitions": [
    {
      "to": "string",
      "allowed": true,
      "blocked_by": "…",
      "blockers": [
        "…"
      ],
      "reason_required": true
    }
  ],
  "without_delay_target_hours": 1.0
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

<a id="12_get_breaches_breach_uuid_affected"></a>
## 12. `GET /breaches/{breach_uuid}/affected` — Who the breach touched, as confirmed, with every revision

### API

- **Operation ID:** `list_affected_breaches__breach_uuid__affected_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `cursor` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachAffectedOut`](#schema-breachaffectedout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "total": 1,
  "revisions": [
    {
      "revision_uuid": "00000000-0000-4000-8000-000000000000",
      "revision": 1,
      "scopes": [
        "…"
      ],
      "derived": 1,
      "added_by_hand": 1,
      "excluded": 1,
      "newly_listed": 1,
      "note": "…",
      "confirmed_at": "2026-09-17T12:00:00Z",
      "confirmed_by_name": "…"
    }
  ],
  "people": [
    {
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "role": "string",
      "has_email": true,
      "has_mobile": true,
      "found_by": "string",
      "evidence": "…",
      "affected_uuid": "00000000-0000-4000-8000-000000000000",
      "revision": 1
    }
  ],
  "next_cursor": "string",
  "platform_tables": [
    "string"
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

<a id="13_post_breaches_breach_uuid_affected"></a>
## 13. `POST /breaches/{breach_uuid}/affected` — Confirm who the breach touched: a new revision, adding only the newly found

### API

- **Operation ID:** `confirm_affected_breaches__breach_uuid__affected_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachAffectedIn`](#schema-breachaffectedin)

```json
{
  "scopes": [
    {
      "kind": "string",
      "processor_uuid": "…",
      "source_uuid": "…",
      "tables": [
        "…"
      ],
      "since": "…",
      "until": "…"
    }
  ],
  "exclude": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "add": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachAffectedOut`](#schema-breachaffectedout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "total": 1,
  "revisions": [
    {
      "revision_uuid": "00000000-0000-4000-8000-000000000000",
      "revision": 1,
      "scopes": [
        "…"
      ],
      "derived": 1,
      "added_by_hand": 1,
      "excluded": 1,
      "newly_listed": 1,
      "note": "…",
      "confirmed_at": "2026-09-17T12:00:00Z",
      "confirmed_by_name": "…"
    }
  ],
  "people": [
    {
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "role": "string",
      "has_email": true,
      "has_mobile": true,
      "found_by": "string",
      "evidence": "…",
      "affected_uuid": "00000000-0000-4000-8000-000000000000",
      "revision": 1
    }
  ],
  "next_cursor": "string",
  "platform_tables": [
    "string"
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

<a id="14_post_breaches_breach_uuid_affected_preview"></a>
## 14. `POST /breaches/{breach_uuid}/affected/preview` — What the records show for these scopes, before confirming

### API

- **Operation ID:** `preview_affected_breaches__breach_uuid__affected_preview_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachPreviewIn`](#schema-breachpreviewin)

```json
{
  "scopes": [
    {
      "kind": "string",
      "processor_uuid": "…",
      "source_uuid": "…",
      "tables": [
        "…"
      ],
      "since": "…",
      "until": "…"
    }
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachPreviewOut`](#schema-breachpreviewout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "scopes": [
    {}
  ],
  "derived": 1,
  "already_listed": 1,
  "would_add": 1,
  "people": [
    {
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "role": "string",
      "has_email": true,
      "has_mobile": true,
      "found_by": "string",
      "evidence": "…",
      "already_listed": true
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

<a id="15_get_breaches_breach_uuid_notices"></a>
## 15. `GET /breaches/{breach_uuid}/notices` — Every version of the notice, and the account of who received which

### API

- **Operation ID:** `list_notices_breaches__breach_uuid__notices_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticesOut`](#schema-breachnoticesout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "versions": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "state": "string",
      "what_happened": "…",
      "consequences": "…",
      "measures": "…",
      "protective_steps": "…",
      "contact": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "created_by_name": "…",
      "updated_at": "2026-09-17T12:00:00Z",
      "approved_at": "…",
      "approved_by_name": "…"
    }
  ],
  "account": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "channel": "string",
      "status": "string",
      "people": 1,
      "last_at": "2026-09-17T12:00:00Z"
    }
  ],
  "failures": [
    {
      "version": 1,
      "channel": "string",
      "attempt": 1,
      "detail": {},
      "recorded_at": "2026-09-17T12:00:00Z",
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string"
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

<a id="16_post_breaches_breach_uuid_notices"></a>
## 16. `POST /breaches/{breach_uuid}/notices` — Start the next version of the notice, as a draft

### API

- **Operation ID:** `draft_notice_breaches__breach_uuid__notices_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachNoticeIn`](#schema-breachnoticein)

```json
{
  "what_happened": "string",
  "consequences": "string",
  "measures": "string",
  "protective_steps": "string",
  "contact": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachNoticesOut`](#schema-breachnoticesout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "versions": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "state": "string",
      "what_happened": "…",
      "consequences": "…",
      "measures": "…",
      "protective_steps": "…",
      "contact": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "created_by_name": "…",
      "updated_at": "2026-09-17T12:00:00Z",
      "approved_at": "…",
      "approved_by_name": "…"
    }
  ],
  "account": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "channel": "string",
      "status": "string",
      "people": 1,
      "last_at": "2026-09-17T12:00:00Z"
    }
  ],
  "failures": [
    {
      "version": 1,
      "channel": "string",
      "attempt": 1,
      "detail": {},
      "recorded_at": "2026-09-17T12:00:00Z",
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string"
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

<a id="17_put_breaches_breach_uuid_notices_notice_uuid"></a>
## 17. `PUT /breaches/{breach_uuid}/notices/{notice_uuid}` — Edit a draft notice

### API

- **Operation ID:** `edit_notice_breaches__breach_uuid__notices__notice_uuid__put`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachNoticeIn`](#schema-breachnoticein)

```json
{
  "what_happened": "string",
  "consequences": "string",
  "measures": "string",
  "protective_steps": "string",
  "contact": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticesOut`](#schema-breachnoticesout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "versions": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "state": "string",
      "what_happened": "…",
      "consequences": "…",
      "measures": "…",
      "protective_steps": "…",
      "contact": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "created_by_name": "…",
      "updated_at": "2026-09-17T12:00:00Z",
      "approved_at": "…",
      "approved_by_name": "…"
    }
  ],
  "account": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "channel": "string",
      "status": "string",
      "people": 1,
      "last_at": "2026-09-17T12:00:00Z"
    }
  ],
  "failures": [
    {
      "version": 1,
      "channel": "string",
      "attempt": 1,
      "detail": {},
      "recorded_at": "2026-09-17T12:00:00Z",
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string"
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

<a id="18_post_breaches_breach_uuid_notices_notice_uuid_approve"></a>
## 18. `POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve` — Approve the words; refused while any of the five is empty

### API

- **Operation ID:** `approve_notice_breaches__breach_uuid__notices__notice_uuid__approve_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `notice_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticesOut`](#schema-breachnoticesout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "versions": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "state": "string",
      "what_happened": "…",
      "consequences": "…",
      "measures": "…",
      "protective_steps": "…",
      "contact": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "created_by_name": "…",
      "updated_at": "2026-09-17T12:00:00Z",
      "approved_at": "…",
      "approved_by_name": "…"
    }
  ],
  "account": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "channel": "string",
      "status": "string",
      "people": 1,
      "last_at": "2026-09-17T12:00:00Z"
    }
  ],
  "failures": [
    {
      "version": 1,
      "channel": "string",
      "attempt": 1,
      "detail": {},
      "recorded_at": "2026-09-17T12:00:00Z",
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string"
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

<a id="19_post_breaches_breach_uuid_notices_send"></a>
## 19. `POST /breaches/{breach_uuid}/notices/send` — Send the approved notice to everyone listed who lacks it; never twice

### API

- **Operation ID:** `send_notice_breaches__breach_uuid__notices_send_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachNoticesOut`](#schema-breachnoticesout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "versions": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "state": "string",
      "what_happened": "…",
      "consequences": "…",
      "measures": "…",
      "protective_steps": "…",
      "contact": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "created_by_name": "…",
      "updated_at": "2026-09-17T12:00:00Z",
      "approved_at": "…",
      "approved_by_name": "…"
    }
  ],
  "account": [
    {
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "version": 1,
      "channel": "string",
      "status": "string",
      "people": 1,
      "last_at": "2026-09-17T12:00:00Z"
    }
  ],
  "failures": [
    {
      "version": 1,
      "channel": "string",
      "attempt": 1,
      "detail": {},
      "recorded_at": "2026-09-17T12:00:00Z",
      "person_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string"
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

<a id="20_get_breaches_breach_uuid_board_intimation"></a>
## 20. `GET /breaches/{breach_uuid}/board/intimation` — Draft the Board's initial intimation (Rule 7(2)(a)) from the register

### API

- **Operation ID:** `board_intimation_breaches__breach_uuid__board_intimation_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachIntimationOut`](#schema-breachintimationout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "document": "string",
  "basis": "string",
  "reference": "string",
  "title": "string",
  "generated_at": "2026-09-17T12:00:00Z",
  "determination": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "nature_extent": "string",
  "likely_impact": "string",
  "assessment_revision": 1,
  "missing": [
    "string"
  ],
  "duty": {
    "obligation_uuid": "00000000-0000-4000-8000-000000000000",
    "duty": "string",
    "label": "string",
    "basis": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "state": "string",
    "due_at": "…",
    "anchored_at": "…",
    "completed_at": "…",
    "reference": "…",
    "extended_until": "…",
    "extension_requested_at": "…",
    "clock": "…",
    "events": [
      "…"
    ]
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

<a id="21_get_breaches_breach_uuid_board_report"></a>
## 21. `GET /breaches/{breach_uuid}/board/report` — Draft the Board's detailed report (Rule 7(2)(b)), all six items

### API

- **Operation ID:** `board_report_breaches__breach_uuid__board_report_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachReportOut`](#schema-breachreportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "document": "string",
  "basis": "string",
  "reference": "string",
  "title": "string",
  "generated_at": "2026-09-17T12:00:00Z",
  "determination": "string",
  "detected_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "determinations": [
    {
      "determination_uuid": "00000000-0000-4000-8000-000000000000",
      "outcome": "string",
      "reasoning": "string",
      "became_aware_at": "…",
      "determined_at": "2026-09-17T12:00:00Z",
      "determined_by_name": "…"
    }
  ],
  "assessment": {
    "assessment_uuid": "00000000-0000-4000-8000-000000000000",
    "revision": 1,
    "began_at": "…",
    "nature_extent": "…",
    "likely_impact": "…",
    "consequences": "…",
    "categories": [
      "…"
    ],
    "circumstances": "…",
    "mitigation": "…",
    "protective_steps": "…",
    "caused_by_findings": "…",
    "remedial_measures": "…",
    "contact_point": "…",
    "revised_at": "2026-09-17T12:00:00Z",
    "revised_by_name": "…"
  },
  "assessment_revisions": 1,
  "facts": [
    {
      "item": "string",
      "label": "string",
      "text": "…"
    }
  ],
  "notices": {
    "sent": true,
    "statement": "string",
    "listed": 1,
    "notified": 1,
    "versions": [
      "…"
    ]
  },
  "missing": [
    "string"
  ],
  "duty": {
    "obligation_uuid": "00000000-0000-4000-8000-000000000000",
    "duty": "string",
    "label": "string",
    "basis": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "state": "string",
    "due_at": "…",
    "anchored_at": "…",
    "completed_at": "…",
    "reference": "…",
    "extended_until": "…",
    "extension_requested_at": "…",
    "clock": "…",
    "events": [
      "…"
    ]
  },
  "duties": [
    {
      "obligation_uuid": "00000000-0000-4000-8000-000000000000",
      "duty": "string",
      "label": "string",
      "basis": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "reference": "…",
      "extended_until": "…",
      "extension_requested_at": "…",
      "clock": "…",
      "events": [
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

# Referenced schemas

<a id="schema-breachaffectedin"></a>
#### `BreachAffectedIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `scopes` | array of [`BreachScopeIn`](#schema-breachscopein) | No | — | — |
| `exclude` | array of `string` | No | — | — |
| `add` | array of `string` | No | — | — |
| `note` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachaffectedout"></a>
#### `BreachAffectedOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `total` | `integer` | Yes | — | — |
| `revisions` | array of [`BreachAffectedRevisionOut`](#schema-breachaffectedrevisionout) | Yes | — | — |
| `people` | array of [`BreachAffectedPersonOut`](#schema-breachaffectedpersonout) | Yes | — | — |
| `next_cursor` | `string` or `null` | Yes | — | — |
| `platform_tables` | array of `string` | Yes | — | — |

<a id="schema-breachassessmentin"></a>
#### `BreachAssessmentIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `began_at` | `string` or `null` | No | format: `date-time` | — |
| `nature_extent` | `string` or `null` | No | max length: `8000` | — |
| `likely_impact` | `string` or `null` | No | max length: `8000` | — |
| `consequences` | `string` or `null` | No | max length: `8000` | — |
| `categories` | array of [`BreachCategoryIn`](#schema-breachcategoryin) | No | — | — |
| `circumstances` | `string` or `null` | No | max length: `8000` | — |
| `mitigation` | `string` or `null` | No | max length: `8000` | — |
| `protective_steps` | `string` or `null` | No | max length: `8000` | — |
| `caused_by_findings` | `string` or `null` | No | max length: `8000` | — |
| `remedial_measures` | `string` or `null` | No | max length: `8000` | — |
| `contact_point` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachcompletionin"></a>
#### `BreachCompletionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `occurred_at` | `string` | Yes | format: `date-time` | — |
| `reference` | `string` | Yes | min length: `1`; max length: `200` | — |
| `note` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachdeterminationin"></a>
#### `BreachDeterminationIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `outcome` | `string` | Yes | — | — |
| `reasoning` | `string` | Yes | min length: `1`; max length: `8000` | — |
| `became_aware_at` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-breachextensionin"></a>
#### `BreachExtensionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `requested_at` | `string` | Yes | format: `date-time` | — |
| `allowed_until` | `string` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | No | max length: `200` | — |
| `note` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachin"></a>
#### `BreachIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `title` | `string` | Yes | min length: `1`; max length: `300` | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | No | format: `date-time` | — |
| `location_kind` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `source_uuid` | `string` or `null` | No | format: `uuid` | — |
| `location_detail` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachintimationout"></a>
#### `BreachIntimationOut`

Rule 7(2)(a), drafted from the register. The platform never submits it.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `reference` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `generated_at` | `string` | Yes | format: `date-time` | — |
| `determination` | `string` | Yes | — | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `nature_extent` | `string` or `null` | Yes | — | — |
| `likely_impact` | `string` or `null` | Yes | — | — |
| `assessment_revision` | `integer` or `null` | Yes | — | — |
| `missing` | array of `string` | Yes | — | — |
| `duty` | [`BreachDutyOut`](#schema-breachdutyout) or `null` | Yes | — | — |

<a id="schema-breachnoticein"></a>
#### `BreachNoticeIn`

The five things Rule 7(1) requires. A draft may leave any empty;
approval may not. Written to be sent to everyone listed: name nobody.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `what_happened` | `string` or `null` | No | max length: `4000` | — |
| `consequences` | `string` or `null` | No | max length: `4000` | — |
| `measures` | `string` or `null` | No | max length: `4000` | — |
| `protective_steps` | `string` or `null` | No | max length: `4000` | — |
| `contact` | `string` or `null` | No | max length: `4000` | — |

<a id="schema-breachnoticesout"></a>
#### `BreachNoticesOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `versions` | array of [`BreachNoticeOut`](#schema-breachnoticeout) | Yes | — | — |
| `account` | array of [`BreachDeliveryCountOut`](#schema-breachdeliverycountout) | Yes | — | — |
| `failures` | array of [`BreachDeliveryFailureOut`](#schema-breachdeliveryfailureout) | Yes | — | — |
| `listed` | `integer` | Yes | — | — |
| `unnotified` | `integer` | Yes | — | — |
| `contents` | array of [`BreachNoticeContentOut`](#schema-breachnoticecontentout) | Yes | — | — |
| `duty` | `string` | Yes | — | — |

<a id="schema-breachout"></a>
#### `BreachOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `breach_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `began_at_recorded` | `string` or `null` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `recorded_by_name` | `string` or `null` | Yes | — | — |
| `determination` | `string` | Yes | — | — |
| `determinations` | array of [`BreachDeterminationOut`](#schema-breachdeterminationout) | Yes | — | — |
| `assessment` | [`BreachAssessmentOut`](#schema-breachassessmentout) or `null` | Yes | — | — |
| `assessment_revisions` | `integer` | Yes | — | — |
| `obligations` | array of [`BreachDutyOut`](#schema-breachdutyout) | Yes | — | — |
| `status_history` | array of [`BreachStatusChangeOut`](#schema-breachstatuschangeout) | Yes | — | — |
| `transitions` | array of [`BreachTransitionOut`](#schema-breachtransitionout) | Yes | — | — |
| `without_delay_target_hours` | `number` or `null` | Yes | — | — |

<a id="schema-breachpreviewin"></a>
#### `BreachPreviewIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `scopes` | array of [`BreachScopeIn`](#schema-breachscopein) | Yes | — | — |

<a id="schema-breachpreviewout"></a>
#### `BreachPreviewOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `scopes` | array of `object` | Yes | — | — |
| `derived` | `integer` | Yes | — | — |
| `already_listed` | `integer` | Yes | — | — |
| `would_add` | `integer` | Yes | — | — |
| `people` | array of [`BreachCandidateOut`](#schema-breachcandidateout) | Yes | — | — |

<a id="schema-breachreportout"></a>
#### `BreachReportOut`

Rule 7(2)(b), all six items, drafted from the register.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `reference` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `generated_at` | `string` | Yes | format: `date-time` | — |
| `determination` | `string` | Yes | — | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `determinations` | array of [`BreachDeterminationOut`](#schema-breachdeterminationout) | Yes | — | — |
| `assessment` | [`BreachAssessmentOut`](#schema-breachassessmentout) or `null` | Yes | — | — |
| `assessment_revisions` | `integer` | Yes | — | — |
| `facts` | array of [`BreachReportFactOut`](#schema-breachreportfactout) | Yes | — | — |
| `notices` | [`BreachNoticeAccountOut`](#schema-breachnoticeaccountout) | Yes | — | — |
| `missing` | array of `string` | Yes | — | — |
| `duty` | [`BreachDutyOut`](#schema-breachdutyout) or `null` | Yes | — | — |
| `duties` | array of [`BreachDutyOut`](#schema-breachdutyout) | Yes | — | — |

<a id="schema-breachtransitionin"></a>
#### `BreachTransitionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `to` | `string` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachtransitionsout"></a>
#### `BreachTransitionsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `current` | `string` | Yes | — | — |
| `available` | array of [`BreachTransitionOut`](#schema-breachtransitionout) | Yes | — | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-breachscopein"></a>
#### `BreachScopeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `source_uuid` | `string` or `null` | No | format: `uuid` | — |
| `tables` | array of `string` | No | — | — |
| `since` | `string` or `null` | No | format: `date-time` | — |
| `until` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-breachaffectedrevisionout"></a>
#### `BreachAffectedRevisionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `revision_uuid` | `string` | Yes | format: `uuid` | — |
| `revision` | `integer` | Yes | — | — |
| `scopes` | array of `object` | Yes | — | — |
| `derived` | `integer` | Yes | — | — |
| `added_by_hand` | `integer` | Yes | — | — |
| `excluded` | `integer` | Yes | — | — |
| `newly_listed` | `integer` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `confirmed_at` | `string` | Yes | format: `date-time` | — |
| `confirmed_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachaffectedpersonout"></a>
#### `BreachAffectedPersonOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `person_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |
| `role` | `string` | Yes | — | — |
| `has_email` | `boolean` | Yes | — | — |
| `has_mobile` | `boolean` | Yes | — | — |
| `found_by` | `string` | Yes | — | — |
| `evidence` | [`BreachEvidenceOut`](#schema-breachevidenceout) | Yes | — | — |
| `affected_uuid` | `string` | Yes | format: `uuid` | — |
| `revision` | `integer` | Yes | — | — |

<a id="schema-breachcategoryin"></a>
#### `BreachCategoryIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category` | `string` | Yes | min length: `1`; max length: `200` | — |
| `sealed` | `boolean` | Yes | — | — |
| `key_exposed` | `boolean` | No | default: `False` | — |

<a id="schema-breachlocationout"></a>
#### `BreachLocationOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `processor_name` | `string` or `null` | Yes | — | — |
| `source_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `source_name` | `string` or `null` | Yes | — | — |
| `detail` | `string` or `null` | Yes | — | — |

<a id="schema-breachdutyout"></a>
#### `BreachDutyOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `obligation_uuid` | `string` | Yes | format: `uuid` | — |
| `duty` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `state` | `string` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `anchored_at` | `string` or `null` | Yes | format: `date-time` | — |
| `completed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | Yes | — | — |
| `extended_until` | `string` or `null` | Yes | format: `date-time` | — |
| `extension_requested_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`BreachClockOut`](#schema-breachclockout) | Yes | — | — |
| `events` | array of [`BreachDutyEventOut`](#schema-breachdutyeventout) | Yes | — | — |

<a id="schema-breachnoticeout"></a>
#### `BreachNoticeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `version` | `integer` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `what_happened` | `string` or `null` | Yes | — | — |
| `consequences` | `string` or `null` | Yes | — | — |
| `measures` | `string` or `null` | Yes | — | — |
| `protective_steps` | `string` or `null` | Yes | — | — |
| `contact` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `created_by_name` | `string` or `null` | Yes | — | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `approved_at` | `string` or `null` | Yes | format: `date-time` | — |
| `approved_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachdeliverycountout"></a>
#### `BreachDeliveryCountOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `version` | `integer` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `people` | `integer` | Yes | — | — |
| `last_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-breachdeliveryfailureout"></a>
#### `BreachDeliveryFailureOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `version` | `integer` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `attempt` | `integer` | Yes | — | — |
| `detail` | `object` | Yes | — | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `person_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachnoticecontentout"></a>
#### `BreachNoticeContentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

<a id="schema-breachdeterminationout"></a>
#### `BreachDeterminationOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `determination_uuid` | `string` | Yes | format: `uuid` | — |
| `outcome` | `string` | Yes | — | — |
| `reasoning` | `string` | Yes | — | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `determined_at` | `string` | Yes | format: `date-time` | — |
| `determined_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachassessmentout"></a>
#### `BreachAssessmentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `assessment_uuid` | `string` | Yes | format: `uuid` | — |
| `revision` | `integer` | Yes | — | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `nature_extent` | `string` or `null` | Yes | — | — |
| `likely_impact` | `string` or `null` | Yes | — | — |
| `consequences` | `string` or `null` | Yes | — | — |
| `categories` | array of [`BreachCategoryOut`](#schema-breachcategoryout) | Yes | — | — |
| `circumstances` | `string` or `null` | Yes | — | — |
| `mitigation` | `string` or `null` | Yes | — | — |
| `protective_steps` | `string` or `null` | Yes | — | — |
| `caused_by_findings` | `string` or `null` | Yes | — | — |
| `remedial_measures` | `string` or `null` | Yes | — | — |
| `contact_point` | `string` or `null` | Yes | — | — |
| `revised_at` | `string` | Yes | format: `date-time` | — |
| `revised_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachstatuschangeout"></a>
#### `BreachStatusChangeOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `from_status` | `string` or `null` | Yes | — | — |
| `to_status` | `string` | Yes | — | — |
| `reason` | `string` or `null` | Yes | — | — |
| `changed_at` | `string` | Yes | format: `date-time` | — |
| `changed_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachtransitionout"></a>
#### `BreachTransitionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `to` | `string` | Yes | — | — |
| `allowed` | `boolean` | Yes | — | — |
| `blocked_by` | `string` or `null` | Yes | — | — |
| `blockers` | array of `string` | Yes | — | — |
| `reason_required` | `boolean` | Yes | — | — |

<a id="schema-breachcandidateout"></a>
#### `BreachCandidateOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `person_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |
| `role` | `string` | Yes | — | — |
| `has_email` | `boolean` | Yes | — | — |
| `has_mobile` | `boolean` | Yes | — | — |
| `found_by` | `string` | Yes | — | — |
| `evidence` | [`BreachEvidenceOut`](#schema-breachevidenceout) | Yes | — | — |
| `already_listed` | `boolean` | Yes | — | — |

<a id="schema-breachreportfactout"></a>
#### `BreachReportFactOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `item` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `text` | `string` or `null` | Yes | — | — |

<a id="schema-breachnoticeaccountout"></a>
#### `BreachNoticeAccountOut`

Rule 7(2)(b)(vi). Present whether or not anything was sent.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `sent` | `boolean` | Yes | — | — |
| `statement` | `string` | Yes | — | — |
| `listed` | `integer` | Yes | — | — |
| `notified` | `integer` | Yes | — | — |
| `versions` | array of [`BreachNoticeVersionCountOut`](#schema-breachnoticeversioncountout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-breachevidenceout"></a>
#### `BreachEvidenceOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `exports` | array of `string` | No | — | — |
| `assets` | array of `string` | No | — | — |
| `tables` | array of `string` | No | — | — |

<a id="schema-breachclockout"></a>
#### `BreachClockOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `without_delay` | `boolean` | Yes | — | — |
| `seconds_remaining` | `integer` or `null` | Yes | — | — |
| `overdue` | `boolean` | Yes | — | — |
| `seconds_elapsed` | `integer` or `null` | Yes | — | — |
| `target_at` | `string` or `null` | Yes | format: `date-time` | — |
| `past_target` | `boolean` | Yes | — | — |

<a id="schema-breachdutyeventout"></a>
#### `BreachDutyEventOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `event_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `occurred_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `requested_at` | `string` or `null` | Yes | format: `date-time` | — |
| `determination_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `recorded_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachcategoryout"></a>
#### `BreachCategoryOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `category` | `string` | Yes | — | — |
| `sealed` | `boolean` | Yes | — | — |
| `key_exposed` | `boolean` | Yes | — | — |

<a id="schema-breachnoticeversioncountout"></a>
#### `BreachNoticeVersionCountOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `version` | `integer` | Yes | — | — |
| `approved_at` | `string` or `null` | Yes | format: `date-time` | — |
| `channels` | array of [`BreachChannelCountOut`](#schema-breachchannelcountout) | Yes | — | — |

<a id="schema-breachchannelcountout"></a>
#### `BreachChannelCountOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `channel` | `string` | Yes | — | — |
| `delivered` | `integer` | Yes | — | — |
| `queued` | `integer` | Yes | — | — |
| `failed` | `integer` | Yes | — | — |
