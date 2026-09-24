# Public Consent: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

6 operations; 6 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/c/{token}` | Public; no role required | No session required; anonymous COND |
| POST | `/c/{token}/consent` | `data_subject` | Data-principal session + link token; anonymous NO |
| GET | `/c/{token}/notice` | Public; no role required | No session required; anonymous COND |
| POST | `/c/{token}/otp` | Public; no role required | No session required; anonymous COND |
| POST | `/c/{token}/otp/verify` | Public; no role required | No session required; anonymous COND |
| POST | `/c/{token}/register` | Public; no role required | No session required; anonymous COND |

## GET /c/{token}

Validate the link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid consent-link capability token required; link state, expiry and use limits are checked. No session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L97), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).

## POST /c/{token}/consent

Give Consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Requires a loaded session whose effective role is data_subject, a valid link, and a matching server-side notice-serving record. The subject is taken from the session. Staff must first sign in through the principal OTP flow; staff-role sessions are refused. This handler loads its cookie directly instead of using CurrentUser/its CSRF dependency. The account's age must be known and adult: an unknown age is refused as age_required and a child as consent_minor_not_permitted, before anything is written (S2-01). Withdrawal is not gated by age.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L232), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).

## GET /c/{token}/notice

Render the notice - stamps served_at.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid link and legally approved language required. Reading is public; a loaded session binds the server-side notice-serving record to that person.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L204), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).

## POST /c/{token}/otp

6-digit code, 10 minutes.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid link and registered contact required for code delivery; no prior session required.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L156), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).

## POST /c/{token}/otp/verify

5 attempts, then the code is discarded.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid link and contact code(s) required. Completion opens a data_subject session, including for staff account holders.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L168), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).

## POST /c/{token}/register

Register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** Valid consent link required. Registration/contact verification does not grant a staff session. A date of birth is required; one under eighteen creates no account and spends no use of the link (S2-01, cmp.domain.users.age). An existing account is recognised and not updated.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/public/consent.py#L132), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L327), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/consent/service.py#L453).
