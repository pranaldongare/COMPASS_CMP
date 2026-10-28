# Consent: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

15 operations; 15 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/consents` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}/assets` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}/grants` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/links` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| GET | `/links/{link_uuid}` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| POST | `/links/{link_uuid}/remint` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| POST | `/links/{link_uuid}/revoke` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| GET | `/links/{link_uuid}/stats` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/consents` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/consents/summary` | `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user` | Full session; anonymous NO |
| GET | `/projects/{project_uuid}/links` | `dco`, `dco_admin`, `dpo`, `rco` | Full session; anonymous NO |
| GET | `/consents/{consent_uuid}/record` | `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user` | Full session; anonymous NO |
| GET | `/consent-records` | `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user` | Full session; anonymous NO |
| POST | `/consent-records` | `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user` | Full session; anonymous NO |

## GET /consents

All consents in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L201), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}

Get Consent.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L393), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}/assets

Which assets contain this person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L419), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /consents/{consent_uuid}/grants

Consent Grants.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L404), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /links

All links in scope.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L180), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /links/{link_uuid}

Get Link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L234), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## POST /links/{link_uuid}/remint

Replace a link with a fresh one.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- Uses LinkReader; every currently admitted link role also has the matrix write grant. Remint/revoke are still mutations, not read-only calls.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L263), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## POST /links/{link_uuid}/revoke

Revoke Link.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- Uses LinkReader; every currently admitted link role also has the matrix write grant. Remint/revoke are still mutations, not read-only calls.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L335), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /links/{link_uuid}/stats

Link Stats.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L245), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/consents

List Consents.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L356), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/consents/summary

Consents Summary.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | OWN | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`, `rnd_user`.
- **Route guard:** `ConsentReader`.
- **Resolved gate:** `RequireResource(consent, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- R&D currently passes the consent reader guard for individual rows, grants and assets as well as summaries. The static matrix comment saying “summary counts only” is not an endpoint restriction here.
- After a project-scope check this endpoint returns project-wide counts; it is not a list of individually scoped consent rows.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L384), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).

## GET /projects/{project_uuid}/links

List Links.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dco`, `dco_admin`, `dpo`, `rco`.
- **Route guard:** `LinkReader`.
- **Resolved gate:** `RequireResource(link, write=False)`.
- **Rules:** Links and individual consent rows are scoped to the collection site: DPO all; DCO/RCO sites they run or cover; DCO Admin non-in-house sites; R&D own-created projects (consent reads only).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/consents.py#L224), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/db/repositories/consent.py#L21).
## GET /consents/{consent_uuid}/record

The consent record as a PDF, for audit.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user`.
- **Route guard:** `RecordReader`.
- **Resolved gate:** `Depends(RequireRole(Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.LEGAL, Role.HR_USER))`.
- **Rules:** Staff in scope only (ADR 0031): a consent in the caller's read scope of consents, within the caller's office; name and one masked contact; every download audited. The administrator and the R&D User are refused by the route.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/consents.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/consent/record.py).

## GET /consent-records

Consent records as PDFs in a ZIP, with a manifest, for a downstream store.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user`.
- **Route guard:** `RecordReader`.
- **Resolved gate:** `Depends(RequireRole(Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.LEGAL, Role.HR_USER))`.
- **Rules:** Staff in scope only (ADR 0031): a consent in the caller's read scope of consents, within the caller's office; name and one masked contact; every download audited. The administrator and the R&D User are refused by the route. A ZIP with a manifest; the filters select within scope only.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/consents.py).

## POST /consent-records

The consent records a list of consent IDs names, as PDFs in a ZIP.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | SCOPED | SCOPED | SCOPED | NO | NO | NO | ALL | SCOPED |

- **Who:** `dpo`, `dco`, `dco_admin`, `rco`, `legal`, `hr_user`.
- **Route guard:** `RecordReader`.
- **Resolved gate:** `Depends(RequireRole(Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.LEGAL, Role.HR_USER))`.
- **Rules:** Staff in scope only (ADR 0031): a consent in the caller's read scope of consents, within the caller's office; name and one masked contact; every download audited. The administrator and the R&D User are refused by the route. An ID outside scope is listed in the manifest as not found, never fetched.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/consents.py).
