# Research Collection Owner (`rco`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `projects`, `sites`, `sources`, `links`, `consents`, `exports`, `imports`, `collections`, `delegate`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | Yes | No | `scoped` | Assigned project/organisational rows |
| `asset` | Yes | No | `scoped` | Assigned project/organisational rows |
| `audit` | No | No | `none` | Denied |
| `collection` | Yes | No | `scoped` | Assigned project/organisational rows |
| `consent` | Yes | No | `scoped` | Assigned project/organisational rows |
| `data_source` | Yes | Yes | `all` | All rows |
| `export` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `import` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `legal_hold` | No | No | `none` | Denied |
| `link` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `me` | No | No | `none` | Denied |
| `message_template` | No | No | `none` | Denied |
| `notice` | Yes | No | `scoped` | Assigned project/organisational rows |
| `processor` | Yes | No | `all` | All rows |
| `project` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `purpose` | Yes | No | `all` | All rows |
| `restricted_country` | No | No | `none` | Denied |
| `rights_request` | No | No | `none` | Denied |
| `site` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | No | No | `none` | Denied |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
