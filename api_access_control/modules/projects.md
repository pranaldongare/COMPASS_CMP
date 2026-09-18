# Projects: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

27 operations; 27 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/approvals` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/approvals/{approval_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/approvals/{approval_uuid}/proof` | `dpo`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects` | `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/projects/{project_uuid}` | `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/approvals` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/approvals` | `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/close` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/history` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/processors` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/processors` | `rnd_user` | Full session; anonymous NO |
| PUT | `/projects/{project_uuid}/processors` | `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/processors/{processor_uuid}/decision` | `dpo` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/sites` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/sites` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/summary` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/transition` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/transitions` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/sites` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/sites/{site_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/sites/{site_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/sites/{site_uuid}/agent` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/sites/{site_uuid}/deactivate` | `dpo` | Full session; anonymous NO |
| PUT | `/sites/{site_uuid}/owner` | `dpo`, `dco_admin`, `rnd_user` | Full session; anonymous NO |
| PUT | `/sites/{site_uuid}/source` | `dpo`, `dco_admin`, `rnd_user` | Full session; anonymous NO |

## GET /approvals

All approvals in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L226), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /approvals/{approval_uuid}

Get Approval.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L537), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /approvals/{approval_uuid}/proof

Download the proof file.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.RND_USER)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Only DPO or the creating R&D user may download approval proof; other collection roles may read approval metadata only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L549), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /projects

List Projects.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L240), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## POST /projects

Create Project.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | OWN | NO |

- **Who:** `rnd_user`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role is not Role.RND_USER`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Only R&D can register a new project; the caller becomes its creator.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L261), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /projects/{project_uuid}

Get Project.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L277), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## PUT /projects/{project_uuid}

Draft only.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | OWN | NO |

- **Who:** `rnd_user`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role is not Role.RND_USER`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Only the creating R&D user; project must be editable in its draft state.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L285), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L327).

## GET /projects/{project_uuid}/approvals

List Approvals.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L481), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## POST /projects/{project_uuid}/approvals

Upload an approval - proof is mandatory (INV-8).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | OWN | NO |

- **Who:** `rnd_user`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role is not Role.RND_USER`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L494), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## POST /projects/{project_uuid}/close

Close Project.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role is not Role.DPO and principal.role not in COLLECTION_OWNERS`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- The service uses project write scope: DCO/RCO must own the primary site/project (or cover its owner), not merely another site.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L460), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L364).

## GET /projects/{project_uuid}/history

Project History.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L330), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /projects/{project_uuid}/processors

List Project Processors.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L362), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## POST /projects/{project_uuid}/processors

Request Project Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | OWN | NO |

- **Who:** `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role is not Role.RND_USER`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Only the R&D owner; adding a processor after approval goes through a request and DPO decision.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L402), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L130).

## PUT /projects/{project_uuid}/processors

Draft only — replaces the set.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | OWN | NO |

- **Who:** `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role is not Role.RND_USER`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Only the R&D owner; the direct replacement path is limited to the editable pre-approval state.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L373), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L289).

## POST /projects/{project_uuid}/processors/{processor_uuid}/decision

Decide Project Processor.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L430), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /projects/{project_uuid}/sites

List Sites.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L600), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## POST /projects/{project_uuid}/sites

Add Site.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.RND_USER)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- The service uses project write scope: DCO/RCO must own the primary site/project (or cover its owner), not merely another site.
- R&D is explicitly allowed to create a site on an own project despite the static site matrix being read-only for R&D; source must be active and under an approved project processor.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L611), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L364), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L688).

## GET /projects/{project_uuid}/summary

Everything a dashboard needs, in one call.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L339), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## POST /projects/{project_uuid}/transition

Transition.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Not every listed role may perform every transition: R&D submits a draft to pending_approval; DPO approves or returns it to draft; DPO/DCO/DCO Admin/RCO close an approved project. (`under_process` is not reachable; nothing transitions to it.) The submission also requires that the Privacy Office has activated every purpose on the notice, which is the one precondition on it the R&D User cannot satisfy themselves.
- The service uses project write scope: DCO/RCO must own the primary site/project (or cover its owner), not merely another site.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L315), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/state_machine.py#L132), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L364).

## GET /projects/{project_uuid}/transitions

What may happen next, and why not.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L304), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82).

## GET /sites

All sites in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L206), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## GET /sites/{site_uuid}

Get Site.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L643), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## PUT /sites/{site_uuid}

Update Site.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- Implemented with ProjectReader plus a scoped site lookup, with no site write-grant check. R&D can update an own-project site. See implementation notes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L654), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## POST /sites/{site_uuid}/agent

Assign the Field Agent and mint the link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ProjectReader`.
- **Resolved gate:** `RequireResource(project, write=False)`.
- **Additional role checks:** `principal.role is not Role.DPO and principal.role not in COLLECTION_OWNERS`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- Only DPO and collection-owner roles can mint the site link; expiry is mandatory and site scope still applies.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L807), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## POST /sites/{site_uuid}/deactivate

Deactivate Site.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L785), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140).

## PUT /sites/{site_uuid}/owner

Name who runs this site, overriding its source.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | SCOPED | NO | OWN | NO |

- **Who:** `dpo`, `dco_admin`, `rnd_user`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.ADMIN, Role.DCO_ADMIN, Role.RND_USER)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- Route admits Admin, but the service then requires project write scope, which is NONE for Admin: Admin cannot complete this operation. R&D is limited to own projects; no extra in-house-only R&D check appears in this path. DCO Admin is subject to both project and site scope.
- New owner must be active and match source type: RCO for in-house, DCO for third-party. A source must already be attached.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L733), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L429), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L502).

## PUT /sites/{site_uuid}/source

Attach the data source that stands here.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | SCOPED | NO | OWN | NO |

- **Who:** `dpo`, `dco_admin`, `rnd_user`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.ADMIN, Role.DCO_ADMIN, Role.RND_USER)`.
- **Rules:** Project scope: DPO all; R&D own-created projects; DCO/RCO assigned project or a project with a site they run (including active cover); DCO Admin third-party projects.
- Site-level lookup further limits DCO/RCO to sites they run; DCO Admin to non-in-house sites; R&D to sites on own projects.
- Route admits Admin, but the service then requires project write scope, which is NONE for Admin: Admin cannot complete this operation. R&D is limited to own projects; no extra in-house-only R&D check appears in this path. DCO Admin is subject to both project and site scope.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/projects.py#L676), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L82), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/projects.py#L140), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L429), [source 5](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/projects/service.py#L502).
