# Users: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

17 operations; 17 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/users` | `dpo`, `legal`, `admin` | Full session; anonymous NO |
| POST | `/users` | `admin` | Full session; anonymous NO |
| GET | `/users/collection-owners` | `admin`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/users/staff` | `admin`, `dpo` | Full session; anonymous NO |
| GET | `/users/{user_uuid}` | `dpo`, `legal`, `admin` | Full session; anonymous NO |
| PATCH | `/users/{user_uuid}` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/deactivate` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/invite` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/mfa/reset` | `admin` | Full session; anonymous NO |
| GET | `/users/{user_uuid}/person-type-history` | `dpo`, `legal`, `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/reactivate` | `admin` | Full session; anonymous NO |
| POST | `/users/{user_uuid}/role` | `admin` | Full session; anonymous NO |
| DELETE | `/users/{user_uuid}/sessions` | `admin` | Full session; anonymous NO |
| PUT | `/users/{user_uuid}/processors` | `admin` | Full session; anonymous NO |
| GET | `/users/hr-pocs` | `legal`, `admin` | Full session; anonymous NO |
| PUT | `/users/{user_uuid}/categories` | `admin` | Full session; anonymous NO |
| GET | `/offices` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user` | Full session; anonymous NO |

## GET /users

The staff and subject register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L165).

## POST /users

Create User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- This provisioning route creates staff accounts; data_subject uses the public registration flow.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L183).

## GET /users/collection-owners

Active DCOs and RCOs, for source ownership.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | NO | NO |

- **Who:** `admin`, `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `RequireStaff`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(*STAFF_ROLES))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- All staff may read the limited lookup of active DCO/RCO owners; this does not expose the full account register.
- `processor`: only those who collect for that processor - the people one of its sources can be handed to. (0050, 2026-10-09)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L148).

## GET /users/staff

Active staff, for naming a processor's respondent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`, `dpo`.
- **Route guard:** `Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L133).

## GET /users/{user_uuid}

Get User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L298).

## PATCH /users/{user_uuid}

Update User.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L304).

## POST /users/{user_uuid}/deactivate

Deactivate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- An administrator cannot apply this operation to their own account.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L378).

## POST /users/{user_uuid}/invite

Send the invitation again.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- Only a pending invited staff account is eligible.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L273).

## POST /users/{user_uuid}/mfa/reset

Reset Mfa.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L448).

## GET /users/{user_uuid}/person-type-history

Person Type History.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L466).

## POST /users/{user_uuid}/reactivate

Reactivate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L417).

## POST /users/{user_uuid}/role

Change a role.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- An administrator cannot apply this operation to their own account.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L351).

## DELETE /users/{user_uuid}/sessions

Force logout.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** Account register: DPO/Admin read, Admin provisions or changes accounts. Access is not inherited merely because another role is staff.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/users.py#L432).

## PUT /users/{user_uuid}/processors

Set the processors a DCO or an RCO collects for.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** The whole set: what is not named is taken away. Only for a DCO (third-party processors) or an RCO (in-house), 422 otherwise; a processor whose sources they are still accountable for is not taken away (409 `processor_still_held`). The trail records `user.processors_set` with the processor uuids before and after. (2026-10-09)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/users.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/users/service.py).
## GET /users/hr-pocs

Active HR PoCs, for a picker.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `legal`, `admin`.
- **Route guard:** `RequireRole(LEGAL, ADMIN)`.
- **Resolved gate:** `Annotated[Any, Depends(RequireRole(Role.LEGAL, Role.ADMIN))]`.
- **Rules:** Active `hr_user` accounts; `category` keeps those assigned to it (404 for a category the caller cannot read). (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/users.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py).

## PUT /users/{user_uuid}/categories

Set the categories an HR PoC runs activities in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `RequireAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.ADMIN))]`.
- **Rules:** The whole set. Only for an HR PoC (422 otherwise); a retired category is refused as a new assignment and kept as an existing one. The trail records `user.categories_set` with the codes before and after, on the Legal office's trail. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/users.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py).
## GET /offices

The offices an account can work in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO | NO | ALL | ALL |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `legal`, `hr_user`.
- **Route guard:** `RequireStaff`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(*STAFF_ROLES))]`.
- **Rules:** Every member of staff (ADR 0032): the two offices with their codes and names, for the administrator's account form and the console's labels; no personal data.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/offices.py).
