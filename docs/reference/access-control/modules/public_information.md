# Public Information: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

18 operations; 18 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/notice/{notice_uuid}` | Public; no role required | No session required; anonymous COND |
| GET | `/rights` | Public; no role required | No session required; anonymous YES |
| GET | `/rights/nominations/{token}` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/nominations/{token}/accept` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/nominations/{token}/code` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/nominations/{token}/decline` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/nominee/requests` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/nominee/start` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/requests` | Public; no role required | No session required; anonymous COND |
| POST | `/rights/requests/verify` | Public; no role required | No session required; anonymous COND |
| GET | `/holder-tickets/{token}` | Public; no role required | No session required; anonymous COND |
| POST | `/holder-tickets/{token}/code` | Public; no role required | No session required; anonymous COND |
| POST | `/holder-tickets/{token}/verify` | Public; no role required | No session required; anonymous COND |
| POST | `/holder-tickets/{token}/sign-out` | Public; no role required | No session required; anonymous COND |
| GET | `/holder-tickets/{token}/ticket` | Public; no role required | No session required; anonymous COND |
| POST | `/holder-tickets/{token}/messages` | Public; no role required | No session required; anonymous COND |
| POST | `/holder-tickets/{token}/answer` | Public; no role required | No session required; anonymous COND |
| GET | `/holder-tickets/{token}/messages/{message_uuid}/evidence` | Public; no role required | No session required; anonymous COND |

## GET /notice/{notice_uuid}

Public notice viewer.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Published or superseded notice only; draft notices are not public.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L64), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## GET /rights

How to make a rights request - Rule 9, Rule 14(1).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public information about exercising rights; no identity or role gate.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L116), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## GET /rights/nominations/{token}

The acceptance link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination capability token required; no session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L273), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/accept

Accept a nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token plus contact code required to accept.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L300), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/code

A code to one of the contacts recorded on the nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token; code is sent to a contact recorded on that nomination.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L287), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/decline

Decline a nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token plus contact code required to decline.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L324), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominee/requests

A nominee makes a request on her behalf.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Accepted/usable nomination and nominee code required; trigger event is recorded and evidence is reviewed before substantive processing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L369), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominee/start

A nominee identifies himself.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Nomination reference and a recorded nominee contact required for code delivery.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L345), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/requests

Make a request without an account.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Anyone may submit without an account. Contact verification and subsequent office checks govern processing; submission is not access to another person’s records.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L212), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## POST /rights/requests/verify

Confirm the code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** The request reference/contact verification code must match; no session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/rights.py#L235), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/rights/service.py#L1).

## GET /holder-tickets/{token}

What an outside holder's ticket link opens, before the code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. Shows the reference, the holder's name, its state and date, and where the code goes - masked. Rate-limited per address (`holder_link_ip`). (0049, 2026-10-08)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## POST /holder-tickets/{token}/code

Send a code to the address on the ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. The code goes to the address the ticket was sent to, never one typed. Rate-limited per ticket (`holder_ticket_code`, five an hour) and per address (`holder_link_act_ip`). (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## POST /holder-tickets/{token}/verify

Enter the code: an hour on the ticket.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. A right code (scope `holder_ticket`, five attempts) sets `cmp_ticket` for an hour (HOLDER_TICKET_SESSION_S). (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## POST /holder-tickets/{token}/sign-out

Close the ticket on this device.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** Ends the hour the cookie holds, if any, and clears the cookie. (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## GET /holder-tickets/{token}/ticket

The ticket, after the code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. And the hour the code opened: the HttpOnly, SameSite=Strict `cmp_ticket` cookie, whose fingerprint in Redis names this ticket and this link (401 `code_needed` otherwise). What is asked, the erasure items, and the messages - the platform's brief of what it holds about the person first; sealed values as stored, opened by the portal. Reading marks the office's messages read. (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## POST /holder-tickets/{token}/messages

An outside holder writes to the Privacy Office.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. And the hour the code opened: the HttpOnly, SameSite=Strict `cmp_ticket` cookie, whose fingerprint in Redis names this ticket and this link (401 `code_needed` otherwise). Not on a closed request (409). A file up to 25 MB; every DPO is told. On the trail with no actor, side holder. (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## POST /holder-tickets/{token}/answer

An outside holder gives its answer.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. And the hour the code opened: the HttpOnly, SameSite=Strict `cmp_ticket` cookie, whose fingerprint in Redis names this ticket and this link (401 `code_needed` otherwise). Only an open ticket on an open request (409). What was done (done, partial, failed), what is held, and proof; it waits for the office to accept it or send it back. On the trail with no actor, channel `link`. (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).

## GET /holder-tickets/{token}/messages/{message_uuid}/evidence

Download a file on the ticket's messages.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** A valid ticket link: the token's keyed fingerprint names an issued ticket, and the link is that ticket's current one (a ticket sent to somebody else has a new link). Every failure is the same 404. Referrer-Policy no-referrer; the token is scrubbed from access logs. And the hour the code opened: the HttpOnly, SameSite=Strict `cmp_ticket` cookie, whose fingerprint in Redis names this ticket and this link (401 `code_needed` otherwise). A file on this ticket's thread only; every download is audited. (0049)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/rights.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/service.py).
