# Consent API

Generated from `cmp_backend/openapi.json`. **12 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /links`](#1_get_links)
2. [`GET /consents`](#2_get_consents)
3. [`GET /projects/{project_uuid}/links`](#3_get_projects_project_uuid_links)
4. [`GET /links/{link_uuid}`](#4_get_links_link_uuid)
5. [`GET /links/{link_uuid}/stats`](#5_get_links_link_uuid_stats)
6. [`POST /links/{link_uuid}/remint`](#6_post_links_link_uuid_remint)
7. [`POST /links/{link_uuid}/revoke`](#7_post_links_link_uuid_revoke)
8. [`GET /projects/{project_uuid}/consents`](#8_get_projects_project_uuid_consents)
9. [`GET /projects/{project_uuid}/consents/summary`](#9_get_projects_project_uuid_consents_summary)
10. [`GET /consents/{consent_uuid}`](#10_get_consents_consent_uuid)
11. [`GET /consents/{consent_uuid}/grants`](#11_get_consents_consent_uuid_grants)
12. [`GET /consents/{consent_uuid}/assets`](#12_get_consents_consent_uuid_assets)

<a id="1_get_links"></a>
## 1. `GET /links` — All links in scope

### API

- **Operation ID:** `list_all_links_links_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

Every consent link in scope, with its registration count.

