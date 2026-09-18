# Rights API

Generated from `cmp_backend/openapi.json`. **43 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /requests/attention`](#1_get_requests_attention)
2. [`GET /requests`](#2_get_requests)
3. [`POST /requests`](#3_post_requests)
4. [`GET /requests/{request_uuid}`](#4_get_requests_request_uuid)
5. [`GET /requests/{request_uuid}/linked/trail`](#5_get_requests_request_uuid_linked_trail)
6. [`GET /requests/{request_uuid}/transitions`](#6_get_requests_request_uuid_transitions)
7. [`GET /requests/{request_uuid}/trail`](#7_get_requests_request_uuid_trail)
8. [`POST /requests/{request_uuid}/acknowledge`](#8_post_requests_request_uuid_acknowledge)
9. [`POST /requests/{request_uuid}/verification/code`](#9_post_requests_request_uuid_verification_code)
10. [`POST /requests/{request_uuid}/verification/confirm`](#10_post_requests_request_uuid_verification_confirm)
11. [`POST /requests/{request_uuid}/verification/manual`](#11_post_requests_request_uuid_verification_manual)
12. [`POST /requests/{request_uuid}/verification/fail`](#12_post_requests_request_uuid_verification_fail)
13. [`POST /requests/{request_uuid}/classify`](#13_post_requests_request_uuid_classify)
14. [`POST /requests/{request_uuid}/refuse`](#14_post_requests_request_uuid_refuse)
15. [`POST /requests/{request_uuid}/withdrawal`](#15_post_requests_request_uuid_withdrawal)
16. [`POST /requests/{request_uuid}/intent`](#16_post_requests_request_uuid_intent)
17. [`POST /requests/{request_uuid}/event`](#17_post_requests_request_uuid_event)
18. [`GET /requests/{request_uuid}/event/evidence`](#18_get_requests_request_uuid_event_evidence)
19. [`POST /requests/{request_uuid}/escalate`](#19_post_requests_request_uuid_escalate)
20. [`POST /requests/{request_uuid}/reviewer`](#20_post_requests_request_uuid_reviewer)
21. [`POST /requests/{request_uuid}/transition`](#21_post_requests_request_uuid_transition)
22. [`POST /requests/{request_uuid}/holders/derive`](#22_post_requests_request_uuid_holders_derive)
23. [`POST /requests/{request_uuid}/holders`](#23_post_requests_request_uuid_holders)
24. [`POST /requests/{request_uuid}/holders/{holder_uuid}/confirm`](#24_post_requests_request_uuid_holders_holder_uuid_confirm)
25. [`GET /requests/{request_uuid}/holders/{holder_uuid}/thread`](#25_get_requests_request_uuid_holders_holder_uuid_thread)
26. [`POST /requests/{request_uuid}/holders/{holder_uuid}/thread`](#26_post_requests_request_uuid_holders_holder_uuid_thread)
27. [`POST /requests/{request_uuid}/holders/{holder_uuid}/send-back`](#27_post_requests_request_uuid_holders_holder_uuid_send_back)
28. [`POST /requests/{request_uuid}/holders/{holder_uuid}/withdraw`](#28_post_requests_request_uuid_holders_holder_uuid_withdraw)
29. [`POST /requests/{request_uuid}/holders/{holder_uuid}/reassign`](#29_post_requests_request_uuid_holders_holder_uuid_reassign)
30. [`POST /requests/{request_uuid}/holders/{holder_uuid}/remind`](#30_post_requests_request_uuid_holders_holder_uuid_remind)
31. [`GET /requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence`](#31_get_requests_request_uuid_holders_holder_uuid_messages_message_uuid_evidence)
32. [`POST /requests/{request_uuid}/holders/{holder_uuid}/contact`](#32_post_requests_request_uuid_holders_holder_uuid_contact)
33. [`POST /requests/{request_uuid}/tickets`](#33_post_requests_request_uuid_tickets)
34. [`POST /requests/{request_uuid}/holders/{holder_uuid}/return`](#34_post_requests_request_uuid_holders_holder_uuid_return)
35. [`GET /requests/{request_uuid}/holders/{holder_uuid}/evidence`](#35_get_requests_request_uuid_holders_holder_uuid_evidence)
36. [`POST /requests/{request_uuid}/holders/{holder_uuid}/escalate`](#36_post_requests_request_uuid_holders_holder_uuid_escalate)
37. [`POST /requests/{request_uuid}/scope/derive`](#37_post_requests_request_uuid_scope_derive)
38. [`PUT /requests/{request_uuid}/scope/{item_uuid}`](#38_put_requests_request_uuid_scope_item_uuid)
39. [`POST /requests/{request_uuid}/scope/{item_uuid}/apply`](#39_post_requests_request_uuid_scope_item_uuid_apply)
40. [`POST /requests/{request_uuid}/respond`](#40_post_requests_request_uuid_respond)
41. [`GET /requests/{request_uuid}/files/{file_uuid}`](#41_get_requests_request_uuid_files_file_uuid)
42. [`POST /requests/{request_uuid}/decide`](#42_post_requests_request_uuid_decide)
43. [`GET /requests/{request_uuid}/download`](#43_get_requests_request_uuid_download)

<a id="1_get_requests_attention"></a>
## 1. `GET /requests/attention` — What the office has not read

### API

- **Operation ID:** `requests_attention_requests_attention_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

