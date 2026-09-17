# Notices: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

22 operations; 22 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/notices` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/notices/import/template` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| PUT | `/notices/{notice_uuid}` | `dpo`, `rnd_user` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}/checklist` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}/languages` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/notices/{notice_uuid}/languages` | `dpo`, `rnd_user` | Full session; anonymous NO |
| PUT | `/notices/{notice_uuid}/languages/{code}` | `dpo`, `rnd_user` | Full session; anonymous NO |
| POST | `/notices/{notice_uuid}/languages/{code}/approve` | `dpo` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}/preview` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/notices/{notice_uuid}/publish` | `dpo` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}/purposes` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/notices/{notice_uuid}/purposes` | `dpo`, `rnd_user` | Full session; anonymous NO |
| POST | `/notices/{notice_uuid}/purposes/activate` | `dpo` | Full session; anonymous NO |
| DELETE | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | `dpo`, `rnd_user` | Full session; anonymous NO |
| PUT | `/notices/{notice_uuid}/purposes/{purpose_uuid}` | `dpo`, `rnd_user` | Full session; anonymous NO |
| GET | `/notices/{notice_uuid}/versions` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/notices` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/notices` | `dpo`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/notices/copy` | `dpo`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/notices/import` | `dpo`, `rnd_user` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/notices/import/validate` | `dpo`, `rnd_user` | Full session; anonymous NO |

## GET /notices

All notices in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L206).

## GET /notices/import/template

The notice document to fill in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L725).

## GET /notices/{notice_uuid}

Get Notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L303).

## PUT /notices/{notice_uuid}

Draft only.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L309), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## GET /notices/{notice_uuid}/checklist

Checklist.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L562).

## GET /notices/{notice_uuid}/languages

List Languages.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L492).

## POST /notices/{notice_uuid}/languages

Add Language.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L511), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## PUT /notices/{notice_uuid}/languages/{code}

Draft only.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L529), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## POST /notices/{notice_uuid}/languages/{code}/approve

Approve Language.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- DPO-only action; publication/activation also requires valid notice content, approved language and lifecycle checks.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L548).

## GET /notices/{notice_uuid}/preview

Preview.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L569).

## POST /notices/{notice_uuid}/publish

Publish.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- DPO-only action; publication/activation also requires valid notice content, approved language and lifecycle checks.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L580).

## GET /notices/{notice_uuid}/purposes

List Notice Purposes.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L335).

## POST /notices/{notice_uuid}/purposes

Attach Purpose.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L342), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## POST /notices/{notice_uuid}/purposes/activate

Activate every draft purpose on this notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `RequireDPO`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO))]`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- DPO-only action; publication/activation also requires valid notice content, approved language and lifecycle checks.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L687).

## DELETE /notices/{notice_uuid}/purposes/{purpose_uuid}

Draft only.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L483), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## PUT /notices/{notice_uuid}/purposes/{purpose_uuid}

Narrow Rule 3(b) for this notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L387), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## GET /notices/{notice_uuid}/versions

Notice Versions.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L328).

## GET /projects/{project_uuid}/notices

List Notices.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `NoticeReader`.
- **Resolved gate:** `RequireResource(notice, write=False)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L233).

## POST /projects/{project_uuid}/notices

Create Notice.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L246), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## POST /projects/{project_uuid}/notices/copy

Copy an existing notice into this project.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L274), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## POST /projects/{project_uuid}/notices/import

Create the notice and its purposes from an uploaded document.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L664), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).

## POST /projects/{project_uuid}/notices/import/validate

Dry run - reports what the document says, writes nothing.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | OWN | NO |

- **Who:** `dpo`, `rnd_user`.
- **Route guard:** `NoticeAuthor`.
- **Resolved gate:** `RequireResource(notice, write=True)`.
- **Rules:** Notice and parent project must be within project scope: DPO all; R&D own project; collection roles their permitted projects. Read permission alone does not permit editing.
- Authors are DPO and R&D owner only. Service checks restrict draft editing and require a new version for material changes.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/notices.py#L642), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/domain/notices/service.py#L1).
