# Public Information: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

10 operations; 10 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

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

## GET /notice/{notice_uuid}

Public notice viewer.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Published or superseded notice only; draft notices are not public.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L64), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## GET /rights

How to make a rights request - Rule 9, Rule 14(1).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Public information about exercising rights; no identity or role gate.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L116), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## GET /rights/nominations/{token}

The acceptance link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination capability token required; no session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L273), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/accept

Accept a nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token plus contact code required to accept.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L300), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/code

A code to one of the contacts recorded on the nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token; code is sent to a contact recorded on that nomination.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L287), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominations/{token}/decline

Decline a nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid nomination token plus contact code required to decline.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L324), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominee/requests

A nominee makes a request on her behalf.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Accepted/usable nomination and nominee code required; trigger event is recorded and evidence is reviewed before substantive processing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L369), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/nominee/start

A nominee identifies himself.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Nomination reference and a recorded nominee contact required for code delivery.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L345), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/requests

Make a request without an account.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Anyone may submit without an account. Contact verification and subsequent office checks govern processing; submission is not access to another person’s records.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L212), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).

## POST /rights/requests/verify

Confirm the code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** The request reference/contact verification code must match; no session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/public/rights.py#L235), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/rights/service.py#L1).
