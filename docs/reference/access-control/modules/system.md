# System: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

8 operations; 5 appear in the existing OpenAPI/API docs. Snapshot `1757d50`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/` | Public; no role required | No session required; anonymous YES |
| GET | `/health` | Public; no role required | No session required; anonymous YES |
| GET | `/health/live` | Public; no role required | No session required; anonymous YES |
| GET | `/health/ready` | Public; no role required | No session required; anonymous YES |
| GET | `/meta/data-categories` | Public; no role required | No session required; anonymous YES |
| GET | `/meta/enums` | Public; no role required | No session required; anonymous YES |
| GET | `/meta/version` | Public; no role required | No session required; anonymous YES |
| GET | `/ready` | Public; no role required | No session required; anonymous YES |

## GET /

Index.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L104).
- **Inventory:** Registered in source but deliberately excluded from OpenAPI.

## GET /health

Liveness.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L135).

## GET /health/live

Health Live.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L143).
- **Inventory:** Registered in source but deliberately excluded from OpenAPI.

## GET /health/ready

Health Ready.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L174).
- **Inventory:** Registered in source but deliberately excluded from OpenAPI.

## GET /meta/data-categories

Controlled vocabulary.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L336).

## GET /meta/enums

All enum values for dropdowns.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L299).

## GET /meta/version

Version.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L186).

## GET /ready

Readiness.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** Public; no role required.
- **Route guard:** `Public; no session dependency`.
- **Rules:** No application session or role is required. Availability can still depend on deployment/network configuration.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/1757d5069ba723f260c88c45419c1286261a127f/backend/api/src/cmp/api/routers/v1/system.py#L148).
