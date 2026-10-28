# Legal PoC (`legal`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `requests`, `breaches`, `hr-activities`, `hr-categories`, `templates`, `purposes`, `consents`, `exports`, `processors`, `users`, `audit`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | No | No | `none` | Denied |
| `asset` | No | No | `none` | Denied |
| `audit` | Yes | No | `all` | All rows |
| `breach` | Yes | Yes | `all` | All rows |
| `breach_ticket` | Yes | Yes | `own` | Own or addressed rows |
| `collection` | No | No | `none` | Denied |
| `consent` | Yes | No | `all` | All rows |
| `data_source` | No | No | `none` | Denied |
| `export` | Yes | Yes | `all` | All rows |
| `hr_category` | Yes | Yes | `all` | All rows |
| `import` | No | No | `none` | Denied |
| `legal_hold` | Yes | Yes | `all` | All rows |
| `link` | Yes | No | `all` | All rows |
| `me` | No | No | `none` | Denied |
| `message_template` | No | No | `none` | Denied |
| `notice` | Yes | No | `all` | All rows |
| `notice_template` | Yes | Yes | `all` | All rows |
| `processor` | Yes | No | `all` | All rows |
| `project` | Yes | No | `all` | All rows |
| `purpose` | Yes | Yes | `all` | All rows |
| `restricted_country` | No | No | `none` | Denied |
| `rights_request` | Yes | Yes | `all` | All rows |
| `site` | Yes | No | `all` | All rows |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | Yes | No | `all` | All rows |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
