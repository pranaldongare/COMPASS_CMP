# Data Protection Officer (`dpo`)

## What this role can do

Navigation returned after sign-in: `dashboard`, `projects`, `approvals`, `notices`, `purposes`, `sites`, `collections`, `processors`, `sources`, `consents`, `links`, `exports`, `imports`, `requests`, `audit`, `users`, `messages`, `delegate`, `tickets`, `notifications`, `profile`.

## Resource access

| Resource | Read | Write | Scope | What the scope means |
|---|---:|---:|---|---|
| `approval` | Yes | No | `all` | All rows |
| `asset` | Yes | No | `all` | All rows |
| `audit` | Yes | No | `all` | All rows |
| `collection` | Yes | No | `all` | All rows |
| `consent` | Yes | No | `all` | All rows |
| `data_source` | Yes | Yes | `all` | All rows |
| `export` | Yes | Yes | `all` | All rows |
| `import` | Yes | Yes | `all` | All rows |
| `link` | Yes | Yes | `all` | All rows |
| `me` | No | No | `none` | Denied |
| `message_template` | Yes | Yes | `all` | All rows |
| `notice` | Yes | Yes | `all` | All rows |
| `processor` | Yes | Yes | `all` | All rows |
| `project` | Yes | Yes | `all` | All rows |
| `purpose` | Yes | Yes | `all` | All rows |
| `rights_request` | Yes | Yes | `all` | All rows |
| `site` | Yes | Yes | `all` | All rows |
| `ticket` | Yes | Yes | `own` | Own or addressed rows |
| `user` | Yes | No | `all` | All rows |

## Enforcement notes

- A missing grant is a denial.
- Scope is applied in the database query, not after rows are loaded.
- `write: yes` permits writes to the resource in principle; individual routes and state machines may impose stricter rules.
- A row outside the caller's scope returns 404; a visible but forbidden action returns 403.
- Every staff role requires MFA by default.
