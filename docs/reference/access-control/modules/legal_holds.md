# Legal holds: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

3 operations; 3 appear in the existing OpenAPI/API docs. Added with S2-03; evidence links point at `HEAD`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/legal-holds` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/legal-holds` | `dpo`, `legal` | Full session; anonymous NO |
| POST | `/legal-holds/{hold_uuid}/release` | `dpo`, `legal` | Full session; anonymous NO |

## GET /legal-holds

Holds, active first.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `LegalHoldReader`.
- **Resolved gate:** `RequireResource(legal_hold)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `legal_hold`, S2-03). A hold covers one asset or one person, stops the erasure executor on every item it covers, and is placed once and released once; the reason is sealed. Other roles are refused by the matrix. Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/legal_holds.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/holds.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /legal-holds

Stop erasure of an asset or a person.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `LegalHoldWriter`.
- **Resolved gate:** `RequireResource(legal_hold, write=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `legal_hold`, S2-03). A hold covers one asset or one person, stops the erasure executor on every item it covers, and is placed once and released once; the reason is sealed. Other roles are refused by the matrix. Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/legal_holds.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/holds.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /legal-holds/{hold_uuid}/release

Release a hold; what it stopped carries on.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ALL | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `dpo`, `legal`.
- **Route guard:** `LegalHoldWriter`.
- **Resolved gate:** `RequireResource(legal_hold, write=True)`.
- **Rules:** The officers' alone - the DPO's and the Legal PoC's, each on its own office's records (resource `legal_hold`, S2-03). A hold covers one asset or one person, stops the erasure executor on every item it covers, and is placed once and released once; the reason is sealed. Other roles are refused by the matrix. Releasing a released hold is 409 `hold_released`. Each office's officer on its own office's records (0055): the DPO on the DPO office's, the Legal PoC on the Legal office's; a rights request in the shared intake (no office) is visible to both until one claims it.
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/legal_holds.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/rights/holds.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).
