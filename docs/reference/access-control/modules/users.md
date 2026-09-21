# Users: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

13 operations; 13 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/users` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/users` | `admin` | Full session; anonymous NO |
| GET | `/users/collection-owners` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/users/staff` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/users/{user_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| PATCH | `/users/{user_uuid}` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/deactivate` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/invite` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/mfa/reset` | `admin` | Full session; anonymous NO |
| GET | `/users/{user_uuid}/person-type-history` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/reactivate` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/role` | `admin` | Full session; anonymous NO |
| DELETE | `/users/{user_uuid}/sessions` | `admin` | Full session; anonymous NO |

## GET /users

The staff and subject register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L165).

## POST /users

Create User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- This provisioning route creates staff accounts; data_subject uses the public registration flow.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L183).

## GET /users/collection-owners

Active DCOs and RCOs, for source ownership.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `RequireStaff`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(*STAFF_ROLES))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- All staff may read the limited lookup of active DCO/RCO owners; this does not expose the full account register.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L148).

## GET /users/staff

Active staff, for naming a processor's respondent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L133).

## GET /users/{user_uuid}

Get User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L298).

## PATCH /users/{user_uuid}

Update User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L304).

## POST /users/{user_uuid}/deactivate

Deactivate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- An administrator cannot apply this operation to their own account.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L378).

## POST /users/{user_uuid}/invite

Send the invitation again.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- Only a pending invited staff account is eligible.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L273).

## POST /users/{user_uuid}/mfa/reset

Reset Mfa.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L448).

## GET /users/{user_uuid}/person-type-history

Person Type History.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L466).

## POST /users/{user_uuid}/reactivate

Reactivate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L417).

## POST /users/{user_uuid}/role

Change a role.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- An administrator cannot apply this operation to their own account.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L351).

## DELETE /users/{user_uuid}/sessions

Force logout.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L432).
