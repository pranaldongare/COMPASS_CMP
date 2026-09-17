# Me: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

26 operations; 26 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/me` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| PATCH | `/me` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/me/consents` | `data_subject` | Full session; anonymous NO |
| GET | `/me/consents/{consent_uuid}` | `data_subject` | Full session; anonymous NO |
| GET | `/me/consents/{consent_uuid}/grants` | `data_subject` | Full session; anonymous NO |
| GET | `/me/consents/{consent_uuid}/history` | `data_subject` | Full session; anonymous NO |
| GET | `/me/consents/{consent_uuid}/notice` | `data_subject` | Full session; anonymous NO |
| GET | `/me/consents/{consent_uuid}/trail` | `data_subject` | Full session; anonymous NO |
| POST | `/me/consents/{consent_uuid}/withdraw` | `data_subject` | Full session; anonymous NO |
| POST | `/me/contact/verify` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| POST | `/me/contacts/code` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/me/disclosures` | `data_subject` | Full session; anonymous NO |
| GET | `/me/nominations` | `data_subject` | Full session; anonymous NO |
| POST | `/me/nominations` | `data_subject` | Full session; anonymous NO |
| DELETE | `/me/nominations/{nomination_uuid}` | `data_subject` | Full session; anonymous NO |
| GET | `/me/nominee-of` | `data_subject` | Full session; anonymous NO |
| GET | `/me/notifications` | `data_subject` | Full session; anonymous NO |
| POST | `/me/person-type` | `dpo`, `admin`, `data_subject` | Full session; anonymous NO |
| GET | `/me/requests` | `data_subject` | Full session; anonymous NO |
| POST | `/me/requests` | `data_subject` | Full session; anonymous NO |
| GET | `/me/requests/{request_uuid}` | `data_subject` | Full session; anonymous NO |
| POST | `/me/requests/{request_uuid}/dispute` | `data_subject` | Full session; anonymous NO |
| GET | `/me/requests/{request_uuid}/download` | `data_subject` | Full session; anonymous NO |
| GET | `/me/requests/{request_uuid}/files/{file_uuid}` | `data_subject` | Full session; anonymous NO |
| GET | `/me/requests/{request_uuid}/trail` | `data_subject` | Full session; anonymous NO |
| DELETE | `/me/secondary-email` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |

## GET /me

Get Me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L114).

## PATCH /me

Update Me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- Adding/changing a contact does not make it usable for sign-in until the matching code is verified.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L123).

## GET /me/consents

My Consents.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L253).

## GET /me/consents/{consent_uuid}

My Consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L267).

## GET /me/consents/{consent_uuid}/grants

My Consent Grants.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L311).

## GET /me/consents/{consent_uuid}/history

The supersession chain.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L320).

## GET /me/consents/{consent_uuid}/notice

The words she actually saw.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L288).

## GET /me/consents/{consent_uuid}/trail

What was recorded about this consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L332).

## POST /me/consents/{consent_uuid}/withdraw

Withdraw.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L366).

## POST /me/contact/verify

Confirm one of my contacts.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- Adding/changing a contact does not make it usable for sign-in until the matching code is verified.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L191).

## POST /me/contacts/code

A code to confirm one of my contacts.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- Adding/changing a contact does not make it usable for sign-in until the matching code is verified.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L181).

## GET /me/disclosures

Who was my data shared with (s.11(1)(b)).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L387).

## GET /me/nominations

Whom I have nominated.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1615).

## POST /me/nominations

Nominate somebody - s.14.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1657).

## DELETE /me/nominations/{nomination_uuid}

Revoke a nomination.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1672).

## GET /me/nominee-of

Who has nominated me.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- Matches nominations naming the caller’s verified contacts; this lists nominee relationships, not only nominations the caller created.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1625).

## GET /me/notifications

My Notifications.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L394).

## POST /me/person-type

Change Person Type.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | NO | NO | NO | NO | OWN |

- **Who:** `dpo`, `admin`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role not in (Role.DATA_SUBJECT, Role.DPO, Role.ADMIN)`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L212).

## GET /me/requests

My requests.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1483).

## POST /me/requests

Make a request, signed in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1495).

## GET /me/requests/{request_uuid}

My Request.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1549).

## POST /me/requests/{request_uuid}/dispute

Dispute the response - a grievance under s.13.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1597).

## GET /me/requests/{request_uuid}/download

The response, while the window is open.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1567).

## GET /me/requests/{request_uuid}/files/{file_uuid}

A file released with the response, while the window is open.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1580).

## GET /me/requests/{request_uuid}/trail

What was recorded about my request.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | OWN |

- **Who:** `data_subject`.
- **Route guard:** `RequireDataSubject`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DATA_SUBJECT))]`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Effective session role must be data_subject. Staff account holders can use this endpoint through a portal OTP session acting as data_subject.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/rights.py#L1556).

## DELETE /me/secondary-email

Remove my second address.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Only the signed-in person’s record or their related records; an account UUID supplied by the client does not select a different principal.
- Shared account/profile route: staff sessions are accepted. POST /me/person-type is narrower: DPO, Admin and data_subject only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/me.py#L202).
