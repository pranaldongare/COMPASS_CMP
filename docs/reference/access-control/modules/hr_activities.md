# HR activities: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

6 operations; 6 appear in the existing OpenAPI/API docs. Added with the HR track (ADR 0033); evidence links point at `HEAD`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/hr/activities` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user` | Full session; anonymous NO |
| GET | `/hr/activities/options` | `hr_user` | Full session; anonymous NO |
| POST | `/hr/activities` | `hr_user` | Full session; anonymous NO |
| GET | `/hr/activities/{activity_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user` | Full session; anonymous NO |
| POST | `/hr/activities/{activity_uuid}/upgrade` | `hr_user` | Full session; anonymous NO |
| POST | `/hr/activities/{activity_uuid}/close` | `hr_user`, `legal` | Full session; anonymous NO |

## GET /hr/activities

HR activities in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user`.
- **Route guard:** `ActivityReader`.
- **Resolved gate:** `Annotated[Any, Depends(RequireResource("project"))]`.
- **Rules:** Only projects with a template version; within the caller's office, so the R&D roles list none. Legal's all; an HR PoC's of the categories assigned to them. (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).

## GET /hr/activities/options

What an activity can be made from.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |

- **Who:** `hr_user`.
- **Route guard:** `HrPoc`.
- **Resolved gate:** `Annotated[Any, Depends(RequireRole(Role.HR_USER))]`.
- **Rules:** The HR PoC's active categories, each with its active templates' approved versions and their purposes, the mandatory ones marked. (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).

## POST /hr/activities

Create an activity, live, with its link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |

- **Who:** `hr_user`.
- **Route guard:** `HrPoc`.
- **Resolved gate:** `Annotated[Any, Depends(RequireRole(Role.HR_USER))]`.
- **Rules:** One transaction: project (hr office), site run by the HR PoC under the category's HR system, notice composed from the version and published by the HR transition, link with `audience_mode`. 422 for a purpose off the list, a mandatory one missing, a description outside the slot, a past expiry; 409 for a retired version or one whose text no longer hashes to its approval; 404 for a category not assigned. (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).

## GET /hr/activities/{activity_uuid}

Get Activity.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user`.
- **Route guard:** `ActivityReader`.
- **Resolved gate:** `Annotated[Any, Depends(RequireResource("project"))]`.
- **Rules:** With its live link and the path to share. 404 outside scope. (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).

## POST /hr/activities/{activity_uuid}/upgrade

Move an activity to another approved version.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | NO | SCOPED |

- **Who:** `hr_user`.
- **Route guard:** `HrPoc`.
- **Resolved gate:** `Annotated[Any, Depends(RequireRole(Role.HR_USER))]`.
- **Rules:** A new notice version composed and published; the live link moves to it. A version flagged `reconsent_required` queues `hr_reconsent_request` to each participant with a current consent, after commit. (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).

## POST /hr/activities/{activity_uuid}/close

Close an activity.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | ALL | SCOPED |

- **Who:** `hr_user`, `legal`.
- **Route guard:** `ActivityCloser`.
- **Resolved gate:** `Annotated[Any, Depends(RequireRole(Role.HR_USER, Role.LEGAL))]`.
- **Rules:** The project closes and its links are revoked; consents stand. A retired version does not stop it (F-1). (2026-10-28, ADR 0033)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_activities.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/activities.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_activities.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/projects/state_machine.py).
