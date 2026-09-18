# Projects API

Generated from `cmp_backend/openapi.json`. **27 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /sites`](#1_get_sites)
2. [`GET /approvals`](#2_get_approvals)
3. [`GET /projects`](#3_get_projects)
4. [`POST /projects`](#4_post_projects)
5. [`GET /projects/{project_uuid}`](#5_get_projects_project_uuid)
6. [`PUT /projects/{project_uuid}`](#6_put_projects_project_uuid)
7. [`GET /projects/{project_uuid}/transitions`](#7_get_projects_project_uuid_transitions)
8. [`POST /projects/{project_uuid}/transition`](#8_post_projects_project_uuid_transition)
9. [`GET /projects/{project_uuid}/history`](#9_get_projects_project_uuid_history)
10. [`GET /projects/{project_uuid}/summary`](#10_get_projects_project_uuid_summary)
11. [`GET /projects/{project_uuid}/processors`](#11_get_projects_project_uuid_processors)
12. [`POST /projects/{project_uuid}/processors`](#12_post_projects_project_uuid_processors)
13. [`PUT /projects/{project_uuid}/processors`](#13_put_projects_project_uuid_processors)
14. [`POST /projects/{project_uuid}/processors/{processor_uuid}/decision`](#14_post_projects_project_uuid_processors_processor_uuid_decision)
15. [`POST /projects/{project_uuid}/close`](#15_post_projects_project_uuid_close)
16. [`GET /projects/{project_uuid}/approvals`](#16_get_projects_project_uuid_approvals)
17. [`POST /projects/{project_uuid}/approvals`](#17_post_projects_project_uuid_approvals)
18. [`GET /approvals/{approval_uuid}`](#18_get_approvals_approval_uuid)
19. [`GET /approvals/{approval_uuid}/proof`](#19_get_approvals_approval_uuid_proof)
20. [`GET /projects/{project_uuid}/sites`](#20_get_projects_project_uuid_sites)
21. [`POST /projects/{project_uuid}/sites`](#21_post_projects_project_uuid_sites)
22. [`GET /sites/{site_uuid}`](#22_get_sites_site_uuid)
23. [`PUT /sites/{site_uuid}`](#23_put_sites_site_uuid)
24. [`PUT /sites/{site_uuid}/source`](#24_put_sites_site_uuid_source)
25. [`PUT /sites/{site_uuid}/owner`](#25_put_sites_site_uuid_owner)
26. [`POST /sites/{site_uuid}/deactivate`](#26_post_sites_site_uuid_deactivate)
27. [`POST /sites/{site_uuid}/agent`](#27_post_sites_site_uuid_agent)

<a id="1_get_sites"></a>
## 1. `GET /sites` — All sites in scope

### API

- **Operation ID:** `list_all_sites_sites_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Every collection site in scope.

