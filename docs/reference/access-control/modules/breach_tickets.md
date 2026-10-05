# Breach tickets: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

5 operations; 5 appear in the existing OpenAPI/API docs. Added with S3-08; evidence links point at `HEAD`.

The holder's side of a breach ticket ([ADR 0023](../../../decisions/0023-breach-tickets-and-breach-only-logins.md)). Resource `breach_ticket`, OWN for every staff role - the same rows as `ticket` - and OWN is the holder in the `WHERE` clause, so another person's ticket is **404**. A holder sees the breach reference, their instruction, the thread, the state and the answer-by date, and nothing else from the register; the register itself answers them 404. Managing tickets - assigning, sending back, closing, withdrawing, reopening - is the DPO's, under `/breaches/{breach_uuid}/tickets`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/breach-tickets` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/breach-tickets/{ticket_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/breach-tickets/{ticket_uuid}/messages` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/breach-tickets/{ticket_uuid}/messages/{message_uuid}/evidence` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/breach-tickets/{ticket_uuid}/return` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |

## GET /breach-tickets

Breach tickets addressed to me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** every member of staff, for a ticket addressed to them; anyone else 404 by scope, a data principal 403.
- **Route guard:** `BreachTicketReader`.
- **Resolved gate:** `RequireResource(breach_ticket)`.
- **Rules:** Resource `breach_ticket`, OWN for every staff role: the holder is this account, in the WHERE clause, so another person's ticket is 404. What a holder sees is the breach reference, their instruction, the thread, the state and the answer-by date (BD-13). A closed breach refuses every write. (S3-08)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breach-tickets/{ticket_uuid}

One breach ticket addressed to me, with its thread.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** every member of staff, for a ticket addressed to them; anyone else 404 by scope, a data principal 403.
- **Route guard:** `BreachTicketReader`.
- **Resolved gate:** `RequireResource(breach_ticket)`.
- **Rules:** Resource `breach_ticket`, OWN for every staff role: the holder is this account, in the WHERE clause, so another person's ticket is 404. What a holder sees is the breach reference, their instruction, the thread, the state and the answer-by date (BD-13). A closed breach refuses every write. (S3-08) Reading it marks the office's messages read.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breach-tickets/{ticket_uuid}/messages

Write to the Privacy Office on my breach ticket, with a file if it helps.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** every member of staff, for a ticket addressed to them; anyone else 404 by scope, a data principal 403.
- **Route guard:** `BreachTicketWriter`.
- **Resolved gate:** `RequireResource(breach_ticket, write=True)`.
- **Rules:** Resource `breach_ticket`, OWN for every staff role: the holder is this account, in the WHERE clause, so another person's ticket is 404. What a holder sees is the breach reference, their instruction, the thread, the state and the answer-by date (BD-13). A closed breach refuses every write. (S3-08)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## GET /breach-tickets/{ticket_uuid}/messages/{message_uuid}/evidence

Download a file attached to a message on my breach ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** every member of staff, for a ticket addressed to them; anyone else 404 by scope, a data principal 403.
- **Route guard:** `BreachTicketReader`.
- **Resolved gate:** `RequireResource(breach_ticket)`.
- **Rules:** Resource `breach_ticket`, OWN for every staff role: the holder is this account, in the WHERE clause, so another person's ticket is 404. What a holder sees is the breach reference, their instruction, the thread, the state and the answer-by date (BD-13). A closed breach refuses every write. (S3-08) Every read is audited.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /breach-tickets/{ticket_uuid}/return

Return my breach ticket: what was done, and how it went.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | NO |

- **Who:** every member of staff, for a ticket addressed to them; anyone else 404 by scope, a data principal 403.
- **Route guard:** `BreachTicketWriter`.
- **Resolved gate:** `RequireResource(breach_ticket, write=True)`.
- **Rules:** Resource `breach_ticket`, OWN for every staff role: the holder is this account, in the WHERE clause, so another person's ticket is 404. What a holder sees is the breach reference, their instruction, the thread, the state and the answer-by date (BD-13). A closed breach refuses every write. (S3-08) Outcome done, partial or failed; only while the ticket is issued.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/breach_tickets.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/tickets.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).
