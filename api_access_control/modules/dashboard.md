# Dashboard: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

3 operations; 3 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/dashboard` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/notifications` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| POST | `/notifications/{log_uuid}/resend` | `dpo`, `dco` | Full session; anonymous NO |

## GET /dashboard

Role-aware aggregate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** All seven roles have a dashboard branch. Results are role-specific aggregates; staff also see their assigned tickets. A data principal sees their own dashboard.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/dashboard.py#L316).

## GET /notifications

Notifications.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Principal sees own audit events. Staff receive a global feed of selected event types plus own ticket events; DPO also gets office ticket events. The staff event query has no project/owner predicate.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/dashboard.py#L766).

## POST /notifications/{log_uuid}/resend

Resend.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | NO | COND | NO | NO | NO | NO |

- **Who:** `dpo`, `dco`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.DCO)`.
- **Rules:** DPO/DCO only. Event and subject recipient must exist. The event lookup is by log UUID without a caller/project-scope predicate.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/dashboard.py#L830).
