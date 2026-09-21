# R&D User (`rnd_user`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `projects`, `notices`, `processors`, `approvals`, `imports`, `collections`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | Yes | Yes | `own` | Own or addressed rows |
| `asset` | Yes | No | `own` | Own or addressed rows |
| `audit` | No | No | `none` | Denied |
| `collection` | Yes | No | `own` | Own or addressed rows |
| `consent` | Yes | No | `own` | Own or addressed rows |
| `data_source` | Yes | No | `all` | All rows |
| `export` | No | No | `none` | Denied |
| `import` | Yes | No | `own` | Own or addressed rows |
| `link` | No | No | `none` | Denied |
| `me` | No | No | `none` | Denied |
| `message_template` | No | No | `none` | Denied |
| `notice` | Yes | Yes | `own` | Own or addressed rows |
| `processor` | Yes | No | `all` | All rows |
| `project` | Yes | Yes | `own` | Own or addressed rows |
| `purpose` | Yes | No | `all` | All rows |
| `rights_request` | No | No | `none` | Denied |
| `site` | Yes | No | `own` | Own or addressed rows |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | No | No | `none` | Denied |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
