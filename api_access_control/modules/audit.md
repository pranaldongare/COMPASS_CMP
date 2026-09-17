# Audit: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

3 operations; 3 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/audit` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/verify` | `dpo`, `admin` | Full session; anonymous NO |
| GET | `/audit/{log_uuid}` | `dpo`, `admin` | Full session; anonymous NO |

## GET /audit

Search the trail.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `RequireDPOorAdmin`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireRole(Role.DPO, Role.ADMIN))]`.
- **Rules:** DPO/Admin may inspect the audit trail and verify its chain. No API to edit audit entries is registered.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/cmp_backend/src/cmp/api/routers/v1/audit.py#L66).

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
