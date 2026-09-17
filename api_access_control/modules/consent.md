# Consent: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

12 operations; 12 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/consents` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}/assets` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}/grants` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/links` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/links/{link_uuid}` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/links/{link_uuid}/remint` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| POST | `/links/{link_uuid}/revoke` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/links/{link_uuid}/stats` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/consents` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/consents/summary` | `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/links` | `dpo`, `dco`, `dco_admin`, `rco` | Full session; anonymous NO |

## GET /consents

All consents in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L201), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}

Get Consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L393), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}/assets

Which assets contain this person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L419), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}/grants

Consent Grants.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L404), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /links

All links in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L180), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /links/{link_uuid}

Get Link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L234), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## POST /links/{link_uuid}/remint

Replace a link with a fresh one.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- Uses LinkReader; every currently admitted link role also has the matrix write grant. Remint/revoke are still mutations, not read-only calls.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L263), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## POST /links/{link_uuid}/revoke

Revoke Link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- Uses LinkReader; every currently admitted link role also has the matrix write grant. Remint/revoke are still mutations, not read-only calls.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L335), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /links/{link_uuid}/stats

Link Stats.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L245), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/consents

List Consents.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L356), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/consents/summary

Consents Summary.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- After a project-scope check this endpoint returns project-wide counts; it is not a list of individually scoped consent rows.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L384), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/links

List Links.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/consents.py#L224), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/db/repositories/consent.py#L21).
