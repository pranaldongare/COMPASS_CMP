# Breaches: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

14 operations; 14 appear in the existing OpenAPI/API docs. Added with S3-01 to S3-04; evidence links point at `HEAD`.

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