Registrations are the number that matters operationally: it counts everyone
who came through the link, including anyone who registered and abandoned
before consenting, who leaves no artefact to trace.

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
| `200` | Successful Response | `application/json` | [`Page_LinkListRow_`](#schema-page_linklistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "link_uuid": "00000000-0000-4000-8000-000000000000",
      "expires_at": "2026-09-17T12:00:00Z",
      "max_uses": "…",
      "use_count": 1,
      "status": "string",
      "created_at": "2026-09-17T12:00:00Z",
      "revoked_at": "…",
      "site_uuid": "00000000-0000-4000-8000-000000000000",
      "site_label": "string",
      "notice_uuid": "00000000-0000-4000-8000-000000000000",
      "notice_code": "string",
      "version": 1,
      "url_path": "…",
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string",
      "registrations": 1
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

<a id="2_get_consents"></a>
## 2. `GET /consents` — All consents in scope

### API

- **Operation ID:** `list_all_consents_consents_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

Every current consent in scope. Status is derived, never stored.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `status` | query | No | `string` or `null` | — | — |
| `project` | query | No | `string` or `null` | format: `uuid` | — |
| `limit` | query | No | `integer` or `null` | minimum: `1`; maximum: `200` | — |
| `cursor` | query | No | `string` or `null` | max length: `512` | — |
| `sort` | query | No | `string` or `null` | max length: `64` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`Page_ConsentListRow_`](#schema-page_consentlistrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "consent_uuid": "00000000-0000-4000-8000-000000000000",
      "subject_uuid": "00000000-0000-4000-8000-000000000000",
      "subject_name": "string",
      "subject_email": "…",
      "subject_mobile": "…",
      "site_uuid": "00000000-0000-4000-8000-000000000000",
      "site_label": "string",
      "served_at": "2026-09-17T12:00:00Z",
      "affirmative_action_at": "2026-09-17T12:00:00Z",
      "action_type": "string",
      "is_withdrawal": true,
      "consent_status": "string",
      "granted_count": 1,
      "refused_count": 1,
      "project_uuid": "00000000-0000-4000-8000-000000000000",
      "project_name": "string"
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

<a id="3_get_projects_project_uuid_links"></a>
## 3. `GET /projects/{project_uuid}/links` — List Links

### API

- **Operation ID:** `list_links_projects__project_uuid__links_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`LinkOut`](#schema-linkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "link_uuid": "00000000-0000-4000-8000-000000000000",
    "expires_at": "2026-09-17T12:00:00Z",
    "max_uses": 1,
    "use_count": 1,
    "status": "string",
    "created_at": "2026-09-17T12:00:00Z",
    "revoked_at": "2026-09-17T12:00:00Z",
    "site_uuid": "00000000-0000-4000-8000-000000000000",
    "site_label": "string",
    "notice_uuid": "00000000-0000-4000-8000-000000000000",
    "notice_code": "string",
    "version": 1,
    "url_path": "string"
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

<a id="4_get_links_link_uuid"></a>
## 4. `GET /links/{link_uuid}` — Get Link

### API

- **Operation ID:** `get_link_links__link_uuid__get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `link_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`LinkOut`](#schema-linkout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "link_uuid": "00000000-0000-4000-8000-000000000000",
  "expires_at": "2026-09-17T12:00:00Z",
  "max_uses": 1,
  "use_count": 1,
  "status": "string",
  "created_at": "2026-09-17T12:00:00Z",
  "revoked_at": "2026-09-17T12:00:00Z",
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "site_label": "string",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "url_path": "string"
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

<a id="5_get_links_link_uuid_stats"></a>
## 5. `GET /links/{link_uuid}/stats` — Link Stats

### API

- **Operation ID:** `link_stats_links__link_uuid__stats_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

Opens, registrations, consents, declines and the remaining use cap.

Registrations counts everyone who came through the link - including anyone
who registered and abandoned before consenting, who leaves no artefact to
trace. If a link circulates beyond its intended population, that gap is the
first sign.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `link_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`LinkStats`](#schema-linkstats) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "use_count": 1,
  "max_uses": 1,
  "uses_remaining": 1,
  "registrations": 1,
  "consents": 1,
  "withdrawals": 1,
  "declines": 1
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

<a id="6_post_links_link_uuid_remint"></a>
## 6. `POST /links/{link_uuid}/remint` — Replace a link with a fresh one

### API

- **Operation ID:** `remint_link_links__link_uuid__remint_post`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

Revoke this link and mint a replacement for the same site.

This predates 0011, when the token genuinely could not be shown twice: the
database held only a keyed digest, and a link whose URL was lost at mint time
was unrecoverable. Links minted since are sealed as well as digested, so the
URL can be read back from the register - but replacing a link is still the
right move when one has leaked rather than been lost, and for the links
minted before sealing existed.

Both halves happen in one transaction. A revoke that succeeded without its
replacement would leave a site with no way to collect and somebody wondering
why; a mint without the revoke would leave two live links for one site, and
the older one is exactly the one nobody is tracking.

The old link stays in the register as `revoked`, with its use count. That is
the point of replacing rather than editing: the consents gathered through it
still point at it, and the record still says when it stopped working.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `link_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="7_post_links_link_uuid_revoke"></a>
## 7. `POST /links/{link_uuid}/revoke` — Revoke Link

### API

- **Operation ID:** `revoke_link_links__link_uuid__revoke_post`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `link_uuid` | path | Yes | `string` | format: `uuid` | — |

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

<a id="8_get_projects_project_uuid_consents"></a>
## 8. `GET /projects/{project_uuid}/consents` — List Consents

### API

- **Operation ID:** `list_consents_projects__project_uuid__consents_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `project_uuid` | path | Yes | `string` | format: `uuid` | — |
| `site` | query | No | `string` or `null` | format: `uuid` | — |
| `status` | query | No | `string` or `null` | — | — |
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
| `200` | Successful Response | `application/json` | [`Page_ConsentRow_`](#schema-page_consentrow) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "items": [
    {
      "consent_uuid": "00000000-0000-4000-8000-000000000000",
      "subject_uuid": "00000000-0000-4000-8000-000000000000",
      "subject_name": "string",
      "subject_email": "…",
      "subject_mobile": "…",
      "site_uuid": "00000000-0000-4000-8000-000000000000",
      "site_label": "string",
      "served_at": "2026-09-17T12:00:00Z",
      "affirmative_action_at": "2026-09-17T12:00:00Z",
      "action_type": "string",
      "is_withdrawal": true,
      "consent_status": "string",
      "granted_count": 1,
      "refused_count": 1
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

<a id="9_get_projects_project_uuid_consents_summary"></a>
## 9. `GET /projects/{project_uuid}/consents/summary` — Consents Summary

### API

- **Operation ID:** `consents_summary_projects__project_uuid__consents_summary_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

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

<a id="10_get_consents_consent_uuid"></a>
## 10. `GET /consents/{consent_uuid}` — Get Consent

### API

- **Operation ID:** `get_consent_consents__consent_uuid__get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | [`ConsentArtefactOut`](#schema-consentartefactout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
{
  "consent_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_uuid": "00000000-0000-4000-8000-000000000000",
  "subject_name": "string",
  "subject_email": "string",
  "subject_mobile": "string",
  "project_uuid": "00000000-0000-4000-8000-000000000000",
  "project_name": "string",
  "site_uuid": "00000000-0000-4000-8000-000000000000",
  "site_label": "string",
  "notice_uuid": "00000000-0000-4000-8000-000000000000",
  "notice_code": "string",
  "version": 1,
  "language_code": "string",
  "notice_content_hash": "string",
  "served_at": "2026-09-17T12:00:00Z",
  "affirmative_action_at": "2026-09-17T12:00:00Z",
  "action_type": "string",
  "is_withdrawal": true,
  "created_at": "2026-09-17T12:00:00Z"
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

<a id="11_get_consents_consent_uuid_grants"></a>
## 11. `GET /consents/{consent_uuid}/grants` — Consent Grants

### API

- **Operation ID:** `consent_grants_consents__consent_uuid__grants_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`GrantOut`](#schema-grantout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "purpose_uuid": "00000000-0000-4000-8000-000000000000",
    "purpose_code": "string",
    "name": "string",
    "description": "string",
    "uses": "string",
    "lawful_basis": "string",
    "data_categories": [
      "string"
    ],
    "retention_period": "string",
    "granted": true
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

<a id="12_get_consents_consent_uuid_assets"></a>
## 12. `GET /consents/{consent_uuid}/assets` — Which assets contain this person

### API

- **Operation ID:** `consent_assets_consents__consent_uuid__assets_get`
- **Access:** Role-controlled `consent` operation. See [`../../roles/README.md`](../../roles/README.md).

The reverse lookup an erasure request depends on.

It is the reason `asset_consent` exists: without it, "delete everything of
mine" has no way to find the frames she appears in.

### Validation

| Parameter | Location | Required | Type | Constraints | Description |
|---|---|---:|---|---|---|
| `consent_uuid` | path | Yes | `string` | format: `uuid` | — |

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`ConsentAssetOut`](#schema-consentassetout) |
| `422` | Validation Error | `application/json` | [`HTTPValidationError`](#schema-httpvalidationerror) |

**Example `200` `application/json` response:**

```json
[
  {
    "asset_uuid": "00000000-0000-4000-8000-000000000000",
    "asset_type": "string",
    "source_asset_ref": "string",
    "storage_ref": "string",
    "has_unmapped_subjects": true,
    "created_at": "2026-09-17T12:00:00Z",
    "subject_role": "string",
    "disposition": "string",
    "disposition_at": "2026-09-17T12:00:00Z",
    "collection_uuid": "00000000-0000-4000-8000-000000000000",
    "collected_on": "2026-09-17",
    "source_code": "string",
    "source_name": "string",
    "project_uuid": "00000000-0000-4000-8000-000000000000",
    "project_name": "string"
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

# Referenced schemas

<a id="schema-acknowledged"></a>
#### `Acknowledged`

For state changes whose only interesting output is that they happened.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `ok` | `boolean` | No | default: `True` | — |
| `message` | `string` or `null` | No | — | — |

<a id="schema-consentartefactout"></a>
#### `ConsentArtefactOut`

One consent record, in full.

Declared rather than returned as a bare dict so `consent_id` - the internal
surrogate key the scoped query needs for its follow-up lookups - cannot ship
to a client. An integer primary key in a response body is an invitation to
enumerate, and it becomes an accidental part of the contract the moment
somebody reads it off the wire.

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `consent_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_name` | `string` | Yes | — | — |
| `subject_email` | `string` or `null` | Yes | — | — |
| `subject_mobile` | `string` or `null` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `language_code` | `string` | Yes | — | — |
| `notice_content_hash` | `string` | Yes | — | — |
| `served_at` | `string` | Yes | format: `date-time` | — |
| `affirmative_action_at` | `string` | Yes | format: `date-time` | — |
| `action_type` | `string` | Yes | — | — |
| `is_withdrawal` | `boolean` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |

<a id="schema-httpvalidationerror"></a>
#### `HTTPValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `detail` | array of [`ValidationError`](#schema-validationerror) | No | — | — |

<a id="schema-linkout"></a>
#### `LinkOut`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `link_uuid` | `string` | Yes | format: `uuid` | — |
| `expires_at` | `string` | Yes | format: `date-time` | — |
| `max_uses` | `integer` or `null` | Yes | — | — |
| `use_count` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `revoked_at` | `string` or `null` | No | format: `date-time` | — |
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `url_path` | `string` or `null` | No | — | — |

<a id="schema-linkstats"></a>
#### `LinkStats`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `use_count` | `integer` | Yes | — | — |
| `max_uses` | `integer` or `null` | Yes | — | — |
| `uses_remaining` | `integer` or `null` | Yes | — | — |
| `registrations` | `integer` | Yes | — | — |
| `consents` | `integer` | Yes | — | — |
| `withdrawals` | `integer` | Yes | — | — |
| `declines` | `integer` | Yes | — | — |

<a id="schema-page_consentlistrow"></a>
#### `Page_ConsentListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ConsentListRow`](#schema-consentlistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_consentrow"></a>
#### `Page_ConsentRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`ConsentRow`](#schema-consentrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-page_linklistrow"></a>
#### `Page_LinkListRow_`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `items` | array of [`LinkListRow`](#schema-linklistrow) | Yes | — | — |
| `next_cursor` | `string` or `null` | No | — | Opaque. Pass back as ?cursor= for the next page. |
| `total` | `integer` or `null` | No | — | Total matching rows where it is cheap to know. Null means not counted. |

<a id="schema-validationerror"></a>
#### `ValidationError`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `loc` | array of `string` or `integer` | Yes | — | — |
| `msg` | `string` | Yes | — | — |
| `type` | `string` | Yes | — | — |
| `input` | `object` | No | — | — |
| `ctx` | `object` | No | — | — |

<a id="schema-consentlistrow"></a>
#### `ConsentListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `consent_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_name` | `string` | Yes | — | — |
| `subject_email` | `string` or `null` | Yes | — | — |
| `subject_mobile` | `string` or `null` | Yes | — | — |
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `served_at` | `string` | Yes | format: `date-time` | — |
| `affirmative_action_at` | `string` | Yes | format: `date-time` | — |
| `action_type` | `string` | Yes | — | — |
| `is_withdrawal` | `boolean` | Yes | — | — |
| `consent_status` | `string` | Yes | — | — |
| `granted_count` | `integer` | Yes | — | — |
| `refused_count` | `integer` | Yes | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |

<a id="schema-consentrow"></a>
#### `ConsentRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `consent_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_uuid` | `string` | Yes | format: `uuid` | — |
| `subject_name` | `string` | Yes | — | — |
| `subject_email` | `string` or `null` | Yes | — | — |
| `subject_mobile` | `string` or `null` | Yes | — | — |
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `served_at` | `string` | Yes | format: `date-time` | — |
| `affirmative_action_at` | `string` | Yes | format: `date-time` | — |
| `action_type` | `string` | Yes | — | — |
| `is_withdrawal` | `boolean` | Yes | — | — |
| `consent_status` | `string` | Yes | — | — |
| `granted_count` | `integer` | Yes | — | — |
| `refused_count` | `integer` | Yes | — | — |

<a id="schema-linklistrow"></a>
#### `LinkListRow`

| Field | Type | Required | Validation | Description |
|---|---|---:|---|---|
| `link_uuid` | `string` | Yes | format: `uuid` | — |
| `expires_at` | `string` | Yes | format: `date-time` | — |
| `max_uses` | `integer` or `null` | Yes | — | — |
| `use_count` | `integer` | Yes | — | — |
| `status` | `string` | Yes | — | — |
| `created_at` | `string` | Yes | format: `date-time` | — |
| `revoked_at` | `string` or `null` | No | format: `date-time` | — |
| `site_uuid` | `string` | Yes | format: `uuid` | — |
| `site_label` | `string` | Yes | — | — |
| `notice_uuid` | `string` | Yes | format: `uuid` | — |
| `notice_code` | `string` | Yes | — | — |
| `version` | `integer` | Yes | — | — |
| `url_path` | `string` or `null` | No | — | — |
| `project_uuid` | `string` | Yes | format: `uuid` | — |
| `project_name` | `string` | Yes | — | — |
| `registrations` | `integer` | Yes | — | — |
