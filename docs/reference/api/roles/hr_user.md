# HR PoC (`hr_user`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `hr-activities`, `hr-categories`, `links`, `consents`, `exports`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | No | No | `none` | Denied |
| `asset` | No | No | `none` | Denied |
| `audit` | No | No | `none` | Denied |
| `breach` | No | No | `none` | Denied |
| `breach_ticket` | Yes | Yes | `own` | Own or addressed rows |
| `collection` | No | No | `none` | Denied |
| `consent` | Yes | No | `scoped` | Assigned project/organisational rows |
| `data_source` | No | No | `none` | Denied |
| `export` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `hr_category` | Yes | No | `scoped` | Assigned project/organisational rows |
| `import` | No | No | `none` | Denied |
| `legal_hold` | No | No | `none` | Denied |
| `link` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `me` | No | No | `none` | Denied |
| `message_template` | No | No | `none` | Denied |
| `notice` | Yes | No | `scoped` | Assigned project/organisational rows |
| `notice_template` | No | No | `none` | Denied |
| `processor` | No | No | `none` | Denied |
| `project` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `purpose` | No | No | `none` | Denied |
| `restricted_country` | No | No | `none` | Denied |
| `rights_request` | No | No | `none` | Denied |
| `site` | Yes | No | `scoped` | Assigned project/organisational rows |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | No | No | `none` | Denied |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
