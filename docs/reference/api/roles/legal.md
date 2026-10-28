# Legal PoC (`legal`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `hr-categories`, `templates`, `purposes`, `processors`, `users`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | No | No | `none` | Denied |
| `asset` | No | No | `none` | Denied |
| `audit` | No | No | `none` | Denied |
| `breach` | No | No | `none` | Denied |
| `breach_ticket` | Yes | Yes | `own` | Own or addressed rows |
| `collection` | No | No | `none` | Denied |
| `consent` | No | No | `none` | Denied |
| `data_source` | No | No | `none` | Denied |
| `export` | No | No | `none` | Denied |
| `hr_category` | Yes | Yes | `all` | All rows |
| `import` | No | No | `none` | Denied |
| `legal_hold` | No | No | `none` | Denied |
| `link` | No | No | `none` | Denied |
| `me` | No | No | `none` | Denied |
| `message_template` | No | No | `none` | Denied |
| `notice` | No | No | `none` | Denied |
| `notice_template` | Yes | Yes | `all` | All rows |
| `processor` | Yes | No | `all` | All rows |
| `project` | No | No | `none` | Denied |
| `purpose` | Yes | Yes | `all` | All rows |
| `restricted_country` | No | No | `none` | Denied |
| `rights_request` | No | No | `none` | Denied |
| `site` | No | No | `none` | Denied |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | Yes | No | `all` | All rows |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
