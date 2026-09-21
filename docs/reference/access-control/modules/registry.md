# Registry: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

23 operations; 23 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/processors` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/processors` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/processors/{processor_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/processors/{processor_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/processors/{processor_uuid}/respondents` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/processors/{processor_uuid}/respondents` | `dpo`, `admin` | Full session; anonymous NO |
| DELETE | `/processors/{processor_uuid}/respondents/{respondent_uuid}` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/processors/{processor_uuid}/suspend` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/purposes` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/purposes` | `dpo` | Full session; anonymous NO |
| GET | `/purposes/{purpose_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/purposes/{purpose_uuid}` | `dpo` | Full session; anonymous NO |
| POST | `/purposes/{purpose_uuid}/activate` | `dpo` | Full session; anonymous NO |
| POST | `/purposes/{purpose_uuid}/retire` | `dpo` | Full session; anonymous NO |
| GET | `/purposes/{purpose_uuid}/usage` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/purposes/{purpose_uuid}/versions` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/sources` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/sources` | `dpo`, `admin`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/sources/{source_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/sources/{source_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/sources/{source_uuid}/batches` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| PUT | `/sources/{source_uuid}/owner` | `dpo`, `admin`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/sources/{source_uuid}/suspend` | `dpo`, `admin`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |

## GET /processors

List Processors.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor'))]`.
- **Resolved gate:** `RequireResource(processor, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L352).

## POST /processors

Create Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor', write=True))]`.
- **Resolved gate:** `RequireResource(processor, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L366).

## GET /processors/{processor_uuid}

Get Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor'))]`.
- **Resolved gate:** `RequireResource(processor, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L506).

## PUT /processors/{processor_uuid}

Update Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor', write=True))]`.
- **Resolved gate:** `RequireResource(processor, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L518).

## GET /processors/{processor_uuid}/respondents

Who answers a rights-request ticket for this processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor'))]`.
- **Resolved gate:** `RequireResource(processor, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L398).

## POST /processors/{processor_uuid}/respondents

Name a respondent for this processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L415).

## DELETE /processors/{processor_uuid}/respondents/{respondent_uuid}

Remove a respondent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L480).

## POST /processors/{processor_uuid}/suspend

Suspend Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('processor', write=True))]`.
- **Resolved gate:** `RequireResource(processor, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L544).

## GET /purposes

List Purposes.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ReadRegistry`.
- **Resolved gate:** `RequireResource(purpose, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L134).

## POST /purposes

Create Purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L151).

## GET /purposes/{purpose_uuid}

Get Purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ReadRegistry`.
- **Resolved gate:** `RequireResource(purpose, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L174).

## PUT /purposes/{purpose_uuid}

Draft only.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L183).

## POST /purposes/{purpose_uuid}/activate

Activate Purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L207).

## POST /purposes/{purpose_uuid}/retire

Retire Purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L225).

## GET /purposes/{purpose_uuid}/usage

Notices referencing this purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L274).

## GET /purposes/{purpose_uuid}/versions

Purpose Versions.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L263).

## GET /sources

List Sources.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source'))]`.
- **Resolved gate:** `RequireResource(data_source, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L616).

## POST /sources

Create Source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | NO | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source', write=True))]`.
- **Resolved gate:** `RequireResource(data_source, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- DCO must choose a third-party processor; RCO must choose an in-house processor. DPO/Admin/DCO Admin are not constrained by that actor-type helper. R&D is denied by the write grant.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L664).

## GET /sources/{source_uuid}

Get Source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | ALL | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source'))]`.
- **Resolved gate:** `RequireResource(data_source, write=False)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L746).

## PUT /sources/{source_uuid}

Update Source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | NO | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source', write=True))]`.
- **Resolved gate:** `RequireResource(data_source, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- Current handler resolves a source by UUID without caller ownership filtering. All data_source writers can act on any source. Owner assignment validates the target owner’s role, not the actor’s source ownership.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L758).

## GET /sources/{source_uuid}/batches

Source Batches.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- All full-session roles pass the route. Project-linked batches follow import scope: DPO all; DCO/DCO Admin/RCO scoped; R&D own projects; Admin/principal none. However, b.project_id IS NULL is allowed for EVERY signed-in role, including Admin and data_subject; list, detail and error-report lookups share this exception.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L904), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L380), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L405).

## PUT /sources/{source_uuid}/owner

Assign the person accountable for a source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | NO | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source', write=True))]`.
- **Resolved gate:** `RequireResource(data_source, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- Current handler resolves a source by UUID without caller ownership filtering. All data_source writers can act on any source. Owner assignment validates the target owner’s role, not the actor’s source ownership.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L816), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L758).

## POST /sources/{source_uuid}/suspend

Suspend Source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | ALL | ALL | ALL | NO | NO |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `Annotated[Any, Depends(RequireResource('data_source', write=True))]`.
- **Resolved gate:** `RequireResource(data_source, write=True)`.
- **Rules:** Registry access is separate from project ownership. Listing/reading a registry entry does not grant access to the projects using it.
- Current handler resolves a source by UUID without caller ownership filtering. All data_source writers can act on any source. Owner assignment validates the target owner’s role, not the actor’s source ownership.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L885), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/registry.py#L758).
