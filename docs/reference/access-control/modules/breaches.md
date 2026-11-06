# Breaches: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

52 operations; 52 appear in the existing OpenAPI/API docs. Added with S3-01 to S3-04; evidence links point at `HEAD`.

An incident is logged first (`POST /breaches`); the first validation of *yes* records it as a breach ([ADR 0022](../../../decisions/0022-an-incident-first-and-a-breach-on-a-yes.md)). Every route is the DPO's and **hidden**: any other role - staff or principal - is answered **404**, on the register, on a breach that exists and on a write alike, where other DPO-only modules answer 403. That a breach is being handled is itself withheld.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/breaches` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/determinations` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/assessments` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/assessments` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/cert-in` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/cert-in/not-applicable` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/obligations/board_report/extension` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/transitions` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/transition` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/affected` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected/preview` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/notices` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices` | `dpo`, `legal` | Full session; anonymous NO |
| PUT | `/breaches/{breach_uuid}/notices/{notice_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices/{notice_uuid}/approve` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/notices/send` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/board/intimation` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/board/report` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/org-board/brief` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/tickets` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/tickets/{ticket_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/messages` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/messages/{message_uuid}/evidence` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/send-back` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/close` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/withdraw` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/reopen` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/attachments` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/attachments/{attachment_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/affected/upload/template` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected/upload/check` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/affected/upload` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/affected/contacts` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/intake` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/intake/dismissed` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/intake/{report_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/intake/{report_uuid}/claim` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/intake/{report_uuid}/dismiss` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/affected/options` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/reports` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/reports` | `dpo`, `legal` | Full session; anonymous NO |
| PUT | `/breaches/{breach_uuid}/reports/{report_uuid}` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/reports/{report_uuid}/finalise` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/reports/{report_uuid}/resend` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/reports/{report_uuid}/evidence` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/reports/{report_uuid}/file` | `dpo`, `legal` | Full session; anonymous NO |
| GET | `/breaches/{breach_uuid}/reports/{report_uuid}/pdf` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/breaches/{breach_uuid}/tickets/{ticket_uuid}/resolve-by` | `dpo`, `legal` | Full session; anonymous NO |

## GET /breaches

Every incident and breach, open first.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. `status` filters open or closed; each breach carries its duties and their clocks. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches

Log an incident as it was noticed.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Detection is entered, never defaulted; began must not follow it. A processor or source is named only for that kind of location. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}

One incident or breach, with every duty.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/determinations

Validate: is it a personal data breach? The first yes records it.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Yes needs the time of awareness and creates the three DPDP duties, and the organisation's board's, due thirty minutes from the validation (ADR 0037); no sets aside those not done. Refused on a closed breach (409 `breach_closed`). (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/assessments

Every revision of the assessment, newest first.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/assessments

Revise what is known; the previous revision stays.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A new revision; the previous stays. Every narrative field sealed. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/cert-in

Mark as a reportable cyber incident: CERT-In in six hours from detection.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Once per breach (409 `cert_in_marked`); due six hours from detection. Marked again after it was set aside, the duty comes back on that same clock, citing the latest determination. (S3-01, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/cert-in/not-applicable

Set aside a CERT-In mark made in error, once validated No; nobody is told.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A CERT-In mark made in error, set aside with a required reason (at most 8,000 characters), sealed on the duty's event. Only once the latest determination is No, which the event cites (409 `cert_in_not_validated_no`). The duty must be outstanding (409 `duty_not_outstanding`, or `no_such_duty` if it was never marked), no report to CERT-In filed (409 `report_filed`) and the breach open (409 `breach_closed`). Nobody is told, and the organisation's board's duty is left alone. The trail records that a reason was given. A decision for the product owner to confirm. (ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/obligations/board_report/extension

Record the longer period the Board allowed for the detailed report.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. The detailed report only; the date allowed must be later than its current due time. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/transitions

Whether it may close, and what stands in the way.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/transition

Close or reopen a breach.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Closing is refused while undetermined or while any duty is outstanding; a closure report is optional and never in the way; reopening needs a reason. (S3-01) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/affected

The people affected, as confirmed, with every revision.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Every revision, and the listed people a page at a time (`cursor` is a listed person's uuid). (S3-02) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected/preview

What the records show for these scopes, before confirming.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A read despite the method: looks in the chosen projects or activities, vendors and data sources, and writes nothing. An unknown kind is 422 naming the choices. (S3-02; tables removed, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/notices

Every version of the notice, and the account of who received which.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Every version, and the account of notices by version, channel and state (Rule 7(2)(b)(vi)). (S3-03) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices

Start the next version of the notice, as a draft.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Starts the next version as a draft; one draft at a time (409 `notice_draft_open`). (S3-03) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## PUT /breaches/{breach_uuid}/notices/{notice_uuid}

Edit a draft notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A draft only: an approved notice does not change (409 `notice_approved`, and by trigger). (S3-03) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices/{notice_uuid}/approve

Approve the words; refused while any of the five is empty.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Refused with any of the five Rule 7(1) contents empty (422 naming each). (S3-03) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/notices/send

Send the approved notice to everyone listed who lacks it; never twice, never before the breach is recorded.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Refused before approval (409 `no_approved_notice`) or with nobody listed; writes each listed person's account at once and queues email and SMS; a resend adds only what is missing. (S3-03) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/board/intimation

Draft the Board's initial intimation (Rule 7(2)(a)) from the register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Rule 7(2)(a), drafted from the register at any point; what it lacks is named in `missing`. Never submitted by the platform; what a person sends is the report under `/reports`. (S3-04) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/board/report

Draft the Board's detailed report (Rule 7(2)(b)), all six items.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Rule 7(2)(b)(i)-(vi); item (vi), the account of notices, is stated in words when nothing was sent. Never submitted by the platform; what a person sends is the report under `/reports`. (S3-04) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected

Confirm the people affected: a new revision, adding only the newly found.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Looks again in the chosen projects or activities, vendors and data sources server-side, leaves out `exclude`, adds `add`; a new revision listing only people not already listed. Refused on a closed breach. (S3-02) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/org-board/brief

Draft the brief for the organisation's board from the register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403. The register as it stands, at any point; counts only for the people affected, no finding on who caused it, no name or contact. What is mailed to the board is the report under `/reports`. (S3-07, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/board.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/tickets

Every ticket on a breach: holder, state, answer-by, unread, who added whom.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets

Assign a ticket to a member of staff; only on a recorded breach.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Refused before the breach is recorded (409 `breach_not_recorded`); the assignee is active staff picked by `user_uuid`, or - S3-09 - anybody named by `full_name`, `email` and optionally `mobile`, whose address must be on `BREACH_TICKET_EMAIL_DOMAINS` (422, the address not echoed); somebody without a console login is given a breach-only login (`breach_holder`) for this breach; one ticket per person per breach (409 `ticket_exists`). Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/tickets/{ticket_uuid}

One ticket, its thread, and the moves the server allows.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Reading it marks the holder's messages read. Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages

Write to the holder on the ticket, with a file if it helps.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/tickets/{ticket_uuid}/messages/{message_uuid}/evidence

Download a file attached to a message on the ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Every read is audited. Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/send-back

Send a returned ticket back to its holder, saying why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/close

Close a returned ticket: the DPO's alone.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Only the DPO closes a ticket (BD-07). Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/withdraw

Withdraw a ticket, saying why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/reopen

Reopen a closed or withdrawn ticket, saying why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/attachments

Keep a file with the incident: an email, a proof, a chat.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01), hidden from every other role (404). Multipart: `file` (PDF, PNG, JPEG, text, CSV, .eml, .msg or .docx; at most 25 MB), `kind` (email, proof, chat, other), an optional `note`. Kept as evidence - never replaced or removed, by trigger and grant; the name and note sealed. Refused on a closed breach (409 `breach_closed`), checked before the file is stored. The trail records the kind, never the name. (2026-10-06) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/attachments/{attachment_uuid}

Download a file kept with the incident; every download is audited.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records, hidden from every other role (404). A file of this breach only (404 otherwise). The response carries `X-Recorded-SHA256` (as kept) and `X-Content-SHA256` (as read); every read is `breach.attachment_read` on the trail. (2026-10-06) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/affected/upload/template

The Excel file to fill in: people (name, email, mobile) or asset IDs.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records, hidden from every other role (404). `kind` is contacts or assets; an Excel workbook with the columns and how to fill them, and no example row. (2026-10-07; Excel, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/lists.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected/upload/check

What a list would add, and each row it cannot read - nothing is written.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** Multipart `kind` and `file` (an Excel workbook or a CSV, 25 MB, 50,000 rows; an old .xls is refused with how to save it as .xlsx). Counts what would be added and names each unreadable row by number. Writes nothing. (2026-10-07) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/lists.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/affected/upload

Add the people a list names, or the people in the assets it names.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** Refused on a closed breach. A person whose email or mobile is an account's is listed as that account (`found_by` upload); anybody else is kept as a contact of this breach, name/email/mobile sealed, deduplicated by blind index. Assets: matched by platform asset ID or by `source_asset_ref` (with `source_code` when two sources share it); their consented people are listed, untraceable subjects counted. The file is not kept, only its sealed name, hash and counts. The trail records counts, never a name or contact. 409 `nothing_new` when everybody is already listed. (2026-10-07) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/lists.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/affected/contacts

People affected who have no account, and the lists they came in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records, hidden from every other role (404). Name, email and mobile sealed; paged by `cursor`. (2026-10-07) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/lists.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/intake

A page of the reports from the public link no office has taken up.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. The shared intake (0058, ADR 0037): a page of the reports from the public link that no office has claimed or dismissed, oldest first, visible to both officers. `limit` 1 to 200, 50 by default, and `offset`; the answer gives `items` and `total`. Each report by who sent it, its title, when it was noticed and arrived and what the reporter said of a cyber attack: a stranger can fill the intake, so the full text is read one report at a time (`GET /breaches/intake/{report_uuid}`). A report carries no office and no policy. The reporter's name and email and the title are sealed.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/intake/dismissed

Reports an office dismissed, newest first, with who did it and why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. The reports an office dismissed (0058, ADR 0037), newest first and the latest 200: who sent each, the officer who dismissed it and why. Both officers read all of them whichever office dismissed it, so a report that was the other office's can be raised. A report carries no office and no policy. The reporter's name and email, the title and the reason are sealed.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/intake/{report_uuid}

One waiting report in full.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. One waiting report in full, for either officer (0058, ADR 0037). Not known is 404; a report with its outcome is 409 `already_claimed` or `already_dismissed`, which is how an officer who has it open learns somebody took it up. A report carries no office and no policy. The reporter's name and email, the title and what they said are sealed.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/intake/{report_uuid}/claim

Take a report into this office's register, as an incident.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Logs the incident into the claiming officer's office, under the number the report arrived with; first noticed is when it arrived. No duty starts, and a reporter's yes to a cyber attack creates no CERT-In duty. The report's row is held, so a second claim is 409 `already_claimed`, and a dismissed report 409 `already_dismissed`. (0058, ADR 0037)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/intake/{report_uuid}/dismiss

Dismiss a report, saying why; it is kept.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A reason is required (422), sealed; the report stays, and reaches no register. 409 `already_claimed` or `already_dismissed` once it has its outcome. The trail records that a reason was given. (0058, ADR 0037)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/affected/options

The projects and activities to choose from, with how many people each.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. The session's office's projects and activities with a consent in them, each with how many people gave one; counts only, nobody named. (0060, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/affected.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/reports

Every kind of report on a breach, and where each stands.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Each of the five kinds of report: where it stands, what it would discharge, why it may not be written yet, and every version with its sealed sections, its proofs and what became of its mail. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/reports

Start the next version of a report, drafted from the register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. `kind` is org_board, board_intimation, cert_in, board_report or closure (422 otherwise). The first version is drafted from the register; a later one starts from the last one's words. One draft of a kind at a time (409 `report_draft_open`). Every kind but cert_in waits for the breach to be recorded (409 `breach_not_recorded`); cert_in waits for the duty instead. Refused on a closed breach. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## PUT /breaches/{breach_uuid}/reports/{report_uuid}

Edit a draft report.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. A draft only: a finalised report does not change (409 `report_finalised`, and by trigger). An unknown section is 422. The sections are sealed; the trail records the kind and the version. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/reports/{report_uuid}/finalise

Freeze a report and mail the organisation's board; never a regulator.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Freezes the words and mails the organisation's board. Refused with a required section empty (422 naming each) or with nobody on the board's list (409 `no_board_recipients`). A report of kind org_board completes that duty when the mail lands, naming who was reached, and a mail that reaches nobody leaves it outstanding; every other kind goes to the board for its information, a report to CERT-In even before a yes. Nothing goes to a regulator (ADR 0021). (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/reports/{report_uuid}/resend

Mail the report again to every address it has not reached.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. After finalising (409 `report_not_finalised`). An `org_board` report's duty is re-read first, whatever follows. Queues a new attempt for every address on the list whose last one failed or stayed queued fifteen minutes, and the first for an address added since; an address the report has reached, whichever row of the list it was mailed under, is left, and one taken off the list is never mailed. Refused with nobody on the list (409 `no_board_recipients`), on a version a later finalised one replaced (409 `report_superseded`) and on a report to CERT-In once that duty is set aside (409 `breach_not_recorded`), unless the re-read completed the duty, which answers 200. The answer adds `queued`, how many this press queued. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/reports/{report_uuid}/evidence

Keep the proof of internal approval, or of the mail sent to the regulator.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Multipart: `file` (as an incident's attachment; at most 25 MB), `kind` (approval or sent_mail), an optional `note`. Kept with the breach's other files, name and note sealed, never replaced or removed. After finalising and before filing (409 `report_not_finalised`, `report_filed`); never on a report to the organisation's board (409 `report_not_filed`). Checked before the file is stored. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/reports/{report_uuid}/file

Record that a person sent it to the regulator; needs both proofs.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Records that a person sent it to the regulator: when, and the reference returned, which every report that discharges a duty needs (422). Refused without both proofs (409 `report_proof_missing`), before finalising, or dated before it. The only way a regulator's duty completes: `POST /breaches/{breach_uuid}/obligations/{duty}/complete` is gone. The platform sends nothing. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breaches/{breach_uuid}/reports/{report_uuid}/pdf

The report as a PDF; every read is audited.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachReader`.
- **Resolved gate:** `RequireResource(breach, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role: `RequireResource(breach, hidden=True)` answers 404, not 403, so a caller cannot tell a breach from a uuid that was never one. Any version, draft or finalised. Every read is `breach.report_read` on the trail. (0059, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breaches/{breach_uuid}/tickets/{ticket_uuid}/resolve-by

Change the date to resolve the ticket by, saying why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `BreachWriter`.
- **Resolved gate:** `RequireResource(breach, write=True, hidden=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `breach`, S3-01). Hidden from every other role - a ticket's holder included: `RequireResource(breach, hidden=True)` answers 404, not 403. Every write takes the breach row first; a closed breach refuses it (409 `breach_closed`). (S3-08) While the ticket is open (409 `ticket_not_open`); a reason is required (422), and a date in the past or the date it already has is refused. The old date, the new one and the sealed reason go on the ticket's events and its thread, the two dates on the trail. No approval. The holder is told, in words that name no breach. (0061, ADR 0037) Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breaches.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).
