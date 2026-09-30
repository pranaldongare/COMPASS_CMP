# Breaches: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

21 operations; 21 appear in the existing OpenAPI/API docs. Added with S3-01 to S3-04; evidence links point at `HEAD`.

Every route is the DPO's and **hidden**: any other role - staff or principal - is answered **404**, on the register, on a breach that exists and on a write alike, where other DPO-only modules answer 403. That a breach is being handled is itself withheld.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/breaches` | `dpo` | Full session; anonymous NO |
| POST | `/breaches` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/determinations` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/assessments` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/assessments` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/cert-in` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/obligations/{duty}/complete` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/obligations/board_report/extension` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/transitions` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/transition` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/affected` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected/preview` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/notices` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices` | `dpo` | Full session; anonymous NO |
| PUT | `/breaches/{breach_uuid}/notices/{notice_uuid}` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices/{notice_uuid}/approve` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices/send` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/board/intimation` | `dpo` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/board/report` | `dpo` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected` | `dpo` | Full session; anonymous NO |

## GET /breaches

The register, open first.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. `status` filters open or closed; each breach carries its duties and their clocks. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches

Record a breach as it was noticed.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Detection is entered, never defaulted; began must not follow it. A processor or source is named only for that kind of location. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}

One breach, with every duty.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/determinations

Record whether it is a personal data breach.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Yes needs the time of awareness and creates the three DPDP duties; no sets aside those not done. Refused on a closed breach (409 `breach_closed`). (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/assessments

Every revision of the assessment, newest first.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/assessments

Revise what is known; the previous revision stays.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A new revision; the previous stays. Every narrative field sealed. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/cert-in

Mark as a reportable cyber incident: CERT-In in six hours from detection.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Once per breach (409 `cert_in_marked`); due six hours from detection. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/obligations/{duty}/complete

Record a submission made, with the regulator's reference.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. An unknown duty is 422; `principals` is refused (409): it completes by delivery (S3-03). (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/obligations/board_report/extension

Record the longer period the Board allowed for the detailed report.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. The detailed report only; the date allowed must be later than its current due time. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/transitions

Whether it may close, and what stands in the way.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/transition

Close or reopen a breach.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Closing is refused while undetermined or while any duty is outstanding; reopening needs a reason. (S3-01)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/affected

Who the breach touched, as confirmed, with every revision.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Every revision, and the listed people a page at a time (`cursor` is a listed person's uuid). (S3-02)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected/preview

What the records show for these scopes, before confirming.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A read despite the method: derives from the scopes and writes nothing. An unknown table is 422 naming the choices. (S3-02)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/notices

Every version of the notice, and the account of who received which.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Every version, and the account of notices by version, channel and state (Rule 7(2)(b)(vi)). (S3-03)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices

Start the next version of the notice, as a draft.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Starts the next version as a draft; one draft at a time (409 `notice_draft_open`). (S3-03)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## PUT /breaches/{breach_uuid}/notices/{notice_uuid}

Edit a draft notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A draft only: an approved notice does not change (409 `notice_approved`, and by trigger). (S3-03)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve

Approve the words; refused while any of the five is empty.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Refused with any of the five Rule 7(1) contents empty (422 naming each). (S3-03)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices/send

Send the approved notice to everyone listed who lacks it; never twice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Refused before approval (409 `no_approved_notice`) or with nobody listed; writes each listed person's account at once and queues email and SMS; a resend adds only what is missing. (S3-03)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/board/intimation

Draft the Board's initial intimation (Rule 7(2)(a)) from the register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Rule 7(2)(a), drafted from the register at any point; what it lacks is named in `missing`. Never submitted by the platform. (S3-04)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/board/report

Draft the Board's detailed report (Rule 7(2)(b)), all six items.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Rule 7(2)(b)(i)-(vi); item (vi), the account of notices, is stated in words when nothing was sent. Never submitted by the platform. (S3-04)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected

Confirm who the breach touched: a new revision, adding only the newly found.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`; everyone else 404.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The DPO's alone (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Re-derives from the scopes server-side, leaves out `exclude`, adds `add`; a new revision listing only people not already listed. Refused on a closed breach. (S3-02)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).
