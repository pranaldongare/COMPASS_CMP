# DataVault: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

5 operations; 5 appear in the existing OpenAPI/API docs. Added 2026-11-13 (migration 0070); evidence links point at `HEAD`.

DataVault is the store the labs' assets live in. The administrator keeps where it is reached; the office that answers a rights request asks it what it holds of the person ("Check in DataVault"), and the platform asks by itself when the holders found include a project's DCO Admin, who then sees their project's assets on their own ticket. See [rights requests](../../../domain/rights-requests.md).

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/datavault-connection` | `admin` | Full session; anonymous NO |
| PUT | `/datavault-connection` | `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/datavault` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/datavault/check` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| GET | `/tickets/{holder_uuid}/datavault` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |

## GET /datavault-connection

Where DataVault is reached, and whether it is on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `DataVaultConnectionReader`.
- **Resolved gate:** `RequireResource(datavault_connection)`.
- **Rules:** Resource `datavault_connection`, the administrator's alone (0070): every other role is answered 403. Where DataVault is reached, the header its key is sent in, whether a key is stored and whether the platform may call it. The key is encrypted with the application key and never served; the trail records that the address or key changed, never either.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## PUT /datavault-connection

Set DataVault's address, its key, and switch it on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `DataVaultConnectionWriter`.
- **Resolved gate:** `RequireResource(datavault_connection, write=True)`.
- **Rules:** Resource `datavault_connection`, the administrator's alone (0070): every other role is answered 403. Where DataVault is reached, the header its key is sent in, whether a key is stored and whether the platform may call it. The key is encrypted with the application key and never served; the trail records that the address or key changed, never either. The address must be http or https with a host and no user, query or fragment (422); it cannot be switched on without one. `api_key` left out keeps the stored key; `clear_api_key` removes it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## GET /requests/{request_uuid}/datavault

What DataVault last said it holds of this request's person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** As every read of a request: the scoped lookup, so a request outside the caller's office is 404. Whether DataVault is set up, whether this caller may ask now, the last answered check with its assets (DataVault's asset identifier, the consent and project as it named them and ours where they are this person's own in the request's office, mid, datapath) and the last attempt if it failed. The name of who asked is sealed.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## POST /requests/{request_uuid}/datavault/check

Check in DataVault: ask it now what it holds of this request's person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** The scoped lookup, then the state machine's `may_act` (403 for a request that is not the caller's to act on). 409 `datavault_not_configured` while DataVault is off or has no address; 409 `datavault_not_askable` for a request with no person behind it or a closed one. One outbound call, `GET {address}/lookup?request_id=<reference>&person_id=<Person ID>`, with no transaction open; recorded whether or not it is answered (`datavault.checked`). A failure is a short code and never DataVault's body. Changes nothing else on the request. The platform makes the same call unattended whenever holders are found - as the request starts (POST /requests/{request_uuid}/transition to in_progress) or on POST /requests/{request_uuid}/holders/derive - when a project's DCO Admin is among them and DataVault has not answered for the request yet.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## GET /tickets/{holder_uuid}/datavault

On a DCO Admin's ticket: the assets DataVault listed for their project.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO | OWN | NO | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `breach_holder`.
- **Route guard:** `RequireResource(ticket)`.
- **Resolved gate:** `RequireResource(ticket, write=False)`.
- **Rules:** Bounded by the holder's own account, as every ticket route is. Lists the assets of the last answered check whose project is the one the ticket's holder answers for, and only for a holder found as a project's DCO Admin (0069); any other ticket, one addressed to somebody else, or one DataVault has not answered for, answers 200 with nothing listed.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)
