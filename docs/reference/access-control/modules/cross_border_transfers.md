# Cross-border transfers: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

3 operations; 3 appear in the existing OpenAPI/API docs. Added with S2-04; evidence links point at `HEAD`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/restricted-countries` | `dpo`, `admin` | Full session; anonymous NO |
| POST | `/restricted-countries` | `dpo` | Full session; anonymous NO |
| POST | `/restricted-countries/{country_uuid}/lift` | `dpo` | Full session; anonymous NO |

## GET /restricted-countries

The restricted list.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | ALL | NO | NO | NO | NO | NO |

- **Who:** `dpo`, `admin`.
- **Route guard:** `TransferListReader`.
- **Resolved gate:** `RequireResource(restricted_country)`.
- **Rules:** The Government's s.16 restricted-country list (resource `restricted_country`, S2-04): the DPO keeps it, the administrator reads it. Data, not code - a country, the notification that lists it, lifted once; one active listing per country, and India cannot be listed. Every export is checked against it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/transfers.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/exchange/transfer.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /restricted-countries

Restrict transfers to a country.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `TransferListWriter`.
- **Resolved gate:** `RequireResource(restricted_country, write=True)`.
- **Rules:** The Government's s.16 restricted-country list (resource `restricted_country`, S2-04): the DPO keeps it, the administrator reads it. Data, not code - a country, the notification that lists it, lifted once; one active listing per country, and India cannot be listed. Every export is checked against it. A country already listed is 409 `already_restricted`.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/transfers.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/exchange/transfer.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /restricted-countries/{country_uuid}/lift

Lift a restriction.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO |

- **Who:** `dpo`.
- **Route guard:** `TransferListWriter`.
- **Resolved gate:** `RequireResource(restricted_country, write=True)`.
- **Rules:** The Government's s.16 restricted-country list (resource `restricted_country`, S2-04): the DPO keeps it, the administrator reads it. Data, not code - a country, the notification that lists it, lifted once; one active listing per country, and India cannot be listed. Every export is checked against it. Lifting twice is 409 `restriction_lifted`.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/transfers.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/exchange/transfer.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).
