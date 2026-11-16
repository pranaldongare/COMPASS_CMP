# DataVault: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

7 operations; 7 appear in the existing OpenAPI/API docs. Added 2026-11-13 (migrations 0070 and 0071); evidence links point at `HEAD`.

DataVault is the store the labs' assets live in. The administrator keeps where it is reached; the office that answers a rights request asks it what it holds of the person ("Check in DataVault"), and the platform asks by itself when the holders found include a project's DCO Admin, who then sees their project's assets on their own ticket. On an erasure request the office tells DataVault to erase what it listed ("Erase in DataVault") and asks how far it has got ("Check status"). Every consent change - a withdrawal in full or in part, a consent given again, a validity run out - is told to DataVault by the worker once the administrator switches it on; it has no route. See [rights requests](../../../domain/rights-requests.md) and [ADR 0039](../../../decisions/0039-datavault-is-told-to-erase-by-the-office-and-of-consent-changes-by-the-worker.md).

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/datavault-connection` | `admin` | Full session; anonymous NO |
| PUT | `/datavault-connection` | `admin` | Full session; anonymous NO |
| GET | `/requests/{request_uuid}/datavault` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/datavault/check` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/datavault/erase` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| POST | `/requests/{request_uuid}/datavault/erase/status` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| GET | `/tickets/{holder_uuid}/datavault` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `breach_holder` | Full session; anonymous NO |

## GET /datavault-connection

Where DataVault is reached, and whether it is on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `DataVaultConnectionReader`.
- **Resolved gate:** `RequireResource(datavault_connection)`.
- **Rules:** Resource `datavault_connection`, the administrator's alone (0070): every other role is answered 403. Where DataVault is reached, the header its key is sent in, whether a key is stored and whether the platform may call it. The key is encrypted with the application key and never served; the trail records that the address or key changed, never either. Since 0071 also the erasure address, how IDs are named, whether consent changes are sent, and how their queue stands as counts and times (waiting, last delivered, why the last try failed in words) - nothing of any consent.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## PUT /datavault-connection

Set DataVault's address, its key, and switch it on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `DataVaultConnectionWriter`.
- **Resolved gate:** `RequireResource(datavault_connection, write=True)`.
- **Rules:** Resource `datavault_connection`, the administrator's alone (0070): every other role is answered 403. Where DataVault is reached, the header its key is sent in, whether a key is stored and whether the platform may call it. The key is encrypted with the application key and never served; the trail records that the address or key changed, never either. The address must be http or https with a host and no user, query or fragment (422); it cannot be switched on without one. `api_key` left out keeps the stored key; `clear_api_key` removes it. Since 0071 also the erasure address erasures and consent changes go to (`erasure_url`, the same rules), how IDs are named in every call (`id_format`, `numeric` or `uuid`; 422 otherwise) and whether consent changes go out by themselves (`consent_changes`, refused without the erasure address; the first time it is switched on fixes where they start, so nothing on record before is sent). The trail says which of these changed, never an address.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## GET /requests/{request_uuid}/datavault

What DataVault last said it holds of this request's person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `RightsReader`.
- **Resolved gate:** `RequireResource(rights_request, write=False)`.
- **Rules:** As every read of a request: the scoped lookup, so a request outside the caller's office is 404. Whether DataVault is set up, whether this caller may ask now, the last answered check with its assets (DataVault's asset identifier, the consent and project as it named them and ours where they are this person's own in the request's office, mid, datapath) and the last attempt if it failed. The name of who asked is sealed. On an erasure request (0071), also where each asset stands in DataVault (whether the request reaches it, its status, when, and DataVault's reason for one it did not erase) and what may be done now (`erasure`: may erase and why not, how many would go and how many are left out, how many are open, the counts, the last ask and its failure); null on any other request.
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

## POST /requests/{request_uuid}/datavault/erase

Erase in DataVault: tell it to erase the assets its last check listed.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** The scoped lookup, then the state machine's `may_act` (403 for a request that is not the caller's to act on). Only an erasure request (409 `datavault_not_an_erasure`). 409 `datavault_erasure_not_now` until it may be sent: a person behind the request, not closed, started and still open (in progress, awaiting holders or collating - identity verified, classified, erasure confirmed), the erasure address set, no legal hold on the person (a hold on the person, whichever office placed it), and a check DataVault answered. 409 `datavault_nothing_to_erase` when every asset the request reaches has been sent and is not failed. Sends the assets the last answered check listed that the request reaches - those matched to the person's records in the request's own office, and of a request confined to one consent that consent's chain only; the rest, and any DataVault gave no consent for, are left out - and that have not been sent or were not erased, each once and with the consent as DataVault gave it, presses on one request taken one at a time, as `POST {erasure address}/erasures` under a new `erasure_id`, at most 1000 assets to an instruction. The instruction is written and committed before the call, which is made with no transaction open; each asset's answer is kept (`erased`, `pending`, `failed` with DataVault's reason, `not_held`). The trail records counts and a failure code (`datavault.erasure_sent`, `datavault.erasure_checked`), never an asset or a reason. Nothing else about the request changes; nothing about it runs by itself.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/erasures.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## POST /requests/{request_uuid}/datavault/erase/status

Check status: ask DataVault how far each asset it was told to erase has got.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | SCOPED | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `RightsWriter`.
- **Resolved gate:** `RequireResource(rights_request, write=True)`.
- **Rules:** The scoped lookup, then `may_act`. Only an erasure request (409 `datavault_not_an_erasure`); 409 `datavault_not_configured` without the erasure address; 409 `datavault_nothing_pending` when no asset is unanswered or pending. Repeats every instruction with such an asset - the same `erasure_id` and the same assets, named as DataVault first took it - which starts nothing new, and keeps each answer; under a legal hold on the person it sends no instruction DataVault has never answered (409 `datavault_erasure_not_now`); an instruction DataVault refused outright and never answered has its assets marked not erased, to be sent again by a press; a final word already kept stands. Allowed on a closed request too: closing does not wait for DataVault. Recorded as `datavault.erasure_checked` with counts or a failure code.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/datavault.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/erasures.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/checks.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/datavault/connection.py), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

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
