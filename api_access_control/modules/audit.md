# Audit: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

7 operations; 7 appear in the existing OpenAPI/API docs. Snapshot `1757d50`, amended `c7d3f6b` (2026-09-17) for the four filter, summary, lookup and export endpoints.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/audit` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/verify` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/summary` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/vocabulary` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/lookup` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/export.csv` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/{log_uuid}` | `dpo`, `admin` | Full session; anonymous NO |

## GET /audit

Search the trail.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin may inspect the audit trail and verify its chain. No API to edit audit entries is registered. Since `c7d3f6b` the search also takes `actor_role`, `entity` (a public uuid with `entity_type`, resolved server-side; unknown matches nothing), `event_group` and `q`; the same filters drive the summary and the export.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/audit.py#L66), [search as amended](https://github.com/pranaldongare/COMPASS_CMP/blob/c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa/cmp_backend/src/cmp/api/routers/v1/audit.py#L219).

## GET /audit/summary

The shape of the rows a filter selects.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin only. Counts by event, area, actor role and day over exactly the rows the same filters would list; the filters are validated as on GET /audit (an unknown entity uuid matches nothing).
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa/cmp_backend/src/cmp/api/routers/v1/audit.py#L258).

## GET /audit/vocabulary

What the trail can be filtered by.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin only. Static: every entity type and event type the trail may carry, with labels, and the pickers the console offers. No row data.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa/cmp_backend/src/cmp/api/routers/v1/audit.py#L302).

## GET /audit/lookup

Find a record to filter on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin only. Name search over data principals, staff, consent records, processors, data sources, projects, notices, sites and rights requests, unscoped (the two supervising roles read every row). `kind` must be a known lookup kind, else 422; at most ten answers.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa/cmp_backend/src/cmp/api/routers/v1/audit.py#L310).

## GET /audit/export.csv

Download the rows a filter selects, as CSV.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin only. Newest first, at most 10,000 rows, free-text cells neutralised against spreadsheet formulas. The download is itself recorded in the trail as `audit.exported`, with the filters used and the caller as actor.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa/cmp_backend/src/cmp/api/routers/v1/audit.py#L343).

## GET /audit/verify

Verify the hash chain.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin may inspect the audit trail and verify its chain. No API to edit audit entries is registered.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/audit.py#L99).

## GET /audit/{log_uuid}

Get Entry.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin may inspect the audit trail and verify its chain. No API to edit audit entries is registered.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/audit.py#L125).
