# Roles, resource grants and row scope

[Guide](README.md)

**Legend:** `NO` = role cannot complete the operation; `YES` = eligible role (normal validation still applies); `ALL` = all rows within the named resource, not an administrator wildcard; `OWN` = own account or own-created project; `SCOPED` = assigned/project/site or about-DPO scope; `COND` = special conditions described in the module entry; `PUBLIC` = endpoint does not require a role. Anonymous `COND` means a link/code/capability is required, not a session role. These are implemented role eligibility and row scopes, not promises of success for invalid records or lifecycle states.

Roles refer to the **effective session role**. A staff account signed in through the portal OTP flow acts as `data_subject`. Ordinary staff sessions cannot use principal-only endpoints. The account itself retains its staff role.

| Role | Meaning |
| --- | --- |
| `dpo` | Data Protection Officer |
| `admin` | Administrator |
| `dco` | Data Collection Owner |
| `dco_admin` | DCO Admin |
| `rco` | Research Collection Owner |
| `rnd_user` | R&D User |
| `data_subject` | Data Subject |

## Static resource matrix

`R` = resource read grant; `RW` = read/write grant. This table alone is insufficient to determine endpoint access: handlers and services can narrow or bypass the matrix. The endpoint matrix records those differences.

| Resource | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| user | R / ALL | RW / ALL | NO | NO | NO | NO | NO |
| purpose | RW / ALL | R / ALL | R / ALL | R / ALL | R / ALL | R / ALL | NO |
| processor | RW / ALL | RW / ALL | R / ALL | R / ALL | R / ALL | R / ALL | NO |
| data_source | RW / ALL | RW / ALL | RW / ALL | RW / ALL | RW / ALL | R / ALL | NO |
| project | RW / ALL | NO | RW / SCOPED | RW / SCOPED | RW / SCOPED | RW / OWN | NO |
| approval | R / ALL | NO | R / SCOPED | R / SCOPED | R / SCOPED | RW / OWN | NO |
| site | RW / ALL | NO | RW / SCOPED | RW / SCOPED | RW / SCOPED | R / OWN | NO |
| notice | RW / ALL | NO | R / SCOPED | R / SCOPED | R / SCOPED | RW / OWN [^notice] | NO |
| link | RW / ALL | NO | RW / SCOPED | RW / SCOPED | RW / SCOPED | NO | NO |
| consent | R / ALL | NO | R / SCOPED | R / SCOPED | R / SCOPED | R / OWN | NO |
| export | RW / ALL | NO | RW / SCOPED | RW / SCOPED | RW / SCOPED | NO | NO |
| import | RW / ALL | NO | RW / SCOPED | RW / SCOPED | RW / SCOPED | R / OWN | NO |
| collection | R / ALL | NO | R / SCOPED | R / SCOPED | R / SCOPED | R / OWN | NO |
| asset | R / ALL | NO | R / SCOPED | R / SCOPED | R / SCOPED | R / OWN | NO |
| audit | R / ALL | R / ALL | NO | NO | NO | NO | NO |
| message_template | RW / ALL | RW / ALL | NO | NO | NO | NO | NO |
| me | NO | NO | NO | NO | NO | NO | RW / OWN |
| rights_request | RW / ALL | RW / SCOPED | NO | NO | NO | NO | NO |
| legal_hold | RW / ALL | NO | NO | NO | NO | NO | NO |
| restricted_country | RW / ALL | R / ALL | NO | NO | NO | NO | NO |
| ticket | RW / OWN | RW / OWN | RW / OWN | RW / OWN | RW / OWN | RW / OWN | NO |

## What scopes mean in this code

- **DPO:** generally all rows for granted resources; not a universal write role. For example, only R&D can create projects and only Admin can provision users.
- **Admin:** account management, registry, messages and audit. No project resource grant. Rights reads are limited to `about_dpo = true`, not automatically to the assigned reviewer.
- **DCO/RCO projects:** read the primary-owner project or a project with a site they run; write-scoped project operations require primary ownership. Active cover can extend ownership predicates.
- **DCO/RCO sites and consents:** site owner override, otherwise source owner; active cover counts. This is narrower than every site of a visible project.
- **DCO Admin:** third-party projects and non-in-house sites. This is a role-defined queue, not just rows personally assigned to that account.
- **R&D:** own-created projects and related records; some endpoint behavior is broader than the static matrix comments imply.
- **Data principal:** own consents, requests, disclosures and nominations through a session acting as `data_subject`. Shared profile/contact endpoints accept staff too; person-type change is an explicit exception.
- **Tickets:** every staff role can answer tickets addressed to that specific account; that does not grant full request access.
- **Imports without a project:** explicitly admitted by the repository predicate for every signed-in role. See implementation notes.

## Authentication and errors

Standard session dependencies resolve the configured session cookie, reject expired sessions and enforce CSRF on POST/PUT/PATCH/DELETE. `CurrentUser` rejects partial MFA sessions. `PartialUser` accepts partial or full sessions and has no role filter; its two MFA endpoints must be read individually. The public consent capture endpoint loads a cookie directly, so the standard dependency’s CSRF check must not be assumed there.

Role denials normally return 403; missing/expired sessions normally return 401. Scoped record lookups generally return 404 for records outside the caller’s scope. State/evidence/verification rules may refuse an otherwise eligible role. Public endpoints still validate tokens, codes, notice state and input as described in their entries.

[^notice]: The R&D User's write on a notice is narrower than the matrix row can
say. They may bring one - check a document, import it, or copy a notice the
Privacy Office has approved - and that is all. Composing one, editing its
wording, attaching, narrowing or removing a purpose, and writing the text of a
rendition are the office's, on routes guarded by role rather than by this
resource. The split is by act, not by resource, so it cannot be read off this
table; `tests/unit/api/test_who_writes_a_notice.py` is where it is pinned.

No live user-account listing was queried: “who” here means roles and ownership/assignment conditions, not employee names. This is a static source-based access reference, not a live authorization test or a claim of legal compliance.

Sources: [permission matrix](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/core/permissions.py#L1), [session dependency](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/sessions.py#L1), [role guards](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/dependencies/authorization.py#L1), [project/site scopes](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/projects.py#L82).
