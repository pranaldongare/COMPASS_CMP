# Portal address: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

2 operations; 2 appear in the existing OpenAPI/API docs. Added 2026-11-16 (migration 0072); evidence links point at `HEAD`.

Every link the platform hands out to a data principal - a consent link copied in the console, the public link for reporting a breach, the links in its mail - starts with the portal's address. The administrator keeps that address here, so it can follow a deployment whose IP changes before it has a domain name, without a file edited or a service restarted. Until one is set the configured address is used.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/portal-address` | `admin` | Full session; anonymous NO |
| PUT | `/portal-address` | `admin` | Full session; anonymous NO |

## GET /portal-address

The address portal links start with.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `PortalAddressReader`.
- **Resolved gate:** `RequireResource(portal_address)`.
- **Rules:** Resource `portal_address`, the administrator's alone (0072): every other role is answered 403. The address links to the data principal's portal start with: the one set, the configured one (`PUBLIC_BASE_URL`), which of them is in use, and who last set it and when. Every signed-in session is told the address in use by `GET /auth/me` (`portal_url`), which is not this route.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/portal_address.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/portal_address/__init__.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/portal_address.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)

## PUT /portal-address

Set the address portal links start with.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | NO | NO |

- **Who:** `admin`.
- **Route guard:** `PortalAddressWriter`.
- **Resolved gate:** `RequireResource(portal_address, write=True)`.
- **Rules:** Resource `portal_address`, the administrator's alone (0072): every other role is answered 403. `portal_url` must be http or https, a host and optionally a port, with no path, query, fragment or user (422, field `portal_url`); null or empty goes back to the configured address. Takes effect in the saving process at once and in every other process, the worker included, within fifteen seconds; nothing is restarted. Recorded on the trail (`portal_address.changed`) with the address before and after.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/portal_address.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/portal_address/__init__.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/portal_address.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py)