The number on the office's bell: every open ticket whose team has
written - a message, a return - and nobody in the office has opened yet.
The respondent's side has the same count on "Tickets for you"; without
this one the conversation rang on one end only.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`AttentionOut`](#schema-attentionout) |

**Example `200` `application/json` response:**

```json
{
  "threads_unread": 1
}
```

<a id="2_get_requests"></a>
## 2. `GET /requests` — Every request in scope

### API

- **Operation ID:** `list_requests_requests_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

The register. Soonest due is the sort that matters; newest first is the default.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `type` | query | No | `string` or `null` | — | — |
| `status` | query | No | `string` or `null` | — | — |
| `overdue` | query | No | `boolean` | default: `False` | — |
| `q` | query | No | `string` or `null` | max length: `120` | — |
| `unread` | query | No | `boolean` | default: `False` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_RequestRow_`](#schema-page_requestrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "request_uuid": "00000000-0000-4000-8000-000000000000",
      "reference": "string",
      "request_type": "string",
      "original_type": "…",
      "status": "string",
      "outcome": "…",
      "channel": "string",
      "subject_uuid": "…",
      "subject_name": "…",
      "submitted_name": "…",
      "submitted_contact": "string",
      "received_at": "2026-09-17T12:00:00Z",
      "due_at": "2026-09-17T12:00:00Z",
      "acknowledged_at": "…",
      "verification_status": "string",
      "about_dpo": true,
      "linked_reference": "…",
      "consent_uuid": "…",
      "consent_project": "…",
      "threads_unread": 0,
      "holder_count": 1,
      "tickets_outstanding": 1,
      "closed_at": "…",
      "clock": "…"
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

<a id="3_post_requests"></a>
## 3. `POST /requests` — Log a request received by email

### API

- **Operation ID:** `log_request_requests_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

Email to the DPO makes the same record as the dashboard and the notice link.

Verification stays pending: the DPO records how identity was established
as a separate act, with a reason, so the record says *how* rather than
only that somebody was satisfied.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`LogRequest`](#schema-logrequest)

```json
{
  "request_type": "string",
  "contact": "string",
  "name": "string",
  "request_text": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "about_dpo": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="4_get_requests_request_uuid"></a>
## 4. `GET /requests/{request_uuid}` — Get Request

### API

- **Operation ID:** `get_request_requests__request_uuid__get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestDetail`](#schema-requestdetail) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1,
  "holders": [
    {
      "holder_uuid": "00000000-0000-4000-8000-000000000000",
      "label": "string",
      "derived_from": "string",
      "evidence": {},
      "processor_uuid": "…",
      "processor_name": "…",
      "is_in_house": "…",
      "confirmed_at": "…",
      "confirmed_by_name": "…",
      "ticket_status": "string",
      "instruction": "…",
      "responder_name": "…",
      "responder_contact": "…",
      "issued_at": "…",
      "due_at": "…",
      "escalated_at": "…",
      "returned_at": "…",
      "return_summary": "…",
      "return_evidence_hash": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "channel": "email",
      "respondent_uuid": "…",
      "responder_user_uuid": "…",
      "responder_user_name": "…",
      "contact_log": [
        "…"
      ],
      "brief": "…",
      "message_count": 0,
      "unread_for_office": 0,
      "seen_at": "…",
      "last_reminded_at": "…",
      "reminders_sent": 0,
      "return_evidence_name": "…",
      "sent_back_at": "…",
      "sent_back_reason": "…",
      "sent_back_count": 0
    }
  ],
  "items": [
    {
      "item_uuid": "00000000-0000-4000-8000-000000000000",
      "other_subjects": 1,
      "state": "string",
      "decision": "…",
      "basis": "…",
      "retain_until": "…",
      "floor_passed_at": "…",
      "decided_at": "…",
      "decided_by_name": "…",
      "applied_at": "…",
      "disposition": "…",
      "disposition_at": "…",
      "subject_role": "string",
      "asset_uuid": "00000000-0000-4000-8000-000000000000",
      "asset_type": "string",
      "source_asset_ref": "string",
      "source_code": "string",
      "source_name": "string",
      "processor_name": "…",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "collected_on": "2026-09-17",
      "holder_uuid": "…",
      "holder_label": "…",
      "holder_ticket_status": "…"
    }
  ],
  "transitions": [
    {}
  ],
  "linked_request": {
    "request_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "request_type": "string",
    "status": "string",
    "outcome": "…",
    "received_at": "2026-09-17T12:00:00Z",
    "closed_at": "…",
    "channel": "string",
    "request_text": "string",
    "due_at": "2026-09-17T12:00:00Z",
    "verification_method": "…",
    "verified_at": "…",
    "responded_at": "…",
    "response_text": "…",
    "refusal_reason": "…",
    "remedy_text": "…",
    "response_file_hash": "…",
    "holder_count": 1,
    "tickets_issued": 1,
    "tickets_returned": 1,
    "clock": "…",
    "in_scope": true
  },
  "linked_from": [
    {
      "request_uuid": "00000000-0000-4000-8000-000000000000",
      "reference": "string",
      "request_type": "string",
      "status": "string",
      "outcome": "…",
      "received_at": "2026-09-17T12:00:00Z",
      "closed_at": "…"
    }
  ],
  "response_files": [
    {
      "file_uuid": "00000000-0000-4000-8000-000000000000",
      "file_name": "string",
      "file_hash": "string",
      "size_bytes": 1,
      "content_type": "…",
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

<a id="5_get_requests_request_uuid_linked_trail"></a>
## 5. `GET /requests/{request_uuid}/linked/trail` — Everything recorded about the request this one is about

### API

- **Operation ID:** `get_linked_trail_requests__request_uuid__linked_trail_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

Reached through the grievance, not the original: whoever may decide a
grievance may read the trail of what it disputes, even when the original
sits outside their scope - a reviewer named because the complaint is about
the DPO has to see how the DPO handled it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="6_get_requests_request_uuid_transitions"></a>
## 6. `GET /requests/{request_uuid}/transitions` — Get Transitions

### API

- **Operation ID:** `get_transitions_requests__request_uuid__transitions_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

What may happen next for this role, and why anything else is blocked.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`cmp__api__routers__v1__rights__TransitionsOut`](#schema-cmp_api_routers_v1_rights_transitionsout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "current": "string",
  "available": [
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

<a id="7_get_requests_request_uuid_trail"></a>
## 7. `GET /requests/{request_uuid}/trail` — Everything recorded about this request

### API

- **Operation ID:** `get_trail_requests__request_uuid__trail_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="8_post_requests_request_uuid_acknowledge"></a>
## 8. `POST /requests/{request_uuid}/acknowledge` — Send (or re-send) the acknowledgement

### API

- **Operation ID:** `acknowledge_requests__request_uuid__acknowledge_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="9_post_requests_request_uuid_verification_code"></a>
## 9. `POST /requests/{request_uuid}/verification/code` — Send a code to the stored channel

### API

- **Operation ID:** `send_code_requests__request_uuid__verification_code_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="10_post_requests_request_uuid_verification_confirm"></a>
## 10. `POST /requests/{request_uuid}/verification/confirm` — Enter the code she read back

### API

- **Operation ID:** `confirm_code_requests__request_uuid__verification_confirm_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`CodeIn`](#schema-codein)

```json
{
  "code": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="11_post_requests_request_uuid_verification_manual"></a>
## 11. `POST /requests/{request_uuid}/verification/manual` — Verified by hand, with the reason recorded

### API

- **Operation ID:** `verify_manually_requests__request_uuid__verification_manual_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ManualVerifyIn`](#schema-manualverifyin)

```json
{
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="12_post_requests_request_uuid_verification_fail"></a>
## 12. `POST /requests/{request_uuid}/verification/fail` — No match, or verification not satisfied

### API

- **Operation ID:** `fail_verification_requests__request_uuid__verification_fail_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NoteIn`](#schema-notein)

```json
{
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="13_post_requests_request_uuid_classify"></a>
## 13. `POST /requests/{request_uuid}/classify` — Confirm, or reclassify, what this is

### API

- **Operation ID:** `classify_requests__request_uuid__classify_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ClassifyIn`](#schema-classifyin)

```json
{
  "request_type": "string",
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="14_post_requests_request_uuid_refuse"></a>
## 14. `POST /requests/{request_uuid}/refuse` — Not a rights request, or refused - with reasons

### API

- **Operation ID:** `refuse_requests__request_uuid__refuse_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`RefuseIn`](#schema-refusein)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="15_post_requests_request_uuid_withdrawal"></a>
## 15. `POST /requests/{request_uuid}/withdrawal` — She meant withdrawal, not erasure

### API

- **Operation ID:** `as_withdrawal_requests__request_uuid__withdrawal_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NoteIn`](#schema-notein)

```json
{
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="16_post_requests_request_uuid_intent"></a>
## 16. `POST /requests/{request_uuid}/intent` — She means erasure - confirmed

### API

- **Operation ID:** `confirm_intent_requests__request_uuid__intent_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="17_post_requests_request_uuid_event"></a>
## 17. `POST /requests/{request_uuid}/event` — Is the triggering event evidenced?

### API

- **Operation ID:** `event_evidence_requests__request_uuid__event_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`EvidenceIn`](#schema-evidencein)

```json
{
  "evidenced": true,
  "note": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="18_get_requests_request_uuid_event_evidence"></a>
## 18. `GET /requests/{request_uuid}/event/evidence` — Download the triggering-event evidence

### API

- **Operation ID:** `event_evidence_file_requests__request_uuid__event_evidence_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="19_post_requests_request_uuid_escalate"></a>
## 19. `POST /requests/{request_uuid}/escalate` — The complaint is about the DPO

### API

- **Operation ID:** `escalate_requests__request_uuid__escalate_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="20_post_requests_request_uuid_reviewer"></a>
## 20. `POST /requests/{request_uuid}/reviewer` — Name the independent reviewer

### API

- **Operation ID:** `assign_reviewer_requests__request_uuid__reviewer_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ReviewerIn`](#schema-reviewerin)

```json
{
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="21_post_requests_request_uuid_transition"></a>
## 21. `POST /requests/{request_uuid}/transition` — Transition

### API

- **Operation ID:** `transition_requests__request_uuid__transition_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TransitionIn`](#schema-transitionin)

```json
{
  "to": "string",
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="22_post_requests_request_uuid_holders_derive"></a>
## 22. `POST /requests/{request_uuid}/holders/derive` — Holders derived from export_line and asset_consent

### API

- **Operation ID:** `derive_holders_requests__request_uuid__holders_derive_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "label": "string",
    "derived_from": "string",
    "evidence": {},
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "is_in_house": true,
    "confirmed_at": "2026-09-17T12:00:00Z",
    "confirmed_by_name": "string",
    "ticket_status": "string",
    "instruction": "string",
    "responder_name": "string",
    "responder_contact": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_evidence_hash": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "channel": "email",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_name": "string",
    "contact_log": [
      {}
    ],
    "brief": {},
    "message_count": 0,
    "unread_for_office": 0,
    "seen_at": "2026-09-17T12:00:00Z",
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0
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

<a id="23_post_requests_request_uuid_holders"></a>
## 23. `POST /requests/{request_uuid}/holders` — A holder the records missed

### API

- **Operation ID:** `add_holder_requests__request_uuid__holders_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`HolderIn`](#schema-holderin)

```json
{
  "label": "string",
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_name": "string",
  "responder_contact": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="24_post_requests_request_uuid_holders_holder_uuid_confirm"></a>
## 24. `POST /requests/{request_uuid}/holders/{holder_uuid}/confirm` — Confirm Holder

### API

- **Operation ID:** `confirm_holder_requests__request_uuid__holders__holder_uuid__confirm_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ConfirmHolderIn`](#schema-confirmholderin)

```json
{
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_name": "string",
  "responder_contact": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="25_get_requests_request_uuid_holders_holder_uuid_thread"></a>
## 25. `GET /requests/{request_uuid}/holders/{holder_uuid}/thread` — The ticket's thread, as the office reads it

### API

- **Operation ID:** `holder_thread_requests__request_uuid__holders__holder_uuid__thread_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ThreadOut`](#schema-threadout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder": {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "label": "string",
    "derived_from": "string",
    "evidence": {},
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "is_in_house": true,
    "confirmed_at": "2026-09-17T12:00:00Z",
    "confirmed_by_name": "string",
    "ticket_status": "string",
    "instruction": "string",
    "responder_name": "string",
    "responder_contact": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_evidence_hash": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "channel": "email",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_name": "string",
    "contact_log": [
      {}
    ],
    "brief": {},
    "message_count": 0,
    "unread_for_office": 0,
    "seen_at": "2026-09-17T12:00:00Z",
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0
  },
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

<a id="26_post_requests_request_uuid_holders_holder_uuid_thread"></a>
## 26. `POST /requests/{request_uuid}/holders/{holder_uuid}/thread` — Write to the holder on the ticket, with a file if it helps

### API

- **Operation ID:** `post_to_holder_requests__request_uuid__holders__holder_uuid__thread_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

Kept on the thread, and the holder is told the way it is reached: on the
portal with a copy by mail, or by mail alone.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_post_to_holder_requests__request_uuid__holders__holder_uuid__thread_post`](#schema-body_post_to_holder_requests_request_uuid_holders_holder_uuid_thread_post)

```json
{
  "body": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ThreadOut`](#schema-threadout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder": {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "label": "string",
    "derived_from": "string",
    "evidence": {},
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "is_in_house": true,
    "confirmed_at": "2026-09-17T12:00:00Z",
    "confirmed_by_name": "string",
    "ticket_status": "string",
    "instruction": "string",
    "responder_name": "string",
    "responder_contact": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_evidence_hash": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "channel": "email",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_name": "string",
    "contact_log": [
      {}
    ],
    "brief": {},
    "message_count": 0,
    "unread_for_office": 0,
    "seen_at": "2026-09-17T12:00:00Z",
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0
  },
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

<a id="27_post_requests_request_uuid_holders_holder_uuid_send_back"></a>
## 27. `POST /requests/{request_uuid}/holders/{holder_uuid}/send-back` — Send a returned ticket back to its holder

### API

- **Operation ID:** `send_back_ticket_requests__request_uuid__holders__holder_uuid__send_back_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

Not satisfied with the return: the ticket is open again with the
reason and a date, the holder is told, and the request waits again.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SendBackIn`](#schema-sendbackin)

```json
{
  "reason": "string",
  "due_at": "2026-09-17T12:00:00Z"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="28_post_requests_request_uuid_holders_holder_uuid_withdraw"></a>
## 28. `POST /requests/{request_uuid}/holders/{holder_uuid}/withdraw` — Withdraw a ticket issued in error

### API

- **Operation ID:** `withdraw_ticket_requests__request_uuid__holders__holder_uuid__withdraw_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`WithdrawIn`](#schema-withdrawin)

```json
{
  "reason": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="29_post_requests_request_uuid_holders_holder_uuid_reassign"></a>
## 29. `POST /requests/{request_uuid}/holders/{holder_uuid}/reassign` — Send an open ticket to a different respondent

### API

- **Operation ID:** `reassign_holder_requests__request_uuid__holders__holder_uuid__reassign_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ReassignIn`](#schema-reassignin)

```json
{
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_name": "string",
  "responder_contact": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="30_post_requests_request_uuid_holders_holder_uuid_remind"></a>
## 30. `POST /requests/{request_uuid}/holders/{holder_uuid}/remind` — Send the respondent a reminder now

### API

- **Operation ID:** `remind_holder_requests__request_uuid__holders__holder_uuid__remind_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="31_get_requests_request_uuid_holders_holder_uuid_messages_message_uuid_evidence"></a>
## 31. `GET /requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence` — Download a file attached to a message on the ticket

### API

- **Operation ID:** `holder_message_attachment_requests__request_uuid__holders__holder_uuid__messages__message_uuid__evidence_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |
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

<a id="32_post_requests_request_uuid_holders_holder_uuid_contact"></a>
## 32. `POST /requests/{request_uuid}/holders/{holder_uuid}/contact` — Record a mail sent, a chase, or a reply - and optionally send the mail

### API

- **Operation ID:** `log_contact_requests__request_uuid__holders__holder_uuid__contact_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

The trail for a holder reached by email, kept on the request rather than
in one person's inbox.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ContactIn`](#schema-contactin)

```json
{
  "kind": "note",
  "note": "string",
  "send": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="33_post_requests_request_uuid_tickets"></a>
## 33. `POST /requests/{request_uuid}/tickets` — Issue a ticket to every confirmed holder

### API

- **Operation ID:** `issue_tickets_requests__request_uuid__tickets_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`IssueTicketsIn`](#schema-issueticketsin)

```json
{
  "instruction": "string",
  "due_at": "2026-09-17T12:00:00Z"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "label": "string",
    "derived_from": "string",
    "evidence": {},
    "processor_uuid": "00000000-0000-4000-8000-000000000000",
    "processor_name": "string",
    "is_in_house": true,
    "confirmed_at": "2026-09-17T12:00:00Z",
    "confirmed_by_name": "string",
    "ticket_status": "string",
    "instruction": "string",
    "responder_name": "string",
    "responder_contact": "string",
    "issued_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "escalated_at": "2026-09-17T12:00:00Z",
    "returned_at": "2026-09-17T12:00:00Z",
    "return_summary": "string",
    "return_evidence_hash": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "channel": "email",
    "respondent_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
    "responder_user_name": "string",
    "contact_log": [
      {}
    ],
    "brief": {},
    "message_count": 0,
    "unread_for_office": 0,
    "seen_at": "2026-09-17T12:00:00Z",
    "last_reminded_at": "2026-09-17T12:00:00Z",
    "reminders_sent": 0,
    "return_evidence_name": "string",
    "sent_back_at": "2026-09-17T12:00:00Z",
    "sent_back_reason": "string",
    "sent_back_count": 0
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

<a id="34_post_requests_request_uuid_holders_holder_uuid_return"></a>
## 34. `POST /requests/{request_uuid}/holders/{holder_uuid}/return` — Record what the holder returned

### API

- **Operation ID:** `return_ticket_requests__request_uuid__holders__holder_uuid__return_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_return_ticket_requests__request_uuid__holders__holder_uuid__return_post`](#schema-body_return_ticket_requests_request_uuid_holders_holder_uuid_return_post)

```json
{
  "summary": "string",
  "evidence": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="35_get_requests_request_uuid_holders_holder_uuid_evidence"></a>
## 35. `GET /requests/{request_uuid}/holders/{holder_uuid}/evidence` — Download a holder's return evidence

### API

- **Operation ID:** `holder_evidence_requests__request_uuid__holders__holder_uuid__evidence_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="36_post_requests_request_uuid_holders_holder_uuid_escalate"></a>
## 36. `POST /requests/{request_uuid}/holders/{holder_uuid}/escalate` — A holder missed its date - escalate once

### API

- **Operation ID:** `escalate_ticket_requests__request_uuid__holders__holder_uuid__escalate_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `holder_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`HolderOut`](#schema-holderout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "label": "string",
  "derived_from": "string",
  "evidence": {},
  "processor_uuid": "00000000-0000-4000-8000-000000000000",
  "processor_name": "string",
  "is_in_house": true,
  "confirmed_at": "2026-09-17T12:00:00Z",
  "confirmed_by_name": "string",
  "ticket_status": "string",
  "instruction": "string",
  "responder_name": "string",
  "responder_contact": "string",
  "issued_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "escalated_at": "2026-09-17T12:00:00Z",
  "returned_at": "2026-09-17T12:00:00Z",
  "return_summary": "string",
  "return_evidence_hash": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "channel": "email",
  "respondent_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_uuid": "00000000-0000-4000-8000-000000000000",
  "responder_user_name": "string",
  "contact_log": [
    {}
  ],
  "brief": {},
  "message_count": 0,
  "unread_for_office": 0,
  "seen_at": "2026-09-17T12:00:00Z",
  "last_reminded_at": "2026-09-17T12:00:00Z",
  "reminders_sent": 0,
  "return_evidence_name": "string",
  "sent_back_at": "2026-09-17T12:00:00Z",
  "sent_back_reason": "string",
  "sent_back_count": 0
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

<a id="37_post_requests_request_uuid_scope_derive"></a>
## 37. `POST /requests/{request_uuid}/scope/derive` — Every appearance of her in a collected asset

### API

- **Operation ID:** `derive_scope_requests__request_uuid__scope_derive_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ItemOut`](#schema-itemout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "item_uuid": "00000000-0000-4000-8000-000000000000",
    "other_subjects": 1,
    "state": "string",
    "decision": "string",
    "basis": "string",
    "retain_until": "2026-09-17",
    "floor_passed_at": "2026-09-17T12:00:00Z",
    "decided_at": "2026-09-17T12:00:00Z",
    "decided_by_name": "string",
    "applied_at": "2026-09-17T12:00:00Z",
    "disposition": "string",
    "disposition_at": "2026-09-17T12:00:00Z",
    "subject_role": "string",
    "asset_uuid": "00000000-0000-4000-8000-000000000000",
    "asset_type": "string",
    "source_asset_ref": "string",
    "source_code": "string",
    "source_name": "string",
    "processor_name": "string",
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string",
    "collected_on": "2026-09-17",
    "holder_uuid": "00000000-0000-4000-8000-000000000000",
    "holder_label": "string",
    "holder_ticket_status": "string"
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

<a id="38_put_requests_request_uuid_scope_item_uuid"></a>
## 38. `PUT /requests/{request_uuid}/scope/{item_uuid}` — What can go, what must stay, and why

### API

- **Operation ID:** `decide_item_requests__request_uuid__scope__item_uuid__put`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `item_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`DecideIn`](#schema-decidein)

```json
{
  "decision": "string",
  "basis": "string",
  "retain_until": "2026-09-17",
  "holder_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ItemOut`](#schema-itemout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "item_uuid": "00000000-0000-4000-8000-000000000000",
  "other_subjects": 1,
  "state": "string",
  "decision": "string",
  "basis": "string",
  "retain_until": "2026-09-17",
  "floor_passed_at": "2026-09-17T12:00:00Z",
  "decided_at": "2026-09-17T12:00:00Z",
  "decided_by_name": "string",
  "applied_at": "2026-09-17T12:00:00Z",
  "disposition": "string",
  "disposition_at": "2026-09-17T12:00:00Z",
  "subject_role": "string",
  "asset_uuid": "00000000-0000-4000-8000-000000000000",
  "asset_type": "string",
  "source_asset_ref": "string",
  "source_code": "string",
  "source_name": "string",
  "processor_name": "string",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "collected_on": "2026-09-17",
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "holder_label": "string",
  "holder_ticket_status": "string"
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

<a id="39_post_requests_request_uuid_scope_item_uuid_apply"></a>
## 39. `POST /requests/{request_uuid}/scope/{item_uuid}/apply` — Set her junction row - the asset survives

### API

- **Operation ID:** `apply_item_requests__request_uuid__scope__item_uuid__apply_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `item_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ItemOut`](#schema-itemout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "item_uuid": "00000000-0000-4000-8000-000000000000",
  "other_subjects": 1,
  "state": "string",
  "decision": "string",
  "basis": "string",
  "retain_until": "2026-09-17",
  "floor_passed_at": "2026-09-17T12:00:00Z",
  "decided_at": "2026-09-17T12:00:00Z",
  "decided_by_name": "string",
  "applied_at": "2026-09-17T12:00:00Z",
  "disposition": "string",
  "disposition_at": "2026-09-17T12:00:00Z",
  "subject_role": "string",
  "asset_uuid": "00000000-0000-4000-8000-000000000000",
  "asset_type": "string",
  "source_asset_ref": "string",
  "source_code": "string",
  "source_name": "string",
  "processor_name": "string",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "collected_on": "2026-09-17",
  "holder_uuid": "00000000-0000-4000-8000-000000000000",
  "holder_label": "string",
  "holder_ticket_status": "string"
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

<a id="40_post_requests_request_uuid_respond"></a>
## 40. `POST /requests/{request_uuid}/respond` — Release and close

### API

- **Operation ID:** `respond_requests__request_uuid__respond_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

Multipart: the outcome and the words, plus any files released with
them - an extract a holder returned, a corrected document, a letter.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_respond_requests__request_uuid__respond_post`](#schema-body_respond_requests_request_uuid_respond_post)

```json
{
  "outcome": "string",
  "response_text": "string",
  "files": []
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`RequestOut`](#schema-requestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "original_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "submitted_name": "string",
  "submitted_contact": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "about_dpo": true,
  "linked_reference": "string",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "threads_unread": 0,
  "holder_count": 1,
  "tickets_outstanding": 1,
  "closed_at": "2026-09-17T12:00:00Z",
  "clock": {
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledge_by": "2026-09-17T12:00:00Z",
    "tickets_by": "2026-09-17T12:00:00Z",
    "halfway_at": "2026-09-17T12:00:00Z",
    "collate_by": "2026-09-17T12:00:00Z",
    "days_remaining": 1,
    "overdue": true,
    "at_risk": true,
    "progress": 1.0,
    "checkpoints": [
      {}
    ],
    "next_checkpoint": "string"
  },
  "request_text": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "verification_method": "string",
  "verified_at": "2026-09-17T12:00:00Z",
  "verified_by_name": "string",
  "verification_note": "string",
  "classified_at": "2026-09-17T12:00:00Z",
  "refusal_reason": "string",
  "intent_confirmed_at": "2026-09-17T12:00:00Z",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "linked_request_type": "string",
  "consent_project_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_withdrawn": true,
  "consent_purposes": [
    "string"
  ],
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_contact": "string",
  "trigger_event": "string",
  "trigger_evidence_hash": "string",
  "trigger_evidenced_at": "2026-09-17T12:00:00Z",
  "reviewer_uuid": "00000000-0000-4000-8000-000000000000",
  "reviewer_name": "string",
  "escalated_at": "2026-09-17T12:00:00Z",
  "grievance_upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "response_file_hash": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "download_expires_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z",
  "holders_confirmed": 1,
  "tickets_issued": 1,
  "tickets_returned": 1,
  "item_count": 1,
  "items_undecided": 1
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

<a id="41_get_requests_request_uuid_files_file_uuid"></a>
## 41. `GET /requests/{request_uuid}/files/{file_uuid}` — A file released with the response

### API

- **Operation ID:** `download_response_file_requests__request_uuid__files__file_uuid__get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |
| `file_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="42_post_requests_request_uuid_decide"></a>
## 42. `POST /requests/{request_uuid}/decide` — Decide a grievance

### API

- **Operation ID:** `decide_grievance_requests__request_uuid__decide_post`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`GrievanceDecisionIn`](#schema-grievancedecisionin)

```json
{
  "upheld": true,
  "remedy_text": "string",
  "response_text": "string",
  "rerun": false
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

<a id="43_get_requests_request_uuid_download"></a>
## 43. `GET /requests/{request_uuid}/download` — The released response file

### API

- **Operation ID:** `download_response_requests__request_uuid__download_get`
- **Access:** Role-controlled `rights` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

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

# Referenced schemas

<a id="schema-attentionout"></a>
#### `AttentionOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `threads_unread` | `integer` | Yes | — | — |

<a id="schema-body_post_to_holder_requests_request_uuid_holders_holder_uuid_thread_post"></a>
#### `Body_post_to_holder_requests__request_uuid__holders__holder_uuid__thread_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `body` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional file, max 25 MB |

<a id="schema-body_respond_requests_request_uuid_respond_post"></a>
#### `Body_respond_requests__request_uuid__respond_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `outcome` | `string` | Yes | — | — |
| `response_text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `files` | array of `string` | No | default: `[]` | — |

<a id="schema-body_return_ticket_requests_request_uuid_holders_holder_uuid_return_post"></a>
#### `Body_return_ticket_requests__request_uuid__holders__holder_uuid__return_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `summary` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `evidence` | `string` or `null` | No | — | Optional evidence, max 25 MB |

<a id="schema-classifyin"></a>
#### `ClassifyIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_type` | `string` | Yes | — | — |
| `note` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-codein"></a>
#### `CodeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-confirmholderin"></a>
#### `ConfirmHolderIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `respondent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `responder_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `responder_contact` | `string` or `null` | No | min length: `3`; max length: `255` | — |

<a id="schema-contactin"></a>
#### `ContactIn`

One line on a holder's contact log, optionally sending the mail too.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `kind` | `string` | No | default: `note` | — |
| `note` | `string` or `null` | No | max length: `2000` | — |
| `send` | `boolean` | No | default: `False` | — |

<a id="schema-decidein"></a>
#### `DecideIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `decision` | `string` | Yes | — | — |
| `basis` | `string` | Yes | min length: `3`; max length: `5000` | — |
| `retain_until` | `string` or `null` | No | format: `date` | — |
| `holder_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-evidencein"></a>
#### `EvidenceIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `evidenced` | `boolean` | Yes | — | — |
| `note` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-grievancedecisionin"></a>
#### `GrievanceDecisionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `upheld` | `boolean` | Yes | — | — |
| `remedy_text` | `string` or `null` | No | max length: `5000` | — |
| `response_text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `rerun` | `boolean` | No | default: `False` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-holderin"></a>
#### `HolderIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `label` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `responder_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `responder_contact` | `string` or `null` | No | min length: `3`; max length: `255` | — |

<a id="schema-holderout"></a>
#### `HolderOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `holder_uuid` | `string` | Yes | format: `uuid` | — |
| `label` | `string` | Yes | — | — |
| `derived_from` | `string` | Yes | — | — |
| `evidence` | `object` | Yes | — | — |
| `processor_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `processor_name` | `string` or `null` | Yes | — | — |
| `is_in_house` | `boolean` or `null` | Yes | — | — |
| `confirmed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `confirmed_by_name` | `string` or `null` | Yes | — | — |
| `ticket_status` | `string` | Yes | — | — |
| `instruction` | `string` or `null` | Yes | — | — |
| `responder_name` | `string` or `null` | Yes | — | — |
| `responder_contact` | `string` or `null` | Yes | — | — |
| `issued_at` | `string` or `null` | Yes | format: `date-time` | — |
| `due_at` | `string` or `null` | Yes | format: `date-time` | — |
| `escalated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `returned_at` | `string` or `null` | Yes | format: `date-time` | — |
| `return_summary` | `string` or `null` | Yes | — | — |
| `return_evidence_hash` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `channel` | `string` | No | default: `email` | — |
| `respondent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `responder_user_uuid` | `string` or `null` | No | format: `uuid` | — |
| `responder_user_name` | `string` or `null` | No | — | — |
| `contact_log` | array of `object` | No | — | — |
| `brief` | `object` or `null` | No | — | — |
| `message_count` | `integer` | No | default: `0` | — |
| `unread_for_office` | `integer` | No | default: `0` | — |
| `seen_at` | `string` or `null` | No | format: `date-time` | — |
| `last_reminded_at` | `string` or `null` | No | format: `date-time` | — |
| `reminders_sent` | `integer` | No | default: `0` | — |
| `return_evidence_name` | `string` or `null` | No | — | — |
| `sent_back_at` | `string` or `null` | No | format: `date-time` | — |
| `sent_back_reason` | `string` or `null` | No | — | — |
| `sent_back_count` | `integer` | No | default: `0` | — |

<a id="schema-issueticketsin"></a>
#### `IssueTicketsIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `instruction` | `string` or `null` | No | min length: `1`; max length: `20000` | — |
| `due_at` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-itemout"></a>
#### `ItemOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `item_uuid` | `string` | Yes | format: `uuid` | — |
| `other_subjects` | `integer` | Yes | — | — |
| `state` | `string` | Yes | — | — |
| `decision` | `string` or `null` | Yes | — | — |
| `basis` | `string` or `null` | Yes | — | — |
| `retain_until` | `string` or `null` | Yes | format: `date` | — |
| `floor_passed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `decided_at` | `string` or `null` | Yes | format: `date-time` | — |
| `decided_by_name` | `string` or `null` | Yes | — | — |
| `applied_at` | `string` or `null` | Yes | format: `date-time` | — |
| `disposition` | `string` or `null` | Yes | — | — |
| `disposition_at` | `string` or `null` | Yes | format: `date-time` | — |
| `subject_role` | `string` | Yes | — | — |
| `asset_uuid` | `string` | Yes | format: `uuid` | — |
| `asset_type` | `string` | Yes | — | — |
| `source_asset_ref` | `string` | Yes | — | — |
| `source_code` | `string` | Yes | — | — |
| `source_name` | `string` | Yes | — | — |
| `processor_name` | `string` or `null` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `collected_on` | `string` | Yes | format: `date` | — |
| `holder_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `holder_label` | `string` or `null` | Yes | — | — |
| `holder_ticket_status` | `string` or `null` | Yes | — | — |

<a id="schema-logrequest"></a>
#### `LogRequest`

A request that arrived by email, logged by the DPO. Same record as the others.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_type` | `string` | Yes | — | — |
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `request_text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `subject_uuid` | `string` or `null` | No | format: `uuid` | — |
| `about_dpo` | `boolean` | No | default: `False` | — |

<a id="schema-manualverifyin"></a>
#### `ManualVerifyIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `note` | `string` | Yes | min length: `3`; max length: `1000` | — |

<a id="schema-notein"></a>
#### `NoteIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `note` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-page_requestrow"></a>
#### `Page_RequestRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`RequestRow`](#schema-requestrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-reassignin"></a>
#### `ReassignIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `respondent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `responder_name` | `string` or `null` | No | max length: `200` | — |
| `responder_contact` | `string` or `null` | No | max length: `255` | — |

<a id="schema-refusein"></a>
#### `RefuseIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `3`; max length: `5000` | — |

<a id="schema-requestdetail"></a>
#### `RequestDetail`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `original_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `subject_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `subject_name` | `string` or `null` | Yes | — | — |
| `submitted_name` | `string` or `null` | Yes | — | — |
| `submitted_contact` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `acknowledged_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verification_status` | `string` | Yes | — | — |
| `about_dpo` | `boolean` | Yes | — | — |
| `linked_reference` | `string` or `null` | Yes | — | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `threads_unread` | `integer` | No | default: `0` | — |
| `holder_count` | `integer` | Yes | — | — |
| `tickets_outstanding` | `integer` | Yes | — | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`ClockOut`](#schema-clockout) | Yes | — | — |
| `request_text` | `string` | Yes | — | — |
| `subject_email` | `string` or `null` | Yes | — | — |
| `subject_mobile` | `string` or `null` | Yes | — | — |
| `verification_method` | `string` or `null` | Yes | — | — |
| `verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verified_by_name` | `string` or `null` | Yes | — | — |
| `verification_note` | `string` or `null` | Yes | — | — |
| `classified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `refusal_reason` | `string` or `null` | Yes | — | — |
| `intent_confirmed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `linked_request_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `linked_request_type` | `string` or `null` | Yes | — | — |
| `consent_project_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_notice_code` | `string` or `null` | No | — | — |
| `consent_notice_version` | `integer` or `null` | No | — | — |
| `consent_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_withdrawn` | `boolean` or `null` | No | — | — |
| `consent_purposes` | array of `string` or `null` | No | — | — |
| `nomination_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `nominee_name` | `string` or `null` | Yes | — | — |
| `nominee_contact` | `string` or `null` | Yes | — | — |
| `trigger_event` | `string` or `null` | Yes | — | — |
| `trigger_evidence_hash` | `string` or `null` | Yes | — | — |
| `trigger_evidenced_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reviewer_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `reviewer_name` | `string` or `null` | Yes | — | — |
| `escalated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `grievance_upheld` | `boolean` or `null` | Yes | — | — |
| `remedy_text` | `string` or `null` | Yes | — | — |
| `response_text` | `string` or `null` | Yes | — | — |
| `response_file_hash` | `string` or `null` | Yes | — | — |
| `responded_at` | `string` or `null` | Yes | format: `date-time` | — |
| `download_expires_at` | `string` or `null` | Yes | format: `date-time` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `holders_confirmed` | `integer` | Yes | — | — |
| `tickets_issued` | `integer` | Yes | — | — |
| `tickets_returned` | `integer` | Yes | — | — |
| `item_count` | `integer` | Yes | — | — |
| `items_undecided` | `integer` | Yes | — | — |
| `holders` | array of [`HolderOut`](#schema-holderout) | Yes | — | — |
| `items` | array of [`ItemOut`](#schema-itemout) | Yes | — | — |
| `transitions` | array of `object` | Yes | — | — |
| `linked_request` | [`LinkedRequestOut`](#schema-linkedrequestout) or `null` | Yes | — | — |
| `linked_from` | array of [`LinkedRefOut`](#schema-linkedrefout) | Yes | — | — |
| `response_files` | array of [`ResponseFileOut`](#schema-responsefileout) | No | — | — |

<a id="schema-requestout"></a>
#### `RequestOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `original_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `subject_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `subject_name` | `string` or `null` | Yes | — | — |
| `submitted_name` | `string` or `null` | Yes | — | — |
| `submitted_contact` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `acknowledged_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verification_status` | `string` | Yes | — | — |
| `about_dpo` | `boolean` | Yes | — | — |
| `linked_reference` | `string` or `null` | Yes | — | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `threads_unread` | `integer` | No | default: `0` | — |
| `holder_count` | `integer` | Yes | — | — |
| `tickets_outstanding` | `integer` | Yes | — | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`ClockOut`](#schema-clockout) | Yes | — | — |
| `request_text` | `string` | Yes | — | — |
| `subject_email` | `string` or `null` | Yes | — | — |
| `subject_mobile` | `string` or `null` | Yes | — | — |
| `verification_method` | `string` or `null` | Yes | — | — |
| `verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verified_by_name` | `string` or `null` | Yes | — | — |
| `verification_note` | `string` or `null` | Yes | — | — |
| `classified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `refusal_reason` | `string` or `null` | Yes | — | — |
| `intent_confirmed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `linked_request_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `linked_request_type` | `string` or `null` | Yes | — | — |
| `consent_project_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_notice_code` | `string` or `null` | No | — | — |
| `consent_notice_version` | `integer` or `null` | No | — | — |
| `consent_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_withdrawn` | `boolean` or `null` | No | — | — |
| `consent_purposes` | array of `string` or `null` | No | — | — |
| `nomination_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `nominee_name` | `string` or `null` | Yes | — | — |
| `nominee_contact` | `string` or `null` | Yes | — | — |
| `trigger_event` | `string` or `null` | Yes | — | — |
| `trigger_evidence_hash` | `string` or `null` | Yes | — | — |
| `trigger_evidenced_at` | `string` or `null` | Yes | format: `date-time` | — |
| `reviewer_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `reviewer_name` | `string` or `null` | Yes | — | — |
| `escalated_at` | `string` or `null` | Yes | format: `date-time` | — |
| `grievance_upheld` | `boolean` or `null` | Yes | — | — |
| `remedy_text` | `string` or `null` | Yes | — | — |
| `response_text` | `string` or `null` | Yes | — | — |
| `response_file_hash` | `string` or `null` | Yes | — | — |
| `responded_at` | `string` or `null` | Yes | format: `date-time` | — |
| `download_expires_at` | `string` or `null` | Yes | format: `date-time` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |
| `holders_confirmed` | `integer` | Yes | — | — |
| `tickets_issued` | `integer` | Yes | — | — |
| `tickets_returned` | `integer` | Yes | — | — |
| `item_count` | `integer` | Yes | — | — |
| `items_undecided` | `integer` | Yes | — | — |

<a id="schema-reviewerin"></a>
#### `ReviewerIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reviewer_uuid` | `string` | Yes | format: `uuid` | — |

<a id="schema-sendbackin"></a>
#### `SendBackIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | max length: `1000` | — |
| `due_at` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-threadout"></a>
#### `ThreadOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `holder` | [`HolderOut`](#schema-holderout) | Yes | — | — |
| `messages` | array of [`cmp__api__routers__v1__rights__MessageOut`](#schema-cmp_api_routers_v1_rights_messageout) | Yes | — | — |

<a id="schema-transitionin"></a>
#### `TransitionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `to` | `string` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-withdrawin"></a>
#### `WithdrawIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `reason` | `string` | Yes | min length: `1`; max length: `2000` | — |

<a id="schema-cmp_api_routers_v1_rights_transitionsout"></a>
#### `cmp__api__routers__v1__rights__TransitionsOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `current` | `string` | Yes | — | — |
| `available` | array of `object` | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-requestrow"></a>
#### `RequestRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `original_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `subject_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `subject_name` | `string` or `null` | Yes | — | — |
| `submitted_name` | `string` or `null` | Yes | — | — |
| `submitted_contact` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `acknowledged_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verification_status` | `string` | Yes | — | — |
| `about_dpo` | `boolean` | Yes | — | — |
| `linked_reference` | `string` or `null` | Yes | — | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `threads_unread` | `integer` | No | default: `0` | — |
| `holder_count` | `integer` | Yes | — | — |
| `tickets_outstanding` | `integer` | Yes | — | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`ClockOut`](#schema-clockout) | Yes | — | — |

<a id="schema-clockout"></a>
#### `ClockOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `received_at` | `string` | Yes | format: `date-time` | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `acknowledge_by` | `string` | Yes | format: `date-time` | — |
| `tickets_by` | `string` | Yes | format: `date-time` | — |
| `halfway_at` | `string` | Yes | format: `date-time` | — |
| `collate_by` | `string` | Yes | format: `date-time` | — |
| `days_remaining` | `integer` | Yes | — | — |
| `overdue` | `boolean` | Yes | — | — |
| `at_risk` | `boolean` | Yes | — | — |
| `progress` | `number` | Yes | — | — |
| `checkpoints` | array of `object` | Yes | — | — |
| `next_checkpoint` | `string` or `null` | Yes | — | — |

<a id="schema-linkedrequestout"></a>
#### `LinkedRequestOut`

The request a grievance is about, as much of it as deciding the
grievance needs: what she asked, when it was due and when it was answered,
how identity was established, what was returned, and whether every holder
came back. Carried on the grievance so the person deciding it - the DPO, or
a reviewer whose scope does not reach the original - sees it without
leaving the page. `in_scope` says whether the full record can be opened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `channel` | `string` | Yes | — | — |
| `request_text` | `string` | Yes | — | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `verification_method` | `string` or `null` | Yes | — | — |
| `verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `responded_at` | `string` or `null` | Yes | format: `date-time` | — |
| `response_text` | `string` or `null` | Yes | — | — |
| `refusal_reason` | `string` or `null` | Yes | — | — |
| `remedy_text` | `string` or `null` | Yes | — | — |
| `response_file_hash` | `string` or `null` | Yes | — | — |
| `holder_count` | `integer` | Yes | — | — |
| `tickets_issued` | `integer` | Yes | — | — |
| `tickets_returned` | `integer` | Yes | — | — |
| `clock` | [`ClockOut`](#schema-clockout) | Yes | — | — |
| `in_scope` | `boolean` | Yes | — | — |

<a id="schema-linkedrefout"></a>
#### `LinkedRefOut`

A request that points at this one: the grievance that disputes it, or
the re-run a grievance ordered.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |

<a id="schema-responsefileout"></a>
#### `ResponseFileOut`

A file released with the response, downloaded from the account.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `file_uuid` | `string` | Yes | format: `uuid` | — |
| `file_name` | `string` | Yes | — | — |
| `file_hash` | `string` | Yes | — | — |
| `size_bytes` | `integer` | Yes | — | — |
| `content_type` | `string` or `null` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-cmp_api_routers_v1_rights_messageout"></a>
#### `cmp__api__routers__v1__rights__MessageOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `message_uuid` | `string` | Yes | format: `uuid` | — |
| `author_side` | `string` | Yes | — | — |
| `author_name` | `string` or `null` | Yes | — | — |
| `kind` | `string` | Yes | — | — |
| `body` | `string` | Yes | — | — |
| `evidence_hash` | `string` or `null` | Yes | — | — |
| `evidence_name` | `string` or `null` | No | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
