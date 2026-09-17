# Delegations: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

5 operations; 5 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/delegations` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/delegations` | `dpo`, `admin`, `dco` | Full session; anonymous NO |
| GET | `/delegations/held` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/delegations/mine` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| DELETE | `/delegations/{delegation_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |

## GET /delegations

Every live arrangement.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin list current cover arrangements. DPO cover records responsibility but adds no rows; DCO cover extends assignment scope while active.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/delegations.py#L138).

## POST /delegations

Arrange cover.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`, `dco`.
- **Route guard:** `RequireStaff`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(*STAFF_ROLES))]`.
- **Rules:** Successful creation: DPO or DCO arranges own cover, or Admin arranges it for them. Delegator and delegate must have the same role, one of DPO/DCO; delegate must be active, not self, and dates must be valid. Other staff pass the route guard but fail service eligibility.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/delegations.py#L79), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/delegations/service.py#L26).

## GET /delegations/held

Cover I am providing.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Any full session may list arrangements involving itself; data principals normally have none. Listing is not permission to create cover.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/delegations.py#L126).

## GET /delegations/mine

Cover I have arranged.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| OWN | OWN | OWN | OWN | OWN | OWN | OWN |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Any full session may list arrangements involving itself; data principals normally have none. Listing is not permission to create cover.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/delegations.py#L119).

## DELETE /delegations/{delegation_uuid}

End cover now.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `RequireStaff`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(*STAFF_ROLES))]`.
- **Rules:** Admin can revoke any arrangement; otherwise caller must be its named delegator or delegate. Role changes do not remove that participant check.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/delegations.py#L103), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/delegations/service.py#L140).
