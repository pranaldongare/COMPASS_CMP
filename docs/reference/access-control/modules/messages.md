# Messages: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

6 operations; 6 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/messages` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/messages/{key}` | `dpo`, `admin` | Full session; anonymous NO |
| DELETE | `/messages/{key}/{channel}` | `dpo`, `admin` | Full session; anonymous NO |
| PUT | `/messages/{key}/{channel}` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/messages/{key}/{channel}/preview` | `dpo`, `admin` | Full session; anonymous NO |
| PUT | `/messages/{key}/copies` | `dpo`, `admin` | Full session; anonymous NO |

## GET /messages

Every message, with the words in force.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageReader`.
- **Resolved gate:** `RequireResource(message_template, write=False)`.
- **Rules:** DPO/Admin manage message templates globally. Preview uses the read grant; saving/resetting a template uses the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/messages.py#L76).

## GET /messages/{key}

One message.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageReader`.
- **Resolved gate:** `RequireResource(message_template, write=False)`.
- **Rules:** DPO/Admin manage message templates globally. Preview uses the read grant; saving/resetting a template uses the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/messages.py#L82).

## DELETE /messages/{key}/{channel}

Back to the default.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageWriter`.
- **Resolved gate:** `RequireResource(message_template, write=True)`.
- **Rules:** DPO/Admin manage message templates globally. Preview uses the read grant; saving/resetting a template uses the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/messages.py#L114).

## PUT /messages/{key}/{channel}

Replace the words.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageWriter`.
- **Resolved gate:** `RequireResource(message_template, write=True)`.
- **Rules:** DPO/Admin manage message templates globally. Preview uses the read grant; saving/resetting a template uses the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/messages.py#L99).

## POST /messages/{key}/{channel}/preview

Render words with sample values, saving nothing.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageReader`.
- **Resolved gate:** `RequireResource(message_template, write=False)`.
- **Rules:** DPO/Admin manage message templates globally. Preview uses the read grant; saving/resetting a template uses the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/messages.py#L92).

## PUT /messages/{key}/copies

Who it is copied to by email: up to five addresses.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `MessageWriter`.
- **Resolved gate:** `RequireResource(message_template, write=True)`.
- **Rules:** As every write of a message's words. Only a message the catalogue marks copyable (`COPYABLE`) takes copies - never one with a code, a link or a person's own record (422 otherwise). At most 5 addresses; the set is replaced; addresses sealed with a blind index. The trail records the count, never an address. (2026-10-08)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/messages.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/messaging/service.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).
