# Breaches API

Generated from `backend/api/openapi.json`. **52 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /breaches`](#1_get_breaches)
2. [`POST /breaches`](#2_post_breaches)
3. [`GET /breaches/intake`](#3_get_breaches_intake)
4. [`GET /breaches/intake/dismissed`](#4_get_breaches_intake_dismissed)
5. [`GET /breaches/intake/{report_uuid}`](#5_get_breaches_intake_report_uuid)
6. [`POST /breaches/intake/{report_uuid}/claim`](#6_post_breaches_intake_report_uuid_claim)
7. [`POST /breaches/intake/{report_uuid}/dismiss`](#7_post_breaches_intake_report_uuid_dismiss)
8. [`GET /breaches/{breach_uuid}`](#8_get_breaches_breach_uuid)
9. [`POST /breaches/{breach_uuid}/determinations`](#9_post_breaches_breach_uuid_determinations)
10. [`GET /breaches/{breach_uuid}/assessments`](#10_get_breaches_breach_uuid_assessments)
11. [`POST /breaches/{breach_uuid}/assessments`](#11_post_breaches_breach_uuid_assessments)
12. [`POST /breaches/{breach_uuid}/attachments`](#12_post_breaches_breach_uuid_attachments)
13. [`GET /breaches/{breach_uuid}/attachments/{attachment_uuid}`](#13_get_breaches_breach_uuid_attachments_attachment_uuid)
14. [`POST /breaches/{breach_uuid}/cert-in`](#14_post_breaches_breach_uuid_cert_in)
15. [`POST /breaches/{breach_uuid}/cert-in/not-applicable`](#15_post_breaches_breach_uuid_cert_in_not_applicable)
16. [`POST /breaches/{breach_uuid}/obligations/board_report/extension`](#16_post_breaches_breach_uuid_obligations_board_report_extension)
17. [`GET /breaches/{breach_uuid}/transitions`](#17_get_breaches_breach_uuid_transitions)
18. [`POST /breaches/{breach_uuid}/transition`](#18_post_breaches_breach_uuid_transition)
19. [`GET /breaches/{breach_uuid}/affected`](#19_get_breaches_breach_uuid_affected)
20. [`POST /breaches/{breach_uuid}/affected`](#20_post_breaches_breach_uuid_affected)
21. [`GET /breaches/{breach_uuid}/affected/options`](#21_get_breaches_breach_uuid_affected_options)
22. [`POST /breaches/{breach_uuid}/affected/preview`](#22_post_breaches_breach_uuid_affected_preview)
23. [`GET /breaches/{breach_uuid}/affected/upload/template`](#23_get_breaches_breach_uuid_affected_upload_template)
24. [`POST /breaches/{breach_uuid}/affected/upload/check`](#24_post_breaches_breach_uuid_affected_upload_check)
25. [`POST /breaches/{breach_uuid}/affected/upload`](#25_post_breaches_breach_uuid_affected_upload)
26. [`GET /breaches/{breach_uuid}/affected/contacts`](#26_get_breaches_breach_uuid_affected_contacts)
27. [`GET /breaches/{breach_uuid}/notices`](#27_get_breaches_breach_uuid_notices)
28. [`POST /breaches/{breach_uuid}/notices`](#28_post_breaches_breach_uuid_notices)
29. [`PUT /breaches/{breach_uuid}/notices/{notice_uuid}`](#29_put_breaches_breach_uuid_notices_notice_uuid)
30. [`POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve`](#30_post_breaches_breach_uuid_notices_notice_uuid_approve)
31. [`POST /breaches/{breach_uuid}/notices/send`](#31_post_breaches_breach_uuid_notices_send)
32. [`GET /breaches/{breach_uuid}/board/intimation`](#32_get_breaches_breach_uuid_board_intimation)
33. [`GET /breaches/{breach_uuid}/board/report`](#33_get_breaches_breach_uuid_board_report)
34. [`GET /breaches/{breach_uuid}/org-board/brief`](#34_get_breaches_breach_uuid_org_board_brief)
35. [`GET /breaches/{breach_uuid}/reports`](#35_get_breaches_breach_uuid_reports)
36. [`POST /breaches/{breach_uuid}/reports`](#36_post_breaches_breach_uuid_reports)
37. [`PUT /breaches/{breach_uuid}/reports/{report_uuid}`](#37_put_breaches_breach_uuid_reports_report_uuid)
38. [`POST /breaches/{breach_uuid}/reports/{report_uuid}/finalise`](#38_post_breaches_breach_uuid_reports_report_uuid_finalise)
39. [`POST /breaches/{breach_uuid}/reports/{report_uuid}/resend`](#39_post_breaches_breach_uuid_reports_report_uuid_resend)
40. [`POST /breaches/{breach_uuid}/reports/{report_uuid}/evidence`](#40_post_breaches_breach_uuid_reports_report_uuid_evidence)
41. [`POST /breaches/{breach_uuid}/reports/{report_uuid}/file`](#41_post_breaches_breach_uuid_reports_report_uuid_file)
42. [`GET /breaches/{breach_uuid}/reports/{report_uuid}/pdf`](#42_get_breaches_breach_uuid_reports_report_uuid_pdf)
43. [`GET /breaches/{breach_uuid}/tickets`](#43_get_breaches_breach_uuid_tickets)
44. [`POST /breaches/{breach_uuid}/tickets`](#44_post_breaches_breach_uuid_tickets)
45. [`GET /breaches/{breach_uuid}/tickets/{ticket_uuid}`](#45_get_breaches_breach_uuid_tickets_ticket_uuid)
46. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages`](#46_post_breaches_breach_uuid_tickets_ticket_uuid_messages)
47. [`GET /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages/{message_uuid}/evidence`](#47_get_breaches_breach_uuid_tickets_ticket_uuid_messages_message_uuid_evidence)
48. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/resolve-by`](#48_post_breaches_breach_uuid_tickets_ticket_uuid_resolve_by)
49. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/send-back`](#49_post_breaches_breach_uuid_tickets_ticket_uuid_send_back)
50. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/close`](#50_post_breaches_breach_uuid_tickets_ticket_uuid_close)
51. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/withdraw`](#51_post_breaches_breach_uuid_tickets_ticket_uuid_withdraw)
52. [`POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/reopen`](#52_post_breaches_breach_uuid_tickets_ticket_uuid_reopen)

<a id="1_get_breaches"></a>
## 1. `GET /breaches` — Every incident and breach, open first

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
    "incident_reference": "string",
    "breach_reference": "string",
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
        "reported_to": "…",
        "extended_until": "…",
        "extension_requested_at": "…",
        "clock": "…",
        "events": "…"
      }
    ],
    "last_activity_at": "2026-09-17T12:00:00Z",
    "tickets_open": 1,
    "tickets_overdue": 1
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
## 2. `POST /breaches` — Log an incident as it was noticed

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
  "location_detail": "string",
  "origin": "string",
  "discovery": "string",
  "affected_systems": "string",
  "incident_details": "string",
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
| `201` | Successful Response | `application/json` | [`BreachOut`](#schema-breachout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "breach_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="3_get_breaches_intake"></a>
## 3. `GET /breaches/intake` — A page of the reports from the public link no office has taken up

### API

- **Operation ID:** `incident_reports_breaches_intake_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `limit` | query | No | `integer` | minimum: `1`; maximum: `200`; default: `50` | — |
| `offset` | query | No | `integer` | minimum: `0`; maximum: `1000000`; default: `0` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`IncidentReportPageOut`](#schema-incidentreportpageout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "report_uuid": "00000000-0000-4000-8000-000000000000",
      "reference": "string",
      "reporter_name": "string",
      "reporter_email": "string",
      "title": "string",
      "noticed_at": "…",
      "received_at": "2026-09-17T12:00:00Z",
      "cyber_attack": "…"
    }
  ],
  "total": 1,
  "limit": 1,
  "offset": 1
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

<a id="4_get_breaches_intake_dismissed"></a>
## 4. `GET /breaches/intake/dismissed` — Reports an office dismissed, newest first, with who did it and why

### API

- **Operation ID:** `dismissed_reports_breaches_intake_dismissed_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`DismissedReportOut`](#schema-dismissedreportout) |

**Example `200` `application/json` response:**

```json
[
  {
    "reference": "string",
    "reporter_name": "string",
    "reporter_email": "string",
    "title": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "dismissed_at": "2026-09-17T12:00:00Z",
    "dismissed_by_name": "string",
    "dismissal_reason": "string"
  }
]
```

<a id="5_get_breaches_intake_report_uuid"></a>
## 5. `GET /breaches/intake/{report_uuid}` — One waiting report in full

### API

- **Operation ID:** `incident_report_breaches_intake__report_uuid__get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`IncidentReportOut`](#schema-incidentreportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "report_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "reporter_name": "string",
  "reporter_email": "string",
  "title": "string",
  "noticed_at": "2026-09-17T12:00:00Z",
  "received_at": "2026-09-17T12:00:00Z",
  "cyber_attack": "string",
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
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

<a id="6_post_breaches_intake_report_uuid_claim"></a>
## 6. `POST /breaches/intake/{report_uuid}/claim` — Take a report into this office's register, as an incident

### API

- **Operation ID:** `claim_report_breaches_intake__report_uuid__claim_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="7_post_breaches_intake_report_uuid_dismiss"></a>
## 7. `POST /breaches/intake/{report_uuid}/dismiss` — Dismiss a report, saying why; it is kept

### API

- **Operation ID:** `dismiss_report_breaches_intake__report_uuid__dismiss_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`IncidentDismissalIn`](#schema-incidentdismissalin)

```json
{
  "reason": "string"
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

<a id="8_get_breaches_breach_uuid"></a>
## 8. `GET /breaches/{breach_uuid}` — One incident or breach, with every duty

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="9_post_breaches_breach_uuid_determinations"></a>
## 9. `POST /breaches/{breach_uuid}/determinations` — Validate: is it a personal data breach? The first yes records it

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="10_get_breaches_breach_uuid_assessments"></a>
## 10. `GET /breaches/{breach_uuid}/assessments` — Every revision of the assessment, newest first

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

<a id="11_post_breaches_breach_uuid_assessments"></a>
## 11. `POST /breaches/{breach_uuid}/assessments` — Revise what is known; the previous revision stays

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="12_post_breaches_breach_uuid_attachments"></a>
## 12. `POST /breaches/{breach_uuid}/attachments` — Keep a file with the incident: an email, a proof, a chat

### API

- **Operation ID:** `add_attachment_breaches__breach_uuid__attachments_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

Evidence, kept as it came: never replaced or removed. Refused on a closed
breach, like every write to one.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_add_attachment_breaches__breach_uuid__attachments_post`](#schema-body_add_attachment_breaches_breach_uuid_attachments_post)

```json
{
  "file": "string",
  "kind": "other",
  "note": "string"
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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="13_get_breaches_breach_uuid_attachments_attachment_uuid"></a>
## 13. `GET /breaches/{breach_uuid}/attachments/{attachment_uuid}` — Download a file kept with the incident; every download is audited

### API

- **Operation ID:** `attachment_file_breaches__breach_uuid__attachments__attachment_uuid__get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `attachment_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="14_post_breaches_breach_uuid_cert_in"></a>
## 14. `POST /breaches/{breach_uuid}/cert-in` — Mark as a reportable cyber incident: CERT-In in six hours from detection

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="15_post_breaches_breach_uuid_cert_in_not_applicable"></a>
## 15. `POST /breaches/{breach_uuid}/cert-in/not-applicable` — Set aside a CERT-In mark made in error, once validated No; nobody is told

### API

- **Operation ID:** `set_aside_cert_in_breaches__breach_uuid__cert_in_not_applicable_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CertInSetAsideIn`](#schema-certinsetasidein)

```json
{
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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="16_post_breaches_breach_uuid_obligations_board_report_extension"></a>
## 16. `POST /breaches/{breach_uuid}/obligations/board_report/extension` — Record the longer period the Board allowed for the detailed report

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="17_get_breaches_breach_uuid_transitions"></a>
## 17. `GET /breaches/{breach_uuid}/transitions` — Whether it may close, and what stands in the way

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

<a id="18_post_breaches_breach_uuid_transition"></a>
## 18. `POST /breaches/{breach_uuid}/transition` — Close or reopen a breach

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
  "incident_reference": "string",
  "breach_reference": "string",
  "breach_recorded_at": "2026-09-17T12:00:00Z",
  "breach_recorded_by_name": "string",
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
  "logged": {
    "origin": "string",
    "discovery": "string",
    "affected_systems": "string",
    "incident_details": "string",
    "impact_scale": "string",
    "countries_involved": "string",
    "data_nature": "string",
    "subject_types": "string",
    "entities_involved": "string",
    "third_parties": "string"
  },
  "cyber_attack": "string",
  "reported": {
    "reporter_name": "string",
    "reporter_email": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "noticed_at": "…",
    "cyber_attack": "…"
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
      "reported_to": "…",
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
  "attachments": [
    {
      "attachment_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "note": "…",
      "file_name": "string",
      "sha256": "string",
      "size_bytes": 1,
      "content_type": "string",
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="19_get_breaches_breach_uuid_affected"></a>
## 19. `GET /breaches/{breach_uuid}/affected` — The people affected, as confirmed, with every revision

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
  "next_cursor": "string"
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

<a id="20_post_breaches_breach_uuid_affected"></a>
## 20. `POST /breaches/{breach_uuid}/affected` — Confirm the people affected: a new revision, adding only the newly found

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
      "project_uuid": "…",
      "processor_uuid": "…",
      "source_uuid": "…",
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
  "next_cursor": "string"
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

<a id="21_get_breaches_breach_uuid_affected_options"></a>
## 21. `GET /breaches/{breach_uuid}/affected/options` — The projects and activities to choose from, with how many people each

### API

- **Operation ID:** `affected_options_breaches__breach_uuid__affected_options_get`
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
| `200` | Successful Response | `application/json` | [`BreachAffectedOptionsOut`](#schema-breachaffectedoptionsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "projects": [
    {
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "is_activity": true,
      "people": 1
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

<a id="22_post_breaches_breach_uuid_affected_preview"></a>
## 22. `POST /breaches/{breach_uuid}/affected/preview` — What the records show for these scopes, before confirming

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
      "project_uuid": "…",
      "processor_uuid": "…",
      "source_uuid": "…",
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

<a id="23_get_breaches_breach_uuid_affected_upload_template"></a>
## 23. `GET /breaches/{breach_uuid}/affected/upload/template` — The Excel file to fill in: people (name, email, mobile) or asset IDs

### API

- **Operation ID:** `list_template_breaches__breach_uuid__affected_upload_template_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `kind` | query | No | `string` | pattern: `^(contacts|assets)$`; default: `contacts` | — |

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

<a id="24_post_breaches_breach_uuid_affected_upload_check"></a>
## 24. `POST /breaches/{breach_uuid}/affected/upload/check` — What a list would add, and each row it cannot read - nothing is written

### API

- **Operation ID:** `check_list_breaches__breach_uuid__affected_upload_check_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_check_list_breaches__breach_uuid__affected_upload_check_post`](#schema-body_check_list_breaches_breach_uuid_affected_upload_check_post)

```json
{
  "kind": "string",
  "file": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachListReportOut`](#schema-breachlistreportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kind": "string",
  "rows_read": 1,
  "matched_people": 1,
  "new_contacts": 1,
  "already_listed": 1,
  "unreadable": 1,
  "untraceable": 1,
  "would_add": 1,
  "errors": [
    {
      "row": 1,
      "message": "string"
    }
  ],
  "more_errors": 1,
  "upload_uuid": "00000000-0000-4000-8000-000000000000"
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

<a id="25_post_breaches_breach_uuid_affected_upload"></a>
## 25. `POST /breaches/{breach_uuid}/affected/upload` — Add the people a list names, or the people in the assets it names

### API

- **Operation ID:** `take_list_breaches__breach_uuid__affected_upload_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

People with an account join the list as themselves; anybody else is
kept, sealed, as a contact of this breach alone, and is sent the notice by
email and SMS. Rows that cannot be read are left out and reported. The file
is not kept.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_take_list_breaches__breach_uuid__affected_upload_post`](#schema-body_take_list_breaches_breach_uuid_affected_upload_post)

```json
{
  "kind": "string",
  "file": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachListReportOut`](#schema-breachlistreportout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "kind": "string",
  "rows_read": 1,
  "matched_people": 1,
  "new_contacts": 1,
  "already_listed": 1,
  "unreadable": 1,
  "untraceable": 1,
  "would_add": 1,
  "errors": [
    {
      "row": 1,
      "message": "string"
    }
  ],
  "more_errors": 1,
  "upload_uuid": "00000000-0000-4000-8000-000000000000"
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

<a id="26_get_breaches_breach_uuid_affected_contacts"></a>
## 26. `GET /breaches/{breach_uuid}/affected/contacts` — People affected who have no account, and the lists they came in

### API

- **Operation ID:** `list_contacts_breaches__breach_uuid__affected_contacts_get`
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
| `200` | Successful Response | `application/json` | [`BreachContactsOut`](#schema-breachcontactsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "total": 1,
  "contacts": [
    {
      "contact_uuid": "00000000-0000-4000-8000-000000000000",
      "full_name": "…",
      "email": "…",
      "mobile": "…",
      "added_at": "2026-09-17T12:00:00Z",
      "upload_uuid": "00000000-0000-4000-8000-000000000000",
      "upload_kind": "string"
    }
  ],
  "next_cursor": "string",
  "uploads": [
    {
      "upload_uuid": "00000000-0000-4000-8000-000000000000",
      "kind": "string",
      "file_name": "string",
      "sha256": "string",
      "rows_read": 1,
      "matched_people": 1,
      "new_contacts": 1,
      "already_listed": 1,
      "unreadable": 1,
      "untraceable": 1,
      "added_at": "2026-09-17T12:00:00Z",
      "added_by_name": "…"
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

<a id="27_get_breaches_breach_uuid_notices"></a>
## 27. `GET /breaches/{breach_uuid}/notices` — Every version of the notice, and the account of who received which

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
      "person_uuid": "…",
      "contact_uuid": "…",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "contacts": 0,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string",
  "send_blocked_by": "string"
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

<a id="28_post_breaches_breach_uuid_notices"></a>
## 28. `POST /breaches/{breach_uuid}/notices` — Start the next version of the notice, as a draft

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
      "person_uuid": "…",
      "contact_uuid": "…",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "contacts": 0,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string",
  "send_blocked_by": "string"
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

<a id="29_put_breaches_breach_uuid_notices_notice_uuid"></a>
## 29. `PUT /breaches/{breach_uuid}/notices/{notice_uuid}` — Edit a draft notice

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
      "person_uuid": "…",
      "contact_uuid": "…",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "contacts": 0,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string",
  "send_blocked_by": "string"
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

<a id="30_post_breaches_breach_uuid_notices_notice_uuid_approve"></a>
## 30. `POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve` — Approve the words; refused while any of the five is empty

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
      "person_uuid": "…",
      "contact_uuid": "…",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "contacts": 0,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string",
  "send_blocked_by": "string"
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

<a id="31_post_breaches_breach_uuid_notices_send"></a>
## 31. `POST /breaches/{breach_uuid}/notices/send` — Send the approved notice to everyone listed who lacks it; never twice, never before the breach is recorded

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
      "person_uuid": "…",
      "contact_uuid": "…",
      "full_name": "…"
    }
  ],
  "listed": 1,
  "contacts": 0,
  "unnotified": 1,
  "contents": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "duty": "string",
  "send_blocked_by": "string"
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

<a id="32_get_breaches_breach_uuid_board_intimation"></a>
## 32. `GET /breaches/{breach_uuid}/board/intimation` — Draft the Board's initial intimation (Rule 7(2)(a)) from the register

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
  "incident_reference": "string",
  "breach_reference": "string",
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
    "reported_to": "…",
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

<a id="33_get_breaches_breach_uuid_board_report"></a>
## 33. `GET /breaches/{breach_uuid}/board/report` — Draft the Board's detailed report (Rule 7(2)(b)), all six items

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
  "incident_reference": "string",
  "breach_reference": "string",
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
    "reported_to": "…",
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
      "reported_to": "…",
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

<a id="34_get_breaches_breach_uuid_org_board_brief"></a>
## 34. `GET /breaches/{breach_uuid}/org-board/brief` — Draft the brief for the organisation's board from the register

### API

- **Operation ID:** `org_board_brief_breaches__breach_uuid__org_board_brief_get`
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
| `200` | Successful Response | `application/json` | [`OrgBoardBriefOut`](#schema-orgboardbriefout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "document": "string",
  "basis": "string",
  "reference": "string",
  "incident_reference": "string",
  "breach_reference": "string",
  "title": "string",
  "generated_at": "2026-09-17T12:00:00Z",
  "detected_at": "2026-09-17T12:00:00Z",
  "began_at": "2026-09-17T12:00:00Z",
  "location": {
    "kind": "string",
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "source_uuid": "00000000-0000-4000-8000-000000000000",
    "source_name": "string",
    "detail": "string"
  },
  "validation": "string",
  "became_aware_at": "2026-09-17T12:00:00Z",
  "cert_in_reportable": true,
  "duties": [
    {
      "duty": "string",
      "label": "string",
      "basis": "string",
      "state": "string",
      "due_at": "…",
      "anchored_at": "…",
      "completed_at": "…",
      "clock": "…"
    }
  ],
  "affected": {
    "listed": 1,
    "notified": 1
  },
  "missing": [
    "string"
  ],
  "duty": {
    "duty": "string",
    "label": "string",
    "basis": "string",
    "state": "string",
    "due_at": "…",
    "anchored_at": "…",
    "completed_at": "…",
    "clock": "…"
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

<a id="35_get_breaches_breach_uuid_reports"></a>
## 35. `GET /breaches/{breach_uuid}/reports` — Every kind of report on a breach, and where each stands

### API

- **Operation ID:** `list_reports_breaches__breach_uuid__reports_get`
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
| `200` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="36_post_breaches_breach_uuid_reports"></a>
## 36. `POST /breaches/{breach_uuid}/reports` — Start the next version of a report, drafted from the register

### API

- **Operation ID:** `draft_report_breaches__breach_uuid__reports_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachDocumentCreateIn`](#schema-breachdocumentcreatein)

```json
{
  "kind": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="37_put_breaches_breach_uuid_reports_report_uuid"></a>
## 37. `PUT /breaches/{breach_uuid}/reports/{report_uuid}` — Edit a draft report

### API

- **Operation ID:** `edit_report_breaches__breach_uuid__reports__report_uuid__put`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachDocumentIn`](#schema-breachdocumentin)

```json
{
  "sections": {}
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="38_post_breaches_breach_uuid_reports_report_uuid_finalise"></a>
## 38. `POST /breaches/{breach_uuid}/reports/{report_uuid}/finalise` — Freeze a report and mail the organisation's board; never a regulator

### API

- **Operation ID:** `finalise_report_breaches__breach_uuid__reports__report_uuid__finalise_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="39_post_breaches_breach_uuid_reports_report_uuid_resend"></a>
## 39. `POST /breaches/{breach_uuid}/reports/{report_uuid}/resend` — Mail the report to every address on the list it has not reached

### API

- **Operation ID:** `resend_report_breaches__breach_uuid__reports__report_uuid__resend_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachDocumentsResentOut`](#schema-breachdocumentsresentout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
    }
  ],
  "queued": 1
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

<a id="40_post_breaches_breach_uuid_reports_report_uuid_evidence"></a>
## 40. `POST /breaches/{breach_uuid}/reports/{report_uuid}/evidence` — Keep the proof of internal approval, or of the mail sent to the regulator

### API

- **Operation ID:** `add_report_proof_breaches__breach_uuid__reports__report_uuid__evidence_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_add_report_proof_breaches__breach_uuid__reports__report_uuid__evidence_post`](#schema-body_add_report_proof_breaches_breach_uuid_reports_report_uuid_evidence_post)

```json
{
  "file": "string",
  "kind": "string",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="41_post_breaches_breach_uuid_reports_report_uuid_file"></a>
## 41. `POST /breaches/{breach_uuid}/reports/{report_uuid}/file` — Record that a person sent it to the regulator; needs both proofs

### API

- **Operation ID:** `file_report_breaches__breach_uuid__reports__report_uuid__file_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachDocumentFilingIn`](#schema-breachdocumentfilingin)

```json
{
  "filed_at": "2026-09-17T12:00:00Z",
  "reference": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachDocumentsOut`](#schema-breachdocumentsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "kinds": [
    {
      "kind": "string",
      "title": "string",
      "basis": "string",
      "duty": "…",
      "duty_state": "…",
      "blocked_by": "…",
      "goes_to_regulator": true,
      "versions": [
        "…"
      ]
    }
  ],
  "board_recipients": 1,
  "proofs": [
    {
      "kind": "string",
      "label": "string"
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

<a id="42_get_breaches_breach_uuid_reports_report_uuid_pdf"></a>
## 42. `GET /breaches/{breach_uuid}/reports/{report_uuid}/pdf` — The report as a PDF; every read is audited

### API

- **Operation ID:** `report_pdf_breaches__breach_uuid__reports__report_uuid__pdf_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `report_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="43_get_breaches_breach_uuid_tickets"></a>
## 43. `GET /breaches/{breach_uuid}/tickets` — Every ticket on a breach: holder, state, answer-by, unread, who added whom

### API

- **Operation ID:** `list_tickets_breaches__breach_uuid__tickets_get`
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
| `200` | Successful Response | `application/json` | array of [`BreachTicketOut`](#schema-breachticketout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      {
        "event_uuid": "…",
        "kind": "…",
        "outcome": "…",
        "summary": "…",
        "reason": "…",
        "date_before": "…",
        "date_after": "…",
        "occurred_at": "…",
        "actor_name": "…"
      }
    ],
    "moves": [
      {
        "move": "…",
        "reason_required": "…"
      }
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
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

<a id="44_post_breaches_breach_uuid_tickets"></a>
## 44. `POST /breaches/{breach_uuid}/tickets` — Assign a ticket to a member of staff; only on a recorded breach

### API

- **Operation ID:** `assign_ticket_breaches__breach_uuid__tickets_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTicketIn`](#schema-breachticketin)

```json
{
  "user_uuid": "00000000-0000-4000-8000-000000000000",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "instruction": "string",
  "answer_by": "2026-09-17"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="45_get_breaches_breach_uuid_tickets_ticket_uuid"></a>
## 45. `GET /breaches/{breach_uuid}/tickets/{ticket_uuid}` — One ticket, its thread, and the moves the server allows

### API

- **Operation ID:** `get_ticket_breaches__breach_uuid__tickets__ticket_uuid__get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

Reading it marks the holder's messages read.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="46_post_breaches_breach_uuid_tickets_ticket_uuid_messages"></a>
## 46. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages` — Write to the holder on the ticket, with a file if it helps

### API

- **Operation ID:** `message_holder_breaches__breach_uuid__tickets__ticket_uuid__messages_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_message_holder_breaches__breach_uuid__tickets__ticket_uuid__messages_post`](#schema-body_message_holder_breaches_breach_uuid_tickets_ticket_uuid_messages_post)

```json
{
  "body": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="47_get_breaches_breach_uuid_tickets_ticket_uuid_messages_message_uuid_evidence"></a>
## 47. `GET /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages/{message_uuid}/evidence` — Download a file attached to a message on the ticket

### API

- **Operation ID:** `ticket_file_breaches__breach_uuid__tickets__ticket_uuid__messages__message_uuid__evidence_get`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |
| `message_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="48_post_breaches_breach_uuid_tickets_ticket_uuid_resolve_by"></a>
## 48. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/resolve-by` — Change the date to resolve the ticket by, saying why

### API

- **Operation ID:** `change_ticket_date_breaches__breach_uuid__tickets__ticket_uuid__resolve_by_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTicketDateIn`](#schema-breachticketdatein)

```json
{
  "answer_by": "2026-09-17",
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="49_post_breaches_breach_uuid_tickets_ticket_uuid_send_back"></a>
## 49. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/send-back` — Send a returned ticket back to its holder, saying why

### API

- **Operation ID:** `send_back_ticket_breaches__breach_uuid__tickets__ticket_uuid__send_back_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTicketReasonIn`](#schema-breachticketreasonin)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="50_post_breaches_breach_uuid_tickets_ticket_uuid_close"></a>
## 50. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/close` — Close a returned ticket: the DPO's alone

### API

- **Operation ID:** `close_ticket_breaches__breach_uuid__tickets__ticket_uuid__close_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="51_post_breaches_breach_uuid_tickets_ticket_uuid_withdraw"></a>
## 51. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/withdraw` — Withdraw a ticket, saying why

### API

- **Operation ID:** `withdraw_ticket_breaches__breach_uuid__tickets__ticket_uuid__withdraw_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTicketReasonIn`](#schema-breachticketreasonin)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="52_post_breaches_breach_uuid_tickets_ticket_uuid_reopen"></a>
## 52. `POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/reopen` — Reopen a closed or withdrawn ticket, saying why

### API

- **Operation ID:** `reopen_ticket_breaches__breach_uuid__tickets__ticket_uuid__reopen_post`
- **Access:** Role-controlled `breaches` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `breach_uuid` | path | Yes | `string` | format: `uuid` | — |
| `ticket_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`BreachTicketReasonIn`](#schema-breachticketreasonin)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`BreachTicketDetailOut`](#schema-breachticketdetailout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "ticket": {
    "ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_name": "string",
    "assigned_by_name": "string",
    "parent_ticket_uuid": "00000000-0000-4000-8000-000000000000",
    "added_by_name": "string",
    "state": "string",
    "answer_by": "2026-09-17",
    "overdue": true,
    "created_at": "2026-09-17T12:00:00Z",
    "unread": 1,
    "last_activity_at": "2026-09-17T12:00:00Z",
    "events": [
      "…"
    ],
    "moves": [
      "…"
    ],
    "may_write": true,
    "may_change_date": true,
    "temporary_access": "string"
  },
  "instruction": "string",
  "messages": [
    {
      "message_uuid": "00000000-0000-4000-8000-000000000000",
      "author_side": "string",
      "author_name": "…",
      "kind": "string",
      "body": "string",
      "evidence_hash": "…",
      "evidence_name": "…",
      "created_at": "2026-09-17T12:00:00Z"
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

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-body_add_attachment_breaches_breach_uuid_attachments_post"></a>
#### `Body_add_attachment_breaches__breach_uuid__attachments_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `file` | `string` | Yes | — | The file, max 25 MB |
| `kind` | `string` | No | default: `other` | email, proof, chat or other |
| `note` | `string` or `null` | No | max length: `500` | — |

<a id="schema-body_add_report_proof_breaches_breach_uuid_reports_report_uuid_evidence_post"></a>
#### `Body_add_report_proof_breaches__breach_uuid__reports__report_uuid__evidence_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `file` | `string` | Yes | — | The file, max 25 MB |
| `kind` | `string` | Yes | — | approval or sent_mail |
| `note` | `string` or `null` | No | max length: `500` | — |

<a id="schema-body_check_list_breaches_breach_uuid_affected_upload_check_post"></a>
#### `Body_check_list_breaches__breach_uuid__affected_upload_check_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | contacts (name, email, mobile) or assets (asset IDs) |
| `file` | `string` | Yes | — | The filled-in .xlsx or CSV, max 25 MB |

<a id="schema-body_message_holder_breaches_breach_uuid_tickets_ticket_uuid_messages_post"></a>
#### `Body_message_holder_breaches__breach_uuid__tickets__ticket_uuid__messages_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `body` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional file, max 25 MB |

<a id="schema-body_take_list_breaches_breach_uuid_affected_upload_post"></a>
#### `Body_take_list_breaches__breach_uuid__affected_upload_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | contacts (name, email, mobile) or assets (asset IDs) |
| `file` | `string` | Yes | — | The filled-in .xlsx or CSV, max 25 MB |

<a id="schema-breachaffectedin"></a>
#### `BreachAffectedIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `scopes` | array of [`BreachScopeIn`](#schema-breachscopein) | No | — | — |
| `exclude` | array of `string` | No | — | — |
| `add` | array of `string` | No | — | — |
| `note` | `string` or `null` | No | max length: `8000` | — |

<a id="schema-breachaffectedoptionsout"></a>
#### `BreachAffectedOptionsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `projects` | array of [`BreachProjectOptionOut`](#schema-breachprojectoptionout) | Yes | — | — |

<a id="schema-breachaffectedout"></a>
#### `BreachAffectedOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `total` | `integer` | Yes | — | — |
| `revisions` | array of [`BreachAffectedRevisionOut`](#schema-breachaffectedrevisionout) | Yes | — | — |
| `people` | array of [`BreachAffectedPersonOut`](#schema-breachaffectedpersonout) | Yes | — | — |
| `next_cursor` | `string` or `null` | Yes | — | — |

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

<a id="schema-breachcontactsout"></a>
#### `BreachContactsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `total` | `integer` | Yes | — | — |
| `contacts` | array of [`BreachContactOut`](#schema-breachcontactout) | Yes | — | — |
| `next_cursor` | `string` or `null` | Yes | — | — |
| `uploads` | array of [`BreachUploadOut`](#schema-breachuploadout) | Yes | — | — |

<a id="schema-breachdeterminationin"></a>
#### `BreachDeterminationIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `outcome` | `string` | Yes | — | — |
| `reasoning` | `string` | Yes | min length: `1`; max length: `8000` | — |
| `became_aware_at` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-breachdocumentcreatein"></a>
#### `BreachDocumentCreateIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |

<a id="schema-breachdocumentfilingin"></a>
#### `BreachDocumentFilingIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `filed_at` | `string` | Yes | format: `date-time` | — |
| `reference` | `string` or `null` | No | max length: `200` | — |

<a id="schema-breachdocumentin"></a>
#### `BreachDocumentIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `sections` | `object` | Yes | — | — |

<a id="schema-breachdocumentsout"></a>
#### `BreachDocumentsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kinds` | array of [`BreachDocumentKindOut`](#schema-breachdocumentkindout) | Yes | — | — |
| `board_recipients` | `integer` | Yes | — | — |
| `proofs` | array of [`BreachProofKindOut`](#schema-breachproofkindout) | Yes | — | — |

<a id="schema-breachdocumentsresentout"></a>
#### `BreachDocumentsResentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kinds` | array of [`BreachDocumentKindOut`](#schema-breachdocumentkindout) | Yes | — | — |
| `board_recipients` | `integer` | Yes | — | — |
| `proofs` | array of [`BreachProofKindOut`](#schema-breachproofkindout) | Yes | — | — |
| `queued` | `integer` | Yes | — | — |

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
| `origin` | `string` or `null` | No | max length: `8000` | — |
| `discovery` | `string` or `null` | No | max length: `8000` | — |
| `affected_systems` | `string` or `null` | No | max length: `8000` | — |
| `incident_details` | `string` or `null` | No | max length: `8000` | — |
| `impact_scale` | `string` or `null` | No | max length: `8000` | — |
| `countries_involved` | `string` or `null` | No | max length: `8000` | — |
| `data_nature` | `string` or `null` | No | max length: `8000` | — |
| `subject_types` | `string` or `null` | No | max length: `8000` | — |
| `entities_involved` | `string` or `null` | No | max length: `8000` | — |
| `third_parties` | `string` or `null` | No | max length: `8000` | — |
| `cyber_attack` | `string` or `null` | No | pattern: `^(yes|no|unknown)$` | — |

<a id="schema-breachintimationout"></a>
#### `BreachIntimationOut`

Rule 7(2)(a), drafted from the register. The platform never submits it.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `reference` | `string` | Yes | — | — |
| `incident_reference` | `string` | Yes | — | — |
| `breach_reference` | `string` or `null` | Yes | — | — |
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

<a id="schema-breachlistreportout"></a>
#### `BreachListReportOut`

What a file comes to: checked (nothing written) or taken.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `rows_read` | `integer` | Yes | — | — |
| `matched_people` | `integer` | Yes | — | — |
| `new_contacts` | `integer` | Yes | — | — |
| `already_listed` | `integer` | Yes | — | — |
| `unreadable` | `integer` | Yes | — | — |
| `untraceable` | `integer` | Yes | — | — |
| `would_add` | `integer` | Yes | — | — |
| `errors` | array of [`BreachListErrorOut`](#schema-breachlisterrorout) | Yes | — | — |
| `more_errors` | `integer` | Yes | — | — |
| `upload_uuid` | `string` or `null` | No | format: `uuid` | — |

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
| `contacts` | `integer` | No | default: `0` | — |
| `unnotified` | `integer` | Yes | — | — |
| `contents` | array of [`BreachNoticeContentOut`](#schema-breachnoticecontentout) | Yes | — | — |
| `duty` | `string` | Yes | — | — |
| `send_blocked_by` | `string` or `null` | Yes | — | — |

<a id="schema-breachout"></a>
#### `BreachOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `breach_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `incident_reference` | `string` | Yes | — | — |
| `breach_reference` | `string` or `null` | Yes | — | — |
| `breach_recorded_at` | `string` or `null` | Yes | format: `date-time` | — |
| `breach_recorded_by_name` | `string` or `null` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `began_at_recorded` | `string` or `null` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `logged` | [`BreachLoggedOut`](#schema-breachloggedout) | No | — | — |
| `cyber_attack` | `string` or `null` | No | — | — |
| `reported` | [`BreachReportedOut`](#schema-breachreportedout) or `null` | No | — | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `recorded_by_name` | `string` or `null` | Yes | — | — |
| `determination` | `string` | Yes | — | — |
| `determinations` | array of [`BreachDeterminationOut`](#schema-breachdeterminationout) | Yes | — | — |
| `assessment` | [`BreachAssessmentOut`](#schema-breachassessmentout) or `null` | Yes | — | — |
| `assessment_revisions` | `integer` | Yes | — | — |
| `obligations` | array of [`BreachDutyOut`](#schema-breachdutyout) | Yes | — | — |
| `status_history` | array of [`BreachStatusChangeOut`](#schema-breachstatuschangeout) | Yes | — | — |
| `attachments` | array of [`BreachAttachmentOut`](#schema-breachattachmentout) | Yes | — | — |
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
| `incident_reference` | `string` | Yes | — | — |
| `breach_reference` | `string` or `null` | Yes | — | — |
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

<a id="schema-breachticketdatein"></a>
#### `BreachTicketDateIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `answer_by` | `string` | Yes | format: `date` | — |
| `reason` | `string` | Yes | min length: `1`; max length: `8000` | — |

<a id="schema-breachticketdetailout"></a>
#### `BreachTicketDetailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket` | [`BreachTicketOut`](#schema-breachticketout) | Yes | — | — |
| `instruction` | `string` | Yes | — | — |
| `messages` | array of [`BreachTicketMessageOut`](#schema-breachticketmessageout) | Yes | — | — |

<a id="schema-breachticketin"></a>
#### `BreachTicketIn`

Either a member of staff, by `user_uuid`, or - S3-09 - somebody named by
`email` (with `full_name`, and a `mobile` if known), who is given a
breach-only login if they have no console account.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `full_name` | `string` or `null` | No | max length: `200` | — |
| `email` | `string` or `null` | No | max length: `320` | — |
| `mobile` | `string` or `null` | No | max length: `32` | — |
| `instruction` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `answer_by` | `string` or `null` | No | format: `date` | — |

<a id="schema-breachticketreasonin"></a>
#### `BreachTicketReasonIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `1`; max length: `8000` | — |

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

<a id="schema-certinsetasidein"></a>
#### `CertInSetAsideIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `1`; max length: `8000` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-incidentdismissalin"></a>
#### `IncidentDismissalIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `1`; max length: `8000` | — |

<a id="schema-incidentreportout"></a>
#### `IncidentReportOut`

A report waiting in the shared intake, with everything it said.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `report_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `reporter_name` | `string` | Yes | — | — |
| `reporter_email` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `noticed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `cyber_attack` | `string` or `null` | Yes | — | — |
| `logged` | [`BreachLoggedOut`](#schema-breachloggedout) | Yes | — | — |

<a id="schema-incidentreportpageout"></a>
#### `IncidentReportPageOut`

A page of the shared intake, oldest first.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`IncidentReportRowOut`](#schema-incidentreportrowout) | Yes | — | — |
| `total` | `integer` | Yes | — | — |
| `limit` | `integer` | Yes | — | — |
| `offset` | `integer` | Yes | — | — |

<a id="schema-orgboardbriefout"></a>
#### `OrgBoardBriefOut`

For the organisation's board, drafted from the register: what the
report mailed to it starts from.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `document` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `reference` | `string` | Yes | — | — |
| `incident_reference` | `string` | Yes | — | — |
| `breach_reference` | `string` or `null` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `generated_at` | `string` | Yes | format: `date-time` | — |
| `detected_at` | `string` | Yes | format: `date-time` | — |
| `began_at` | `string` or `null` | Yes | format: `date-time` | — |
| `location` | [`BreachLocationOut`](#schema-breachlocationout) | Yes | — | — |
| `validation` | `string` | Yes | — | — |
| `became_aware_at` | `string` or `null` | Yes | format: `date-time` | — |
| `cert_in_reportable` | `boolean` | Yes | — | — |
| `duties` | array of [`OrgBoardDutyOut`](#schema-orgboarddutyout) | Yes | — | — |
| `affected` | [`OrgBoardAffectedOut`](#schema-orgboardaffectedout) | Yes | — | — |
| `missing` | array of `string` | Yes | — | — |
| `duty` | [`OrgBoardDutyOut`](#schema-orgboarddutyout) or `null` | Yes | — | — |

<a id="schema-breachscopein"></a>
#### `BreachScopeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `project_uuid` | `string` or `null` | No | format: `uuid` | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `source_uuid` | `string` or `null` | No | format: `uuid` | — |
| `since` | `string` or `null` | No | format: `date-time` | — |
| `until` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-breachprojectoptionout"></a>
#### `BreachProjectOptionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `is_activity` | `boolean` | Yes | — | — |
| `people` | `integer` | Yes | — | — |

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

<a id="schema-breachcontactout"></a>
#### `BreachContactOut`

Somebody affected who has no account. Name and contacts sealed.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |
| `email` | `string` or `null` | Yes | — | — |
| `mobile` | `string` or `null` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `upload_uuid` | `string` | Yes | format: `uuid` | — |
| `upload_kind` | `string` | Yes | — | — |

<a id="schema-breachuploadout"></a>
#### `BreachUploadOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `upload_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `file_name` | `string` | Yes | — | — |
| `sha256` | `string` | Yes | — | — |
| `rows_read` | `integer` | Yes | — | — |
| `matched_people` | `integer` | Yes | — | — |
| `new_contacts` | `integer` | Yes | — | — |
| `already_listed` | `integer` | Yes | — | — |
| `unreadable` | `integer` | Yes | — | — |
| `untraceable` | `integer` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachdocumentkindout"></a>
#### `BreachDocumentKindOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `duty` | `string` or `null` | Yes | — | — |
| `duty_state` | `string` or `null` | Yes | — | — |
| `blocked_by` | `string` or `null` | Yes | — | — |
| `goes_to_regulator` | `boolean` | Yes | — | — |
| `versions` | array of [`BreachDocumentOut`](#schema-breachdocumentout) | Yes | — | — |

<a id="schema-breachproofkindout"></a>
#### `BreachProofKindOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

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
| `reported_to` | `string` or `null` | Yes | — | — |
| `extended_until` | `string` or `null` | Yes | format: `date-time` | — |
| `extension_requested_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`BreachClockOut`](#schema-breachclockout) | Yes | — | — |
| `events` | array of [`BreachDutyEventOut`](#schema-breachdutyeventout) | Yes | — | — |

<a id="schema-breachlisterrorout"></a>
#### `BreachListErrorOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `row` | `integer` | Yes | — | — |
| `message` | `string` | Yes | — | — |

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
| `person_uuid` | `string` or `null` | No | format: `uuid` | — |
| `contact_uuid` | `string` or `null` | No | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachnoticecontentout"></a>
#### `BreachNoticeContentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |

<a id="schema-breachloggedout"></a>
#### `BreachLoggedOut`

What was said when it was logged (0047). Sealed; the console opens them.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `origin` | `string` or `null` | No | — | — |
| `discovery` | `string` or `null` | No | — | — |
| `affected_systems` | `string` or `null` | No | — | — |
| `incident_details` | `string` or `null` | No | — | — |
| `impact_scale` | `string` or `null` | No | — | — |
| `countries_involved` | `string` or `null` | No | — | — |
| `data_nature` | `string` or `null` | No | — | — |
| `subject_types` | `string` or `null` | No | — | — |
| `entities_involved` | `string` or `null` | No | — | — |
| `third_parties` | `string` or `null` | No | — | — |

<a id="schema-breachreportedout"></a>
#### `BreachReportedOut`

Who reported it through the public link, if somebody did (0058).

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reporter_name` | `string` | Yes | — | — |
| `reporter_email` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `noticed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `cyber_attack` | `string` or `null` | Yes | — | — |

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

<a id="schema-breachattachmentout"></a>
#### `BreachAttachmentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `attachment_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `file_name` | `string` | Yes | — | — |
| `sha256` | `string` | Yes | — | — |
| `size_bytes` | `integer` | Yes | — | — |
| `content_type` | `string` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |

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

<a id="schema-breachticketout"></a>
#### `BreachTicketOut`

A breach ticket as the office reads it.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ticket_uuid` | `string` | Yes | format: `uuid` | — |
| `holder_uuid` | `string` | Yes | format: `uuid` | — |
| `holder_name` | `string` or `null` | Yes | — | — |
| `assigned_by_name` | `string` or `null` | Yes | — | — |
| `parent_ticket_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `answer_by` | `string` or `null` | Yes | format: `date` | — |
| `overdue` | `boolean` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `unread` | `integer` | Yes | — | — |
| `last_activity_at` | `string` or `null` | Yes | format: `date-time` | — |
| `events` | array of [`BreachTicketEventOut`](#schema-breachticketeventout) | Yes | — | — |
| `moves` | array of [`BreachTicketMoveOut`](#schema-breachticketmoveout) | Yes | — | — |
| `may_write` | `boolean` | Yes | — | — |
| `may_change_date` | `boolean` | Yes | — | — |
| `temporary_access` | `string` or `null` | Yes | — | — |

<a id="schema-breachticketmessageout"></a>
#### `BreachTicketMessageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `message_uuid` | `string` | Yes | format: `uuid` | — |
| `author_side` | `string` | Yes | — | — |
| `author_name` | `string` or `null` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `body` | `string` | Yes | — | — |
| `evidence_hash` | `string` or `null` | Yes | — | — |
| `evidence_name` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-incidentreportrowout"></a>
#### `IncidentReportRowOut`

A report waiting in the shared intake, as the list shows it.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `report_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `reporter_name` | `string` | Yes | — | — |
| `reporter_email` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `noticed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `cyber_attack` | `string` or `null` | Yes | — | — |

<a id="schema-orgboarddutyout"></a>
#### `OrgBoardDutyOut`

A duty as the brief carries it: its clock, and nobody's name.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `duty` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `basis` | `string` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `anchored_at` | `string` or `null` | Yes | format: `date-time` | — |
| `completed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`BreachClockOut`](#schema-breachclockout) | Yes | — | — |

<a id="schema-orgboardaffectedout"></a>
#### `OrgBoardAffectedOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `listed` | `integer` | Yes | — | — |
| `notified` | `integer` | Yes | — | — |

<a id="schema-breachevidenceout"></a>
#### `BreachEvidenceOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `projects` | array of `string` | No | — | — |
| `exports` | array of `string` | No | — | — |
| `assets` | array of `string` | No | — | — |
| `activities` | array of `string` | No | — | — |
| `tables` | array of `string` | No | — | — |

<a id="schema-breachdocumentout"></a>
#### `BreachDocumentOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `report_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `title` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `sections` | array of [`BreachDocumentSectionOut`](#schema-breachdocumentsectionout) | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `created_by_name` | `string` or `null` | Yes | — | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `finalised_at` | `string` or `null` | Yes | format: `date-time` | — |
| `finalised_by_name` | `string` or `null` | Yes | — | — |
| `filed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `filed_reference` | `string` or `null` | Yes | — | — |
| `filed_by_name` | `string` or `null` | Yes | — | — |
| `evidence` | array of [`BreachDocumentProofOut`](#schema-breachdocumentproofout) | Yes | — | — |
| `mail` | [`BreachDocumentMailOut`](#schema-breachdocumentmailout) | Yes | — | — |

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
| `reported_to` | `string` or `null` | Yes | — | — |
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

<a id="schema-breachticketeventout"></a>
#### `BreachTicketEventOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `event_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `summary` | `string` or `null` | Yes | — | — |
| `reason` | `string` or `null` | Yes | — | — |
| `date_before` | `string` or `null` | No | format: `date` | — |
| `date_after` | `string` or `null` | No | format: `date` | — |
| `occurred_at` | `string` | Yes | format: `date-time` | — |
| `actor_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachticketmoveout"></a>
#### `BreachTicketMoveOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `move` | `string` | Yes | — | — |
| `reason_required` | `boolean` | Yes | — | — |

<a id="schema-breachdocumentsectionout"></a>
#### `BreachDocumentSectionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `key` | `string` | Yes | — | — |
| `label` | `string` | Yes | — | — |
| `required` | `boolean` | Yes | — | — |
| `body` | `string` or `null` | Yes | — | — |

<a id="schema-breachdocumentproofout"></a>
#### `BreachDocumentProofOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `attachment_uuid` | `string` | Yes | format: `uuid` | — |
| `kind` | `string` | Yes | — | — |
| `note` | `string` or `null` | Yes | — | — |
| `file_name` | `string` | Yes | — | — |
| `sha256` | `string` | Yes | — | — |
| `size_bytes` | `integer` | Yes | — | — |
| `added_at` | `string` | Yes | format: `date-time` | — |
| `added_by_name` | `string` or `null` | Yes | — | — |

<a id="schema-breachdocumentmailout"></a>
#### `BreachDocumentMailOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `delivered` | `integer` | Yes | — | — |
| `queued` | `integer` | Yes | — | — |
| `failed` | `integer` | Yes | — | — |
| `stale` | `integer` | Yes | — | — |
| `retryable` | `integer` | Yes | — | — |
| `recipients` | array of [`BreachDocumentMailRecipientOut`](#schema-breachdocumentmailrecipientout) | Yes | — | — |

<a id="schema-breachchannelcountout"></a>
#### `BreachChannelCountOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `channel` | `string` | Yes | — | — |
| `delivered` | `integer` | Yes | — | — |
| `queued` | `integer` | Yes | — | — |
| `failed` | `integer` | Yes | — | — |

<a id="schema-breachdocumentmailrecipientout"></a>
#### `BreachDocumentMailRecipientOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `recipient_uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` or `null` | Yes | — | — |
| `email` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `attempt` | `integer` | Yes | — | — |
| `error` | `string` or `null` | Yes | — | — |
| `recorded_at` | `string` | Yes | format: `date-time` | — |
| `removed` | `boolean` | Yes | — | — |
