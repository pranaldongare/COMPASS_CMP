# Me API

Generated from `backend/api/openapi.json`. **26 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /me`](#1_get_me)
2. [`PATCH /me`](#2_patch_me)
3. [`POST /me/contacts/code`](#3_post_me_contacts_code)
4. [`POST /me/contact/verify`](#4_post_me_contact_verify)
5. [`DELETE /me/secondary-email`](#5_delete_me_secondary_email)
6. [`POST /me/person-type`](#6_post_me_person_type)
7. [`GET /me/consents`](#7_get_me_consents)
8. [`GET /me/consents/{consent_uuid}`](#8_get_me_consents_consent_uuid)
9. [`GET /me/consents/{consent_uuid}/notice`](#9_get_me_consents_consent_uuid_notice)
10. [`GET /me/consents/{consent_uuid}/grants`](#10_get_me_consents_consent_uuid_grants)
11. [`GET /me/consents/{consent_uuid}/history`](#11_get_me_consents_consent_uuid_history)
12. [`GET /me/consents/{consent_uuid}/trail`](#12_get_me_consents_consent_uuid_trail)
13. [`POST /me/consents/{consent_uuid}/withdraw`](#13_post_me_consents_consent_uuid_withdraw)
14. [`GET /me/disclosures`](#14_get_me_disclosures)
15. [`GET /me/notifications`](#15_get_me_notifications)
16. [`GET /me/requests`](#16_get_me_requests)
17. [`POST /me/requests`](#17_post_me_requests)
18. [`GET /me/requests/{request_uuid}`](#18_get_me_requests_request_uuid)
19. [`GET /me/requests/{request_uuid}/trail`](#19_get_me_requests_request_uuid_trail)
20. [`GET /me/requests/{request_uuid}/download`](#20_get_me_requests_request_uuid_download)
21. [`GET /me/requests/{request_uuid}/files/{file_uuid}`](#21_get_me_requests_request_uuid_files_file_uuid)
22. [`POST /me/requests/{request_uuid}/dispute`](#22_post_me_requests_request_uuid_dispute)
23. [`GET /me/nominations`](#23_get_me_nominations)
24. [`POST /me/nominations`](#24_post_me_nominations)
25. [`GET /me/nominee-of`](#25_get_me_nominee_of)
26. [`DELETE /me/nominations/{nomination_uuid}`](#26_delete_me_nominations_nomination_uuid)

<a id="1_get_me"></a>
## 1. `GET /me` — Get Me

### API

- **Operation ID:** `get_me_me_get`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MeProfile`](#schema-meprofile) |

**Example `200` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "organization_id": "string",
  "person_type": "string",
  "status": "string",
  "dob": "string",
  "is_minor": true,
  "created_at": "string",
  "secondary_email": "string",
  "mobile_verified_at": "2026-09-17T12:00:00Z",
  "email_verified_at": "2026-09-17T12:00:00Z",
  "secondary_email_verified_at": "2026-09-17T12:00:00Z"
}
```

<a id="2_patch_me"></a>
## 2. `PATCH /me` — Update Me

### API

- **Operation ID:** `update_me_me_patch`
- **Access:** Authenticated caller acting on their own records.

Her own details. A contact she gives here is sent a code in the same
request, and cannot sign her in until it comes back.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`UpdateMe`](#schema-updateme)

```json
{
  "full_name": "string",
  "mobile": "string",
  "secondary_email": "string",
  "dob": "2026-09-17"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`MeProfile`](#schema-meprofile) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "uuid": "00000000-0000-4000-8000-000000000000",
  "full_name": "string",
  "email": "string",
  "mobile": "string",
  "organization_id": "string",
  "person_type": "string",
  "status": "string",
  "dob": "string",
  "is_minor": true,
  "created_at": "string",
  "secondary_email": "string",
  "mobile_verified_at": "2026-09-17T12:00:00Z",
  "email_verified_at": "2026-09-17T12:00:00Z",
  "secondary_email_verified_at": "2026-09-17T12:00:00Z"
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

<a id="3_post_me_contacts_code"></a>
## 3. `POST /me/contacts/code` — A code to confirm one of my contacts

### API

- **Operation ID:** `contact_code_me_contacts_code_post`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ContactCodeRequest`](#schema-contactcoderequest)

```json
{
  "contact": "string"
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

<a id="4_post_me_contact_verify"></a>
## 4. `POST /me/contact/verify` — Confirm one of my contacts

### API

- **Operation ID:** `verify_contact_me_contact_verify_post`
- **Access:** Authenticated caller acting on their own records.

The code came back, so the contact is hers and may now sign her in.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ContactVerify`](#schema-contactverify)

```json
{
  "contact": "string",
  "code": "string"
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

<a id="5_delete_me_secondary_email"></a>
## 5. `DELETE /me/secondary-email` — Remove my second address

### API

- **Operation ID:** `remove_secondary_email_me_secondary_email_delete`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Acknowledged`](#schema-acknowledged) |

**Example `200` `application/json` response:**

```json
{
  "ok": true,
  "message": "string"
}
```

<a id="6_post_me_person_type"></a>
## 6. `POST /me/person-type` — Change Person Type

### API

- **Operation ID:** `change_person_type_me_person_type_post`
- **Access:** Authenticated caller acting on their own records.

`role` is authorisation, `person_type` is identity.

They are separate columns because a DPO is *also* an employee. A type change
must never alter permissions, and this endpoint does not touch `role`.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`PersonTypeChange`](#schema-persontypechange)

```json
{
  "person_type": "string",
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

<a id="7_get_me_consents"></a>
## 7. `GET /me/consents` — My Consents

### API

- **Operation ID:** `my_consents_me_consents_get`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ConsentSummary`](#schema-consentsummary) |

**Example `200` `application/json` response:**

```json
[
  {
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string",
    "notice_uuid": "00000000-0000-4000-8000-000000000000",
    "notice_code": "string",
    "version": 1,
    "language_code": "string",
    "affirmative_action_at": "string",
    "is_withdrawal": true,
    "granted_count": 1,
    "purpose_count": 1
  }
]
```

<a id="8_get_me_consents_consent_uuid"></a>
## 8. `GET /me/consents/{consent_uuid}` — My Consent

### API

- **Operation ID:** `my_consent_me_consents__consent_uuid__get`
- **Access:** Authenticated caller acting on their own records.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="9_get_me_consents_consent_uuid_notice"></a>
## 9. `GET /me/consents/{consent_uuid}/notice` — The words she actually saw

### API

- **Operation ID:** `my_consent_notice_me_consents__consent_uuid__notice_get`
- **Access:** Authenticated caller acting on their own records.

Reads the copied `notice_content_hash`, not the live notice.

Joining live to notice_language would let a later correction silently
repoint her record at words she never saw.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="10_get_me_consents_consent_uuid_grants"></a>
## 10. `GET /me/consents/{consent_uuid}/grants` — My Consent Grants

### API

- **Operation ID:** `my_consent_grants_me_consents__consent_uuid__grants_get`
- **Access:** Authenticated caller acting on their own records.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="11_get_me_consents_consent_uuid_history"></a>
## 11. `GET /me/consents/{consent_uuid}/history` — The supersession chain

### API

- **Operation ID:** `my_consent_history_me_consents__consent_uuid__history_get`
- **Access:** Authenticated caller acting on their own records.

Every grant and withdrawal in order, so she can see the whole sequence.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="12_get_me_consents_consent_uuid_trail"></a>
## 12. `GET /me/consents/{consent_uuid}/trail` — What was recorded about this consent

### API

- **Operation ID:** `my_consent_trail_me_consents__consent_uuid__trail_get`
- **Access:** Authenticated caller acting on their own records.

The audit trail for one consent, in her own words rather than the DPO's.

The same rows the DPO's audit trail shows and the same entity resolver, so
there is one record and two views of it rather than two records that can
disagree. What differs is the scope: only artefacts in *her* chain for this
notice, which `_own_consent` has already proved is hers.

**Refused and withdrawn consents have trails too**, and this is the endpoint
that shows them. A decision to refuse is a decision the Act protects — s.6(1)
requires consent to be freely given, and "freely" is not demonstrable if the
person cannot see that their refusal was recorded, when, and against which
notice. A system that only evidences agreement is a system that quietly
treats refusal as an absence.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="13_post_me_consents_consent_uuid_withdraw"></a>
## 13. `POST /me/consents/{consent_uuid}/withdraw` — Withdraw

### API

- **Operation ID:** `withdraw_me_consents__consent_uuid__withdraw_post`
- **Access:** Authenticated caller acting on their own records.

Withdraw some purposes or all of them.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`WithdrawRequest`](#schema-withdrawrequest)

```json
{
  "purposes": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "all": false
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

<a id="14_get_me_disclosures"></a>
## 14. `GET /me/disclosures` — Who was my data shared with (s.11(1)(b))

### API

- **Operation ID:** `my_disclosures_me_disclosures_get`
- **Access:** Authenticated caller acting on their own records.

Answered from export_line, not by parsing an archived CSV.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of `object` |

**Example `200` `application/json` response:**

```json
[
  {}
]
```

<a id="15_get_me_notifications"></a>
## 15. `GET /me/notifications` — My Notifications

### API

- **Operation ID:** `my_notifications_me_notifications_get`
- **Access:** Authenticated caller acting on their own records.

Notifications a data subject can see, derived from her own audit trail.

There is no notifications table in the 22; the events that concern her are
already recorded, and deriving the feed means it can never disagree with the
record.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `limit` | query | No | `integer` | minimum: `1`; maximum: `100`; default: `50` | — |

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

<a id="16_get_me_requests"></a>
## 16. `GET /me/requests` — My requests

### API

- **Operation ID:** `my_requests_me_requests_get`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`SubjectRequestOut`](#schema-subjectrequestout) |

**Example `200` `application/json` response:**

```json
[
  {
    "request_uuid": "00000000-0000-4000-8000-000000000000",
    "reference": "string",
    "request_type": "string",
    "status": "string",
    "outcome": "string",
    "channel": "string",
    "request_text": "string",
    "received_at": "2026-09-17T12:00:00Z",
    "due_at": "2026-09-17T12:00:00Z",
    "acknowledged_at": "2026-09-17T12:00:00Z",
    "verification_status": "string",
    "responded_at": "2026-09-17T12:00:00Z",
    "response_text": "string",
    "refusal_reason": "string",
    "remedy_text": "string",
    "grievance_upheld": true,
    "download_available": true,
    "download_expires_at": "2026-09-17T12:00:00Z",
    "linked_reference": "string",
    "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_uuid": "00000000-0000-4000-8000-000000000000",
    "consent_project": "string",
    "consent_notice_code": "string",
    "consent_notice_version": 1,
    "consent_at": "2026-09-17T12:00:00Z",
    "consent_purposes": [
      "string"
    ],
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
        "…"
      ],
      "next_checkpoint": "…"
    },
    "response_files": [
      {
        "file_uuid": "…",
        "file_name": "…",
        "file_hash": "…",
        "size_bytes": "…",
        "content_type": "…",
        "created_at": "…"
      }
    ]
  }
]
```

<a id="17_post_me_requests"></a>
## 17. `POST /me/requests` — Make a request, signed in

### API

- **Operation ID:** `make_request_me_requests_post`
- **Access:** Authenticated caller acting on their own records.

From the dashboard. The session is the verification, so the clock starts
and the acknowledgement goes out in the same moment.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SubjectRequestIn`](#schema-subjectrequestin)

```json
{
  "request_type": "string",
  "request_text": "string",
  "about_dpo": false,
  "consent_uuid": "00000000-0000-4000-8000-000000000000"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`SubjectRequestOut`](#schema-subjectrequestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "request_text": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "response_text": "string",
  "refusal_reason": "string",
  "remedy_text": "string",
  "grievance_upheld": true,
  "download_available": true,
  "download_expires_at": "2026-09-17T12:00:00Z",
  "linked_reference": "string",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_purposes": [
    "string"
  ],
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

<a id="18_get_me_requests_request_uuid"></a>
## 18. `GET /me/requests/{request_uuid}` — My Request

### API

- **Operation ID:** `my_request_me_requests__request_uuid__get`
- **Access:** Authenticated caller acting on their own records.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`SubjectRequestOut`](#schema-subjectrequestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "request_text": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "response_text": "string",
  "refusal_reason": "string",
  "remedy_text": "string",
  "grievance_upheld": true,
  "download_available": true,
  "download_expires_at": "2026-09-17T12:00:00Z",
  "linked_reference": "string",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_purposes": [
    "string"
  ],
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

<a id="19_get_me_requests_request_uuid_trail"></a>
## 19. `GET /me/requests/{request_uuid}/trail` — What was recorded about my request

### API

- **Operation ID:** `my_request_trail_me_requests__request_uuid__trail_get`
- **Access:** Authenticated caller acting on their own records.

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

<a id="20_get_me_requests_request_uuid_download"></a>
## 20. `GET /me/requests/{request_uuid}/download` — The response, while the window is open

### API

- **Operation ID:** `my_download_me_requests__request_uuid__download_get`
- **Access:** Authenticated caller acting on their own records.

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

<a id="21_get_me_requests_request_uuid_files_file_uuid"></a>
## 21. `GET /me/requests/{request_uuid}/files/{file_uuid}` — A file released with the response, while the window is open

### API

- **Operation ID:** `my_download_file_me_requests__request_uuid__files__file_uuid__get`
- **Access:** Authenticated caller acting on their own records.

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

<a id="22_post_me_requests_request_uuid_dispute"></a>
## 22. `POST /me/requests/{request_uuid}/dispute` — Dispute the response - a grievance under s.13

### API

- **Operation ID:** `dispute_me_requests__request_uuid__dispute_post`
- **Access:** Authenticated caller acting on their own records.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `request_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`DisputeIn`](#schema-disputein)

```json
{
  "text": "string",
  "about_dpo": false
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`SubjectRequestOut`](#schema-subjectrequestout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "request_uuid": "00000000-0000-4000-8000-000000000000",
  "reference": "string",
  "request_type": "string",
  "status": "string",
  "outcome": "string",
  "channel": "string",
  "request_text": "string",
  "received_at": "2026-09-17T12:00:00Z",
  "due_at": "2026-09-17T12:00:00Z",
  "acknowledged_at": "2026-09-17T12:00:00Z",
  "verification_status": "string",
  "responded_at": "2026-09-17T12:00:00Z",
  "response_text": "string",
  "refusal_reason": "string",
  "remedy_text": "string",
  "grievance_upheld": true,
  "download_available": true,
  "download_expires_at": "2026-09-17T12:00:00Z",
  "linked_reference": "string",
  "linked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "consent_project": "string",
  "consent_notice_code": "string",
  "consent_notice_version": 1,
  "consent_at": "2026-09-17T12:00:00Z",
  "consent_purposes": [
    "string"
  ],
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

<a id="23_get_me_nominations"></a>
## 23. `GET /me/nominations` — Whom I have nominated

### API

- **Operation ID:** `my_nominations_me_nominations_get`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`NominationOut`](#schema-nominationout) |

**Example `200` `application/json` response:**

```json
[
  {
    "nomination_uuid": "00000000-0000-4000-8000-000000000000",
    "nominee_name": "string",
    "nominee_mobile": "string",
    "nominee_email": "string",
    "rights": [
      "string"
    ],
    "status": "string",
    "accept_expires_at": "2026-09-17T12:00:00Z",
    "accepted_at": "2026-09-17T12:00:00Z",
    "declined_at": "2026-09-17T12:00:00Z",
    "revoked_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "invoked_at": "2026-09-17T12:00:00Z",
    "invoked_event": "string",
    "invoked_reference": "string",
    "invoked_request_uuid": "00000000-0000-4000-8000-000000000000",
    "invoked_evidenced_at": "2026-09-17T12:00:00Z"
  }
]
```

<a id="24_post_me_nominations"></a>
## 24. `POST /me/nominations` — Nominate somebody - s.14

### API

- **Operation ID:** `nominate_me_nominations_post`
- **Access:** Authenticated caller acting on their own records.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`NominationIn`](#schema-nominationin)

```json
{
  "nominee_name": "string",
  "nominee_mobile": "string",
  "nominee_email": "string",
  "rights": [
    "string"
  ]
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`NominationOut`](#schema-nominationout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_mobile": "string",
  "nominee_email": "string",
  "rights": [
    "string"
  ],
  "status": "string",
  "accept_expires_at": "2026-09-17T12:00:00Z",
  "accepted_at": "2026-09-17T12:00:00Z",
  "declined_at": "2026-09-17T12:00:00Z",
  "revoked_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "invoked_at": "2026-09-17T12:00:00Z",
  "invoked_event": "string",
  "invoked_reference": "string",
  "invoked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "invoked_evidenced_at": "2026-09-17T12:00:00Z"
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

<a id="25_get_me_nominee_of"></a>
## 25. `GET /me/nominee-of` — Who has nominated me

### API

- **Operation ID:** `nominations_naming_me_me_nominee_of_get`
- **Access:** Authenticated caller acting on their own records.

Nominations where the caller is the nominee.

A data principal can be somebody else's nominee too, and until this
existed her account said nothing about it. Matched on the account recorded
when she accepted, falling back to the contacts the principal wrote down
for nominations accepted before that was kept.

Each row carries how far the request she raised has got. Raising a *new*
one still goes through the nominee page and a code to a recorded contact:
being signed in here is enough to read what became of her own request, and
not enough to make another in somebody else's name.

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`NomineeOfOut`](#schema-nomineeofout) |

**Example `200` `application/json` response:**

```json
[
  {
    "nomination_uuid": "00000000-0000-4000-8000-000000000000",
    "principal_name": "string",
    "rights": [
      "string"
    ],
    "status": "string",
    "contact": "string",
    "accept_expires_at": "2026-09-17T12:00:00Z",
    "accepted_at": "2026-09-17T12:00:00Z",
    "created_at": "2026-09-17T12:00:00Z",
    "invoked_at": "2026-09-17T12:00:00Z",
    "invoked_event": "string",
    "invoked_reference": "string",
    "invoked_evidenced_at": "2026-09-17T12:00:00Z",
    "invoked_request_uuid": "00000000-0000-4000-8000-000000000000",
    "invoked_request_type": "string",
    "invoked_status": "string",
    "invoked_outcome": "string",
    "invoked_due_at": "2026-09-17T12:00:00Z",
    "invoked_responded_at": "2026-09-17T12:00:00Z",
    "invoked_closed_at": "2026-09-17T12:00:00Z"
  }
]
```

<a id="26_delete_me_nominations_nomination_uuid"></a>
## 26. `DELETE /me/nominations/{nomination_uuid}` — Revoke a nomination

### API

- **Operation ID:** `revoke_nomination_me_nominations__nomination_uuid__delete`
- **Access:** Authenticated caller acting on their own records.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `nomination_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`NominationOut`](#schema-nominationout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "nomination_uuid": "00000000-0000-4000-8000-000000000000",
  "nominee_name": "string",
  "nominee_mobile": "string",
  "nominee_email": "string",
  "rights": [
    "string"
  ],
  "status": "string",
  "accept_expires_at": "2026-09-17T12:00:00Z",
  "accepted_at": "2026-09-17T12:00:00Z",
  "declined_at": "2026-09-17T12:00:00Z",
  "revoked_at": "2026-09-17T12:00:00Z",
  "created_at": "2026-09-17T12:00:00Z",
  "invoked_at": "2026-09-17T12:00:00Z",
  "invoked_event": "string",
  "invoked_reference": "string",
  "invoked_request_uuid": "00000000-0000-4000-8000-000000000000",
  "invoked_evidenced_at": "2026-09-17T12:00:00Z"
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

<a id="schema-contactcoderequest"></a>
#### `ContactCodeRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |

<a id="schema-contactverify"></a>
#### `ContactVerify`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `contact` | `string` | Yes | min length: `3`; max length: `255` | — |
| `code` | `string` | Yes | min length: `4`; max length: `10`; pattern: `^[0-9]+$` | — |

<a id="schema-disputein"></a>
#### `DisputeIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `about_dpo` | `boolean` | No | default: `False` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-meprofile"></a>
#### `MeProfile`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `uuid` | `string` | Yes | format: `uuid` | — |
| `full_name` | `string` | Yes | — | — |
| `email` | `string` or `null` | Yes | — | — |
| `mobile` | `string` or `null` | Yes | — | — |
| `organization_id` | `string` or `null` | Yes | — | — |
| `person_type` | `string` or `null` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `dob` | `string` or `null` | Yes | — | — |
| `is_minor` | `boolean` or `null` | Yes | — | — |
| `created_at` | `object` | Yes | — | — |
| `secondary_email` | `string` or `null` | Yes | — | — |
| `mobile_verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `email_verified_at` | `string` or `null` | Yes | format: `date-time` | — |
| `secondary_email_verified_at` | `string` or `null` | Yes | format: `date-time` | — |

<a id="schema-nominationin"></a>
#### `NominationIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `nominee_name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `nominee_mobile` | `string` | Yes | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `nominee_email` | `string` or `null` | No | max length: `255`; format: `email` | — |
| `rights` | array of `string` | Yes | — | — |

<a id="schema-nominationout"></a>
#### `NominationOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `nomination_uuid` | `string` | Yes | format: `uuid` | — |
| `nominee_name` | `string` | Yes | — | — |
| `nominee_mobile` | `string` or `null` | Yes | — | — |
| `nominee_email` | `string` or `null` | Yes | — | — |
| `rights` | array of `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `accept_expires_at` | `string` or `null` | Yes | format: `date-time` | — |
| `accepted_at` | `string` or `null` | Yes | format: `date-time` | — |
| `declined_at` | `string` or `null` | Yes | format: `date-time` | — |
| `revoked_at` | `string` or `null` | Yes | format: `date-time` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `invoked_at` | `string` or `null` | No | format: `date-time` | — |
| `invoked_event` | `string` or `null` | No | — | — |
| `invoked_reference` | `string` or `null` | No | — | — |
| `invoked_request_uuid` | `string` or `null` | No | format: `uuid` | — |
| `invoked_evidenced_at` | `string` or `null` | No | format: `date-time` | — |

<a id="schema-persontypechange"></a>
#### `PersonTypeChange`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `person_type` | `string` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `500` | — |

<a id="schema-subjectrequestin"></a>
#### `SubjectRequestIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_type` | `string` | Yes | — | — |
| `request_text` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `about_dpo` | `boolean` | No | default: `False` | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-subjectrequestout"></a>
#### `SubjectRequestOut`

What she sees of her own request. No verification notes, no holders -
the holders are in the response itself, and the notes are ours.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `request_uuid` | `string` | Yes | format: `uuid` | — |
| `reference` | `string` | Yes | — | — |
| `request_type` | `string` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `outcome` | `string` or `null` | Yes | — | — |
| `channel` | `string` | Yes | — | — |
| `request_text` | `string` | Yes | — | — |
| `received_at` | `string` | Yes | format: `date-time` | — |
| `due_at` | `string` | Yes | format: `date-time` | — |
| `acknowledged_at` | `string` or `null` | Yes | format: `date-time` | — |
| `verification_status` | `string` | Yes | — | — |
| `responded_at` | `string` or `null` | Yes | format: `date-time` | — |
| `response_text` | `string` or `null` | Yes | — | — |
| `refusal_reason` | `string` or `null` | Yes | — | — |
| `remedy_text` | `string` or `null` | Yes | — | — |
| `grievance_upheld` | `boolean` or `null` | Yes | — | — |
| `download_available` | `boolean` | Yes | — | — |
| `download_expires_at` | `string` or `null` | Yes | format: `date-time` | — |
| `linked_reference` | `string` or `null` | Yes | — | — |
| `linked_request_uuid` | `string` or `null` | Yes | format: `uuid` | — |
| `consent_uuid` | `string` or `null` | No | format: `uuid` | — |
| `consent_project` | `string` or `null` | No | — | — |
| `consent_notice_code` | `string` or `null` | No | — | — |
| `consent_notice_version` | `integer` or `null` | No | — | — |
| `consent_at` | `string` or `null` | No | format: `date-time` | — |
| `consent_purposes` | array of `string` or `null` | No | — | — |
| `closed_at` | `string` or `null` | Yes | format: `date-time` | — |
| `clock` | [`ClockOut`](#schema-clockout) | Yes | — | — |
| `response_files` | array of [`ResponseFileOut`](#schema-responsefileout) | No | — | — |

<a id="schema-updateme"></a>
#### `UpdateMe`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `full_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `mobile` | `string` or `null` | No | min length: `6`; max length: `20`; pattern: `^\+?[0-9 \-]+$` | — |
| `secondary_email` | `string` or `null` | No | max length: `255`; format: `email` | — |
| `dob` | `string` or `null` | No | format: `date` | — |

<a id="schema-withdrawrequest"></a>
#### `WithdrawRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `purposes` | array of `string` or `null` | No | — | — |
| `all` | `boolean` | No | default: `False` | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

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
