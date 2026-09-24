# Exchange: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

19 operations; 19 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/assets/{asset_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/assets/{asset_uuid}/subjects` | `dpo`, `dco` | Full session; anonymous NO |
| GET | `/collections` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/collections/{collection_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/collections/{collection_uuid}/assets` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/collections/{collection_uuid}/exceptions` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/exports` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/exports/{export_uuid}` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/exports/{export_uuid}/download` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/exports/{export_uuid}/lines` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/imports` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| POST | `/imports` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/imports/template` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/imports/validate` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/imports/{batch_uuid}` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/imports/{batch_uuid}/errors` | `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/collections` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/exports` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/projects/{project_uuid}/exports` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |

## GET /assets/{asset_uuid}

Get Asset.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L498), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /assets/{asset_uuid}/subjects

One row per subject, bystanders included.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | NO | NO | NO | NO |

- **Who:** `dpo`, `dco`.
- **Route guard:** `CurrentUser`.
- **Additional role checks:** `principal.role not in (Role.DPO, Role.DCO)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- Explicitly DPO/DCO only. DCO Admin and RCO are refused even though they can read collection/asset metadata.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L509), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /collections

All collections, with their reconciliation gap.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L151), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /collections/{collection_uuid}

Get Collection.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L447), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /collections/{collection_uuid}/assets

Collection Assets.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L464), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /collections/{collection_uuid}/exceptions

Declared against mapped - the control that makes direct collection workable.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L480), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /exports

The disclosure register.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportReader`.
- **Resolved gate:** `RequireResource(export, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L123), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /exports/{export_uuid}

Get Export.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportReader`.
- **Resolved gate:** `RequireResource(export, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L205), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /exports/{export_uuid}/download

Download Export.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportReader`.
- **Resolved gate:** `RequireResource(export, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L216), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /exports/{export_uuid}/lines

Who was in this file (s.11(1)(b)).

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportReader`.
- **Resolved gate:** `RequireResource(export, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L262), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /imports

List Imports.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- All full-session roles pass the route. Project-linked batches follow import scope: DPO all; DCO/DCO Admin/RCO scoped; R&D own projects; Admin/principal none. However, b.project_id IS NULL is allowed for EVERY signed-in role, including Admin and data_subject; list, detail and error-report lookups share this exception.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L374), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L380), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L405).

## POST /imports

Create Import.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ImportActor`.
- **Resolved gate:** `RequireResource(import, write=True)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- Import validation rules apply; ingest requires a reachable project and valid source/export data.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L353), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/exchange/service.py#L526).

## GET /imports/template

A manifest file to fill in.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ImportActor`.
- **Resolved gate:** `RequireResource(import, write=True)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L292), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## POST /imports/validate

Dry run - nothing is written.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ImportActor`.
- **Resolved gate:** `RequireResource(import, write=True)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- Import validation rules apply; ingest requires a reachable project and valid source/export data.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L315), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/exchange/service.py#L526).

## GET /imports/{batch_uuid}

Get Import.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- All full-session roles pass the route. Project-linked batches follow import scope: DPO all; DCO/DCO Admin/RCO scoped; R&D own projects; Admin/principal none. However, b.project_id IS NULL is allowed for EVERY signed-in role, including Admin and data_subject; list, detail and error-report lookups share this exception.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L395), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L380), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L405).

## GET /imports/{batch_uuid}/errors

Import Errors.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| COND | COND | COND | COND | COND | COND | COND |

- **Who:** `dpo`, `admin`, `dco`, `dco_admin`, `rco`, `rnd_user`, `data_subject`.
- **Route guard:** `CurrentUser`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- All full-session roles pass the route. Project-linked batches follow import scope: DPO all; DCO/DCO Admin/RCO scoped; R&D own projects; Admin/principal none. However, b.project_id IS NULL is allowed for EVERY signed-in role, including Admin and data_subject; list, detail and error-report lookups share this exception.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L407), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L380), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L405).

## GET /projects/{project_uuid}/collections

List Collections.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `CollectionReader`.
- **Resolved gate:** `RequireResource(collection, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L431), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## GET /projects/{project_uuid}/exports

List Exports.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportReader`.
- **Resolved gate:** `RequireResource(export, write=False)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L196), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23).

## POST /projects/{project_uuid}/exports

Generate Export.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `ExportActor`.
- **Resolved gate:** `RequireResource(export, write=True)`.
- **Rules:** Exports/collections/assets use repository scope: DPO all; collection roles permitted projects; R&D own-created projects where its resource grant allows reading. Each row's destination - the processor running its site - is checked under s.16 first (S2-04): an unknown location, a restricted country, or a granted purpose not permitted cross-border refuses the whole export with 422 `transfer_refused`, recorded in its own transaction.
- Source consent rows for a new export are selected using the caller’s site scope.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/exchange.py#L174), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/exchange.py#L23), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/domain/exchange/service.py#L49).
