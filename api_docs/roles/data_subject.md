# Data Subject (`data_subject`)

## What this role can do

Navigation returned after sign-in: `consents`, `requests`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | No | No | `none` | Denied |
| `asset` | No | No | `none` | Denied |
| `audit` | No | No | `none` | Denied |
| `collection` | No | No | `none` | Denied |
| `consent` | No | No | `none` | Denied |
| `data_source` | No | No | `none` | Denied |
| `export` | No | No | `none` | Denied |
| `import` | No | No | `none` | Denied |
| `link` | No | No | `none` | Denied |
| `me` | Yes | Yes | `own` | Own or addressed rows |
| `message_template` | No | No | `none` | Denied |
| `notice` | No | No | `none` | Denied |
| `processor` | No | No | `none` | Denied |
| `project` | No | No | `none` | Denied |
| `purpose` | No | No | `none` | Denied |
| `rights_request` | No | No | `none` | Denied |
| `site` | No | No | `none` | Denied |
| `ticket` | No | No | `none` | Denied |
| `user` | No | No | `none` | Denied |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
