# Module-by-module access overview

[Guide](README.md) · [Full endpoint matrix](endpoint_permissions.md)

Each cell is **GET / non-GET endpoint counts** for which that role is eligible. This is HTTP-method grouping, not an assertion that every POST writes business data (for example, preview/validation). Conditional access counts are included. A nonzero count does not grant every endpoint in the module. Public operations are counted for every role because a role is not required.

| Module | Endpoints | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Audit](modules/audit.md) | 7 | 7 / 0 | 7 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| [Auth](modules/auth.md) | 14 | 2 / 12 | 2 / 12 | 2 / 12 | 2 / 12 | 2 / 12 | 2 / 12 | 2 / 12 |
| [Consent](modules/consent.md) | 12 | 10 / 2 | 0 / 0 | 10 / 2 | 10 / 2 | 10 / 2 | 6 / 0 | 0 / 0 |
| [Dashboard](modules/dashboard.md) | 3 | 2 / 1 | 2 / 0 | 2 / 1 | 2 / 0 | 2 / 0 | 2 / 0 | 2 / 0 |
| [Delegations](modules/delegations.md) | 5 | 3 / 2 | 3 / 2 | 2 / 2 | 2 / 1 | 2 / 1 | 2 / 1 | 2 / 0 |
| [Exchange](modules/exchange.md) | 19 | 16 / 3 | 3 / 0 | 16 / 3 | 15 / 3 | 15 / 3 | 9 / 0 | 3 / 0 |
| [Legal holds](modules/legal_holds.md) | 3 | 1 / 2 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| [Me](modules/me.md) | 26 | 1 / 5 | 1 / 5 | 1 / 4 | 1 / 4 | 1 / 4 | 1 / 4 | 16 / 10 |
| [Messages](modules/messages.md) | 5 | 2 / 3 | 2 / 3 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| [Notices](modules/notices.md) | 22 | 9 / 13 | 0 / 0 | 9 / 0 | 9 / 0 | 9 / 0 | 9 / 3 | 0 / 0 |
| [Projects](modules/projects.md) | 27 | 13 / 9 | 0 / 0 | 12 / 5 | 12 / 7 | 12 / 5 | 13 / 10 | 0 / 0 |
| [Public Consent](modules/public_consent.md) | 6 | 2 / 3 | 2 / 3 | 2 / 3 | 2 / 3 | 2 / 3 | 2 / 3 | 2 / 4 |
| [Public Information](modules/public_information.md) | 10 | 3 / 7 | 3 / 7 | 3 / 7 | 3 / 7 | 3 / 7 | 3 / 7 | 3 / 7 |
| [Registry](modules/registry.md) | 23 | 10 / 13 | 10 / 9 | 8 / 4 | 8 / 4 | 8 / 4 | 8 / 0 | 1 / 0 |
| [Rights](modules/rights.md) | 44 | 12 / 31 | 12 / 32 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| [System](modules/system.md) | 8 | 8 / 0 | 8 / 0 | 8 / 0 | 8 / 0 | 8 / 0 | 8 / 0 | 8 / 0 |
| [Tickets](modules/tickets.md) | 5 | 3 / 2 | 3 / 2 | 3 / 2 | 3 / 2 | 3 / 2 | 3 / 2 | 0 / 0 |
| [Users](modules/users.md) | 13 | 5 / 0 | 5 / 8 | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 | 0 / 0 |


System includes three registered routes omitted from OpenAPI. Read the endpoint conditions for imports, delegations, public flows and rights requests before treating any count as broad access.