A site is a recipient named in a published notice, so this doubles as the
answer to "where does our data actually go".

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_SiteListRow_`](#schema-page_sitelistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "site_uuid": "00000000-0000-4000-8000-000000000000",
      "site_label": "string",
      "location": "…",
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "project_status": "string",
      "processor_uuid": "…",
      "processor_name": "…",
      "active_links": 1
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

<a id="2_get_approvals"></a>
## 2. `GET /approvals` — All approvals in scope

### API

- **Operation ID:** `list_all_approvals_approvals_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Every approval in scope, with the hash of its proof file (INV-8).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_ApprovalListRow_`](#schema-page_approvallistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "approval_uuid": "00000000-0000-4000-8000-000000000000",
      "approval_type": "string",
      "reference_no": "string",
      "approved_on": "2026-09-17",
      "proof_file_hash": "string",
      "uploaded_at": "2026-09-17T12:00:00Z",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "project_status": "string",
      "uploaded_by_uuid": "00000000-0000-4000-8000-000000000000",
      "uploaded_by_name": "string"
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

<a id="3_get_projects"></a>
## 3. `GET /projects` — List Projects

### API

- **Operation ID:** `list_projects_projects_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

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
| `200` | Successful Response | `application/json` | [`Page_ProjectOut_`](#schema-page_projectout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "internal_project_name": "…",
      "description": "…",
      "requesting_team": "…",
      "project_status": "string",
      "dco_uuid": "…",
      "dco_name": "…",
      "created_by_name": "…",
      "current_notice_uuid": "…",
      "created_at": "2026-09-17T12:00:00Z",
      "updated_at": "2026-09-17T12:00:00Z"
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

<a id="4_post_projects"></a>
## 4. `POST /projects` — Create Project

### API

- **Operation ID:** `create_project_projects_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProjectIn`](#schema-projectin)

```json
{
  "project_name": "string",
  "description": "string",
  "processor_uuids": [
    "00000000-0000-4000-8000-000000000000"
  ],
  "internal_project_name": "string",
  "requesting_team": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `201` | Successful Response | `application/json` | [`ProjectOut`](#schema-projectout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `201` `application/json` response:**

```json
{
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "internal_project_name": "string",
  "description": "string",
  "requesting_team": "string",
  "project_status": "string",
  "dco_uuid": "00000000-0000-4000-8000-000000000000",
  "dco_name": "string",
  "created_by_name": "string",
  "current_notice_uuid": "00000000-0000-4000-8000-000000000000",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z"
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

<a id="5_get_projects_project_uuid"></a>
## 5. `GET /projects/{project_uuid}` — Get Project

### API

- **Operation ID:** `get_project_projects__project_uuid__get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ProjectOut`](#schema-projectout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "internal_project_name": "string",
  "description": "string",
  "requesting_team": "string",
  "project_status": "string",
  "dco_uuid": "00000000-0000-4000-8000-000000000000",
  "dco_name": "string",
  "created_by_name": "string",
  "current_notice_uuid": "00000000-0000-4000-8000-000000000000",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z"
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

<a id="6_put_projects_project_uuid"></a>
## 6. `PUT /projects/{project_uuid}` — Draft only

### API

- **Operation ID:** `update_project_projects__project_uuid__put`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProjectUpdate`](#schema-projectupdate)

```json
{
  "project_name": "string",
  "description": "string",
  "internal_project_name": "string",
  "requesting_team": "string"
}
```

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ProjectOut`](#schema-projectout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "internal_project_name": "string",
  "description": "string",
  "requesting_team": "string",
  "project_status": "string",
  "dco_uuid": "00000000-0000-4000-8000-000000000000",
  "dco_name": "string",
  "created_by_name": "string",
  "current_notice_uuid": "00000000-0000-4000-8000-000000000000",
  "created_at": "2026-09-17T12:00:00Z",
  "updated_at": "2026-09-17T12:00:00Z"
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

<a id="7_get_projects_project_uuid_transitions"></a>
## 7. `GET /projects/{project_uuid}/transitions` — What may happen next, and why not

### API

- **Operation ID:** `transitions_projects__project_uuid__transitions_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`cmp__api__routers__v1__projects__TransitionsOut`](#schema-cmp_api_routers_v1_projects_transitionsout) |
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
      "reason_required": false,
      "publishes_notice": false
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

<a id="8_post_projects_project_uuid_transition"></a>
## 8. `POST /projects/{project_uuid}/transition` — Transition

### API

- **Operation ID:** `transition_projects__project_uuid__transition_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TransitionRequest`](#schema-transitionrequest)

```json
{
  "to": "string",
  "reason": "string"
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

<a id="9_get_projects_project_uuid_history"></a>
## 9. `GET /projects/{project_uuid}/history` — Project History

### API

- **Operation ID:** `project_history_projects__project_uuid__history_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="10_get_projects_project_uuid_summary"></a>
## 10. `GET /projects/{project_uuid}/summary` — Everything a dashboard needs, in one call

### API

- **Operation ID:** `project_summary_projects__project_uuid__summary_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="11_get_projects_project_uuid_processors"></a>
## 11. `GET /projects/{project_uuid}/processors` — List Project Processors

### API

- **Operation ID:** `list_project_processors_projects__project_uuid__processors_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="12_post_projects_project_uuid_processors"></a>
## 12. `POST /projects/{project_uuid}/processors` — Request Project Processor

### API

- **Operation ID:** `request_project_processor_projects__project_uuid__processors_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Add a collector, or ask the DPO to let you.

Which of the two depends on where the project is, and the caller does not
choose. In draft it is added outright - the DPO reviews the whole project at
approval, so asking separately would be the same question twice. Once the
project is approved, or while it is being reviewed, it is a request: the
processor goes on the list marked pending and nothing may collect under it
until the DPO answers.

The R&D User alone, because naming the collectors is the initiator's
decision - the study is theirs and the partners are the ones they arranged.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProcessorRequestIn`](#schema-processorrequestin)

```json
{
  "processor_uuid": "00000000-0000-4000-8000-000000000000"
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

<a id="13_put_projects_project_uuid_processors"></a>
## 13. `PUT /projects/{project_uuid}/processors` — Draft only — replaces the set

### API

- **Operation ID:** `set_project_processors_projects__project_uuid__processors_put`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Change who will collect, while the project is still in draft.

The R&D User alone, and their own projects alone - row scope sees to the
second half. Naming the collectors is the initiator's decision because it is
the one they are answerable for: the study is theirs, and the partners are
the ones they arranged. A DPO who disagreed with the choice returns the
project to draft and says so, which leaves a record; editing it silently
would not.

Nobody may after approval: the processors are what the DPO reviewed and what
the routing was decided from, so changing them would re-point an approved
project at a collector nobody approved.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProcessorsIn`](#schema-processorsin)

```json
{
  "processor_uuids": [
    "00000000-0000-4000-8000-000000000000"
  ]
}
```

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

<a id="14_post_projects_project_uuid_processors_processor_uuid_decision"></a>
## 14. `POST /projects/{project_uuid}/processors/{processor_uuid}/decision` — Decide Project Processor

### API

- **Operation ID:** `decide_project_processor_projects__project_uuid__processors__processor_uuid__decision_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Approve or refuse a collector proposed for an approved project.

One endpoint with a decision rather than two verbs, because a refusal
carries a reason and an approval does not - and a pair of routes where only
one takes a body invites the reason being posted to the wrong one.

Approving does not move the project. It makes the processor real, and the
work then appears where it belongs: a third party's on the DCO Admin's
queue, an in-house one back with the R&D owner. Nothing about the project
changed - something was added to it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |
| `processor_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`ProcessorDecisionIn`](#schema-processordecisionin)

```json
{
  "approved": true,
  "reason": "string"
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

<a id="15_post_projects_project_uuid_close"></a>
## 15. `POST /projects/{project_uuid}/close` — Close Project

### API

- **Operation ID:** `close_project_projects__project_uuid__close_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`TransitionRequest`](#schema-transitionrequest)

```json
{
  "to": "string",
  "reason": "string"
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

<a id="16_get_projects_project_uuid_approvals"></a>
## 16. `GET /projects/{project_uuid}/approvals` — List Approvals

### API

- **Operation ID:** `list_approvals_projects__project_uuid__approvals_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="17_post_projects_project_uuid_approvals"></a>
## 17. `POST /projects/{project_uuid}/approvals` — Upload an approval - proof is mandatory (INV-8)

### API

- **Operation ID:** `add_approval_projects__project_uuid__approvals_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `multipart/form-data`  
**Schema:** [`Body_add_approval_projects__project_uuid__approvals_post`](#schema-body_add_approval_projects_project_uuid_approvals_post)

```json
{
  "approval_type": "string",
  "reference_no": "string",
  "approved_on": "2026-09-17",
  "proof": "string"
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

<a id="18_get_approvals_approval_uuid"></a>
## 18. `GET /approvals/{approval_uuid}` — Get Approval

### API

- **Operation ID:** `get_approval_approvals__approval_uuid__get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `approval_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="19_get_approvals_approval_uuid_proof"></a>
## 19. `GET /approvals/{approval_uuid}/proof` — Download the proof file

### API

- **Operation ID:** `download_proof_approvals__approval_uuid__proof_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `approval_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="20_get_projects_project_uuid_sites"></a>
## 20. `GET /projects/{project_uuid}/sites` — List Sites

### API

- **Operation ID:** `list_sites_projects__project_uuid__sites_get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="21_post_projects_project_uuid_sites"></a>
## 21. `POST /projects/{project_uuid}/sites` — Add Site

### API

- **Operation ID:** `add_site_projects__project_uuid__sites_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Register where collection will physically happen.

The R&D User is included because they are the one who knows: they designed
the study, they know which lab or clinic is running it, and which processor
operates it. Leaving this to the DPO meant the DPO inventing a site to get
past their own publication screen.

The DCO Admin and the RCO are included because registering the site is the
first half of the job they exist to do. Routing an approved project means
saying where collection happens and what stands there, and a role that could
attach a source but not create the site it attaches to would be able to
finish the work only if somebody else had started it.

What it takes is a data source, chosen from those registered under the
project's processors - not a name typed by hand. A site is where one of
those sources stands.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SiteIn`](#schema-sitein)

```json
{
  "source_uuid": "00000000-0000-4000-8000-000000000000",
  "location": "string"
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

<a id="22_get_sites_site_uuid"></a>
## 22. `GET /sites/{site_uuid}` — Get Site

### API

- **Operation ID:** `get_site_sites__site_uuid__get`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="23_put_sites_site_uuid"></a>
## 23. `PUT /sites/{site_uuid}` — Update Site

### API

- **Operation ID:** `update_site_sites__site_uuid__put`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SiteUpdate`](#schema-siteupdate)

```json
{
  "site_label": "string",
  "location": "string"
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

<a id="24_put_sites_site_uuid_source"></a>
## 24. `PUT /sites/{site_uuid}/source` — Attach the data source that stands here

### API

- **Operation ID:** `assign_site_source_sites__site_uuid__source_put`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Attach a data source to a site. The project follows.

This is the routing step, and it is deliberately not a way to name a person.
A source carries its own owner, so choosing CIT for a site is choosing
whoever runs CIT - the two cannot disagree, because there is only one of
them. `trg_site_owner` re-derives `project.dco_user_id` from the primary
site on commit, and the project appears in that owner's list.

Who may call it follows the same split as the routing itself:

* a **DCO Admin** on a project collected by a third party - that queue is
  their job;
* the **R&D owner** on one collected in-house, which is where an approved
  project goes back to them to name the sources and an RCO;
* a **DPO** or **administrator** anywhere, for correction.

A DCO is not on that list. Reassigning their own sites would let them hand
themselves somebody else's project, or drop one they no longer want.

The response reports the routing consequence rather than leaving the caller
to infer it: `project_moved` is true when this changed who owns the project,
which is the fact somebody needs to see before they close the dialog.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SiteSourceAssign`](#schema-sitesourceassign)

```json
{
  "source_uuid": "00000000-0000-4000-8000-000000000000"
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

<a id="25_put_sites_site_uuid_owner"></a>
## 25. `PUT /sites/{site_uuid}/owner` — Name who runs this site, overriding its source

### API

- **Operation ID:** `assign_site_owner_sites__site_uuid__owner_put`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

Override the owner a site inherits from its data source.

Attaching a source picks the owner automatically and that is right almost
every time. This is the exception: cover, a handover, a partner who insists
on a named contact. Several sites on one project can each name a different
person.

**It does not move the source.** The rig keeps its owner and every other
project collecting from it is untouched — which is the whole reason this is
a separate operation rather than a shortcut into `PUT /sources/{uuid}/owner`.
That endpoint moves everybody; this one moves one site.

Who may call it follows the routing: a **DCO Admin** on third-party
collection, the **R&D owner** on in-house, and a **DPO** or **administrator**
anywhere. A DCO is absent for the same reason as everywhere else — naming
themselves on somebody else's site is exactly what this must not enable.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`SiteOwnerAssign`](#schema-siteownerassign)

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

<a id="26_post_sites_site_uuid_deactivate"></a>
## 26. `POST /sites/{site_uuid}/deactivate` — Deactivate Site

### API

- **Operation ID:** `deactivate_site_sites__site_uuid__deactivate_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="27_post_sites_site_uuid_agent"></a>
## 27. `POST /sites/{site_uuid}/agent` — Assign the Field Agent and mint the link

### API

- **Operation ID:** `assign_agent_sites__site_uuid__agent_post`
- **Access:** Role-controlled `projects` operation. See [`../../roles/README.md`](../../roles/README.md).

`expires_at` is required - no default and no maximum.

The absence of a pre-fill is the control. Somebody has to decide how long
this link should live; a default would be chosen once and never revisited.

The token is returned exactly once. What the database holds is its keyed
digest, so this response is the only opportunity to capture it.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `site_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

Request body required: **yes**.

**Content type:** `application/json`  
**Schema:** [`AgentAssign`](#schema-agentassign)

```json
{
  "expires_at": "2026-09-17T12:00:00Z",
  "max_uses": 1.0,
  "agent_ref": "string"
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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-agentassign"></a>
#### `AgentAssign`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `expires_at` | `string` | Yes | format: `date-time` | — |
| `max_uses` | `integer` or `null` | No | minimum: `1.0`; maximum: `100000.0` | — |
| `agent_ref` | `string` or `null` | No | max length: `120` | — |

<a id="schema-body_add_approval_projects_project_uuid_approvals_post"></a>
#### `Body_add_approval_projects__project_uuid__approvals_post`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `approval_type` | `string` | Yes | — | — |
| `reference_no` | `string` | Yes | max length: `120` | — |
| `approved_on` | `string` | Yes | format: `date` | — |
| `proof` | `string` | Yes | — | PDF or image, max 25 MB |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-page_approvallistrow"></a>
#### `Page_ApprovalListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ApprovalListRow`](#schema-approvallistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_projectout"></a>
#### `Page_ProjectOut_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ProjectOut`](#schema-projectout) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_sitelistrow"></a>
#### `Page_SiteListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`SiteListRow`](#schema-sitelistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-processordecisionin"></a>
#### `ProcessorDecisionIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `approved` | `boolean` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-processorrequestin"></a>
#### `ProcessorRequestIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processor_uuid` | `string` | Yes | format: `uuid` | — |

<a id="schema-processorsin"></a>
#### `ProcessorsIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `processor_uuids` | array of `string` | Yes | — | — |

<a id="schema-projectin"></a>
#### `ProjectIn`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `project_name` | `string` | Yes | min length: `1`; max length: `200` | — |
| `description` | `string` | Yes | min length: `1`; max length: `20000` | — |
| `processor_uuids` | array of `string` | Yes | — | — |
| `internal_project_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `requesting_team` | `string` or `null` | No | max length: `120` | — |

<a id="schema-projectout"></a>
#### `ProjectOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `internal_project_name` | `string` or `null` | Yes | — | — |
| `description` | `string` or `null` | Yes | — | — |
| `requesting_team` | `string` or `null` | Yes | — | — |
| `project_status` | `string` | Yes | — | — |
| `dco_uuid` | `string` or `null` | No | format: `uuid` | — |
| `dco_name` | `string` or `null` | No | — | — |
| `created_by_name` | `string` or `null` | No | — | — |
| `current_notice_uuid` | `string` or `null` | No | format: `uuid` | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `updated_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-projectupdate"></a>
#### `ProjectUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `project_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `description` | `string` or `null` | No | min length: `1`; max length: `20000` | — |
| `internal_project_name` | `string` or `null` | No | min length: `1`; max length: `200` | — |
| `requesting_team` | `string` or `null` | No | max length: `120` | — |

<a id="schema-sitein"></a>
#### `SiteIn`

A collection site is the deployment of one data source on one project.

That is why the data source is the only required field. It decides the
processor (a source belongs to one), the label (a site has no name of its
own - it *is* that source, standing somewhere), and who is accountable (the
source carries its owner). Asking for those separately invited them to
disagree with each other, and a site whose label said one thing while its
source said another had two answers to one question.

The source has to be one of the project's own processors'. Anything else
would mean collecting through an organisation the DPO did not review.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source_uuid` | `string` | Yes | format: `uuid` | — |
| `location` | `string` or `null` | No | max length: `200` | — |

<a id="schema-siteownerassign"></a>
#### `SiteOwnerAssign`

Who runs this site on this project, when it is not the source's owner.

`null` clears the exception and the site goes back to whoever owns its data
source — the usual way an override ends, because it was cover and the cover
finished.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `owner_user_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-sitesourceassign"></a>
#### `SiteSourceAssign`

Which data source stands at this site.

`null` detaches, which is a real operation: a site between sources is
honestly unassigned, and leaving the previous one attached would say
collection is happening somewhere it is not.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `source_uuid` | `string` or `null` | No | format: `uuid` | — |

<a id="schema-siteupdate"></a>
#### `SiteUpdate`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `site_label` | `string` or `null` | No | max length: `160` | — |
| `location` | `string` or `null` | No | max length: `200` | — |

<a id="schema-transitionrequest"></a>
#### `TransitionRequest`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `to` | `string` | Yes | — | — |
| `reason` | `string` or `null` | No | max length: `1000` | — |

<a id="schema-cmp_api_routers_v1_projects_transitionsout"></a>
#### `cmp__api__routers__v1__projects__TransitionsOut`

Declared rather than returned as a bare dict so the API reference says
what this endpoint sends. It is the one the console draws its only forward
control from, and it was documented as `{}`.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `current` | `string` | Yes | — | — |
| `available` | array of [`TransitionOptionOut`](#schema-transitionoptionout) | Yes | — | — |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-approvallistrow"></a>
#### `ApprovalListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `approval_uuid` | `string` | Yes | format: `uuid` | — |
| `approval_type` | `string` | Yes | — | — |
| `reference_no` | `string` | Yes | — | — |
| `approved_on` | `string` | Yes | format: `date` | — |
| `proof_file_hash` | `string` | Yes | — | — |
| `uploaded_at` | `string` | Yes | format: `date-time` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `project_status` | `string` | Yes | — | — |
| `uploaded_by_uuid` | `string` | Yes | format: `uuid` | — |
| `uploaded_by_name` | `string` | Yes | — | — |

<a id="schema-sitelistrow"></a>
#### `SiteListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `location` | `string` or `null` | No | — | — |
| `status` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `project_status` | `string` | Yes | — | — |
| `processor_uuid` | `string` or `null` | No | format: `uuid` | — |
| `processor_name` | `string` or `null` | No | — | — |
| `active_links` | `integer` | Yes | — | — |

<a id="schema-transitionoptionout"></a>
#### `TransitionOptionOut`

One move out of this project's state, and why it cannot be made.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `to` | `string` | Yes | — | — |
| `allowed` | `boolean` | Yes | — | — |
| `blocked_by` | `string` or `null` | No | — | — |
| `blockers` | array of `string` | No | — | — |
| `reason_required` | `boolean` | No | default: `False` | — |
| `publishes_notice` | `boolean` | No | default: `False` | — |
