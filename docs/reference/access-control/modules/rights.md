# Rights: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

44 operations; 44 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/requests` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/attention` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/acknowledge` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/classify` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/decide` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/download` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/escalate` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/event` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/event/evidence` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/files/{file_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/derive` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/confirm` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/contact` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/escalate` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/evidence` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/reassign` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/remind` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/return` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/send-back` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/withdraw` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/intent` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/linked/trail` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/refuse` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/respond` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/reviewer` | `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/scope/derive` | `dpo`, `admin` | Full session; anonymous NO |
| PUT | `/requests/{request_uuid}/scope/{item_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/apply` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/execute` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/tickets` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/trail` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/transition` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/transitions` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/verification/code` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/verification/confirm` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/verification/fail` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/verification/manual` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/withdrawal` | `dpo`, `admin` | Full session; anonymous NO |

## GET /requests

Every request in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L621), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests

Log a request received by email.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| YES | YES | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- Creation admits both DPO and Admin and does not apply an existing-row scope predicate. Admin can create an ordinary request it cannot subsequently read through the scoped register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L654), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/attention

What the office has not read.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L611), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}

Get Request.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L683), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/acknowledge

Send (or re-send) the acknowledgement.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L743), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/classify

Confirm, or reclassify, what this is.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L818), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/decide

Decide a grievance.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- DPO decides ordinary grievances. A grievance about the DPO requires Admin; if a reviewer is assigned, only that reviewer can decide it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1435), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L2350).

## GET /requests/{request_uuid}/download

The released response file.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1459), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/escalate

The complaint is about the DPO.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L917), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/event

Is the triggering event evidenced?.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L879), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/event/evidence

Download the triggering-event evidence.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L897), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/files/{file_uuid}

A file released with the response.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1410), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders

A holder the records missed.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L982), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/derive

Holders derived from export_line and asset_consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L968), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/confirm

Confirm Holder.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L998), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/contact

Record a mail sent, a chase, or a reply - and optionally send the mail.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1204), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/escalate

A holder missed its date - escalate once.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1306), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/holders/{holder_uuid}/evidence

Download a holder's return evidence.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1274), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence

Download a file attached to a message on the ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1185), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/reassign

Send an open ticket to a different respondent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1145), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/remind

Send the respondent a reminder now.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1167), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/return

Record what the holder returned.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1248), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/send-back

Send a returned ticket back to its holder.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1102), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/holders/{holder_uuid}/thread

The ticket's thread, as the office reads it.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1020), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/thread

Write to the holder on the ticket, with a file if it helps.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1072), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/holders/{holder_uuid}/withdraw

Withdraw a ticket issued in error.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1125), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/intent

She means erasure - confirmed.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L868), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/linked/trail

Everything recorded about the request this one is about.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L695), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/refuse

Not a rights request, or refused - with reasons.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L838), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/respond

Release and close.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests. `complete` is refused (response_partial_required) while a holder has not returned or a correction or erasure has not been carried out with evidence; the reason is served on the request as complete_blocked_by (S2-02).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1370), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/reviewer

Name the independent reviewer.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- Service narrows the route to Admin only, on an open grievance about the DPO; chosen reviewer must be an active Admin.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L928), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L660).

## POST /requests/{request_uuid}/scope/derive

Every appearance of her in a collected asset.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1322), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## PUT /requests/{request_uuid}/scope/{item_uuid}

What can go, what must stay, and why.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1335), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/scope/{item_uuid}/apply

Quarantine her appearance, then carry the decision out.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1358), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/scope/{item_uuid}/execute

Try an applied item's stores again now.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** As for the rest of the request: DPO all, Admin where about_dpo. Retries an applied erasure or redaction's stores now (S2-03); anything else is 409 `item_not_executable`.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/erasure.py).

## POST /requests/{request_uuid}/tickets

Issue a ticket to every confirmed holder.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1228), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## GET /requests/{request_uuid}/trail

Everything recorded about this request.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L723), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/transition

Transition.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- Available actions depend on request type, verification, intent, nominee evidence, reviewer, holder tickets and current state.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L945), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L1).

## GET /requests/{request_uuid}/transitions

Get Transitions.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- Available actions depend on request type, verification, intent, nominee evidence, reviewer, holder tickets and current state.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L713), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L1).

## POST /requests/{request_uuid}/verification/code

Send a code to the stored channel.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L754), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/verification/confirm

Enter the code she read back.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L769), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/verification/fail

No match, or verification not satisfied.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L801), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/verification/manual

Verified by hand, with the reason recorded.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L784), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).

## POST /requests/{request_uuid}/withdrawal

She meant withdrawal, not erasure.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** DPO can read all requests. Admin can read requests where about_dpo is true; this predicate is not limited to the assigned reviewer. Mutations apply action/state checks. This is distinct from personal /me/requests.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L853), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L99), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/state_machine.py#L109).
