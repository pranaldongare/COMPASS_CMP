# Administrator (`admin`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `users`, `messages`, `processors`, `sources`, `requests`, `audit`, `delegate`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | No | No | `none` | Denied |
| `asset` | No | No | `none` | Denied |
| `audit` | Yes | No | `all` | All rows |
| `collection` | No | No | `none` | Denied |
| `consent` | No | No | `none` | Denied |
| `data_source` | Yes | Yes | `all` | All rows |
| `export` | No | No | `none` | Denied |
| `import` | No | No | `none` | Denied |
| `link` | No | No | `none` | Denied |
| `me` | No | No | `none` | Denied |
| `message_template` | Yes | Yes | `all` | All rows |
| `notice` | No | No | `none` | Denied |
| `processor` | Yes | Yes | `all` | All rows |
| `project` | No | No | `none` | Denied |
| `purpose` | Yes | No | `all` | All rows |
| `rights_request` | Yes | Yes | `scoped` | Assigned project/organisational rows |
| `site` | No | No | `none` | Denied |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | Yes | Yes | `all` | All rows |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
