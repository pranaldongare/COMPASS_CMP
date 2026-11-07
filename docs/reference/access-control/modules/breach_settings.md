# Breach settings: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

5 operations; 5 appear in the existing OpenAPI/API docs. Added with the public link, 2026-11-06; evidence links point at `HEAD`.

How the office hears of a breach ([ADR 0037](../../../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)): which roles are told of a report from the public link, and where the organisation's board is mailed. Resource `breach_settings`, kept by the administrator, the DPO and the Legal PoC. It says nothing about any breach, so the administrator may keep it without seeing one; every other role is answered **403**, as on an ordinary resource.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/breach-settings` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| PUT | `/breach-settings/intake-roles` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| POST | `/breach-settings/board-recipients` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| DELETE | `/breach-settings/board-recipients/{recipient_uuid}` | `dpo`, `admin`, `legal` | Full session; anonymous NO |
| PUT | `/breach-settings/board-recipients/{recipient_uuid}/mandatory` | `dpo`, `admin`, `legal` | Full session; anonymous NO |

## GET /breach-settings

Who hears of a breach, and how.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `BreachSettingsReader`.
- **Resolved gate:** `RequireResource(breach_settings)`.
- **Rules:** Resource `breach_settings`, read and write for the administrator, the DPO and the Legal PoC (0058, ADR 0037): the administrator keeps it with the officers and sees no breach by it; every other role is answered 403. Who is told of a report from the public link, the roles that may be chosen, the addresses on the organisation's board (name and email sealed) and the public link. Each entry on the board's list carries `mandatory`, and when and by whom the mark last changed (the name sealed); an address added for one report alone is never listed. (0064)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_settings.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/settings.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## PUT /breach-settings/intake-roles

Which roles are told of a report from the public link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `BreachSettingsWriter`.
- **Resolved gate:** `RequireResource(breach_settings, write=True)`.
- **Rules:** Resource `breach_settings`, read and write for the administrator, the DPO and the Legal PoC (0058, ADR 0037): the administrator keeps it with the officers and sees no breach by it; every other role is answered 403. An unknown role is 422; a breach-only login and a data principal cannot be chosen. The two officers are always kept on the list, whatever is sent. The trail records the roles.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_settings.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/settings.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breach-settings/board-recipients

Add an address to the organisation's board.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `BreachSettingsWriter`.
- **Resolved gate:** `RequireResource(breach_settings, write=True)`.
- **Rules:** Resource `breach_settings`, read and write for the administrator, the DPO and the Legal PoC (0058, ADR 0037): the administrator keeps it with the officers and sees no breach by it; every other role is answered 403. Not an email address is 422, and so is a name carrying the sealed prefix (on `full_name`); an address already listed, found by its blind index, is 409 `recipient_exists`. Name and email sealed. The trail records the change, never the address. Mails every active DPO and Legal account, naming the address and no breach; a broker that cannot be reached is 503 and nothing changes. One list, of no office: an address on it is offered to every report on either office's breaches, which the product owner kept on 2026-11-07 (ADR 0037).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_settings.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/settings.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## DELETE /breach-settings/board-recipients/{recipient_uuid}

Take an address off the organisation's board.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `BreachSettingsWriter`.
- **Resolved gate:** `RequireResource(breach_settings, write=True)`.
- **Rules:** Resource `breach_settings`, read and write for the administrator, the DPO and the Legal PoC (0058, ADR 0037): the administrator keeps it with the officers and sees no breach by it; every other role is answered 403. The row stays, with who took it off and when: reports already mailed name it. Not listed, or an address added for one report alone, is 404; a mandatory entry is 409 `recipient_mandatory` until it is made optional. The trail records the change, never the address. Mails every active DPO and Legal account, naming the address and no breach; a broker that cannot be reached is 503 and nothing changes (0064). Whatever was still queued to the address, on either office's reports, goes to the worker to be recorded failed (`RecipientRemoved`), and the organisation's board's duty is re-read after it; the caller is served none of that.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_settings.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/settings.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/reports.py).
## PUT /breach-settings/board-recipients/{recipient_uuid}/mandatory

Make an address on the organisation's board mandatory, or optional again.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `admin`, `legal`.
- **Route guard:** `BreachSettingsWriter`.
- **Resolved gate:** `RequireResource(breach_settings, write=True)`.
- **Rules:** Resource `breach_settings`, read and write for the administrator, the DPO and the Legal PoC (0058, ADR 0037): the administrator keeps it with the officers and sees no breach by it; every other role is answered 403. A mandatory entry goes with every report finalised while it is set, and cannot be taken off the list until it is made optional again. Each change writes an event (who and when) and the trail, never the address, and mails every active DPO and Legal account, naming the address and no breach. An unchanged mark records nothing and mails nobody. Not on the list, taken off, or an address added for one report alone is 404; a broker that cannot be reached is 503 and nothing changes. (0064, amended 2026-11-07)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_settings.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/settings.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/alerts/__init__.py).

