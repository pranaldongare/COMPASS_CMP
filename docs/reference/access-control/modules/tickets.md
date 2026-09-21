# Tickets: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

5 operations; 5 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/tickets` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/tickets/{holder_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/tickets/{holder_uuid}/messages` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/tickets/{holder_uuid}/messages/{message_uuid}/evidence` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/tickets/{holder_uuid}/return` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |

## GET /tickets

Tickets addressed to me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `TicketReader`.
- **Resolved gate:** `RequireResource(ticket, write=False)`.
- **Rules:** Any staff role can use tickets addressed to that account only (respondent_user_id). This does not grant the staff member the full rights-request register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1687), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L891).

## GET /tickets/{holder_uuid}

One ticket, with its brief and thread.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `TicketReader`.
- **Resolved gate:** `RequireResource(ticket, write=False)`.
- **Rules:** Any staff role can use tickets addressed to that account only (respondent_user_id). This does not grant the staff member the full rights-request register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1700), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L891).

## POST /tickets/{holder_uuid}/messages

Write to the Privacy Office on my ticket, with a file if it helps.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `TicketWriter`.
- **Resolved gate:** `RequireResource(ticket, write=True)`.
- **Rules:** Any staff role can use tickets addressed to that account only (respondent_user_id). This does not grant the staff member the full rights-request register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1711), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L891).

## GET /tickets/{holder_uuid}/messages/{message_uuid}/evidence

Download a file attached to a message on my ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `TicketReader`.
- **Resolved gate:** `RequireResource(ticket, write=False)`.
- **Rules:** Any staff role can use tickets addressed to that account only (respondent_user_id). This does not grant the staff member the full rights-request register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1735), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L891).

## POST /tickets/{holder_uuid}/return

Return a ticket addressed to me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `TicketWriter`.
- **Resolved gate:** `RequireResource(ticket, write=True)`.
- **Rules:** Any staff role can use tickets addressed to that account only (respondent_user_id). This does not grant the staff member the full rights-request register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/rights.py#L1753), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/rights.py#L891).
