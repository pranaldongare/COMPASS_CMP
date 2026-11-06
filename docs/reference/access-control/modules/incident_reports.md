# Incident reports: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

2 operations; 2 appear in the existing OpenAPI/API docs. Added with the public link, 2026-11-06; evidence links point at `HEAD`.

The public link ([ADR 0037](../../../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)): anybody may report an incident, with no account, once they have proved their email by a code. The report waits in the shared intake, on no clock, under `/breaches/intake`, for one of the two officers to claim or dismiss it. The routes here take a report and give back its number; nothing that is in it can be read back through them.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| POST | `/incident-reports/code` | public | No session required; anonymous COND |
| POST | `/incident-reports` | public | No session required; anonymous COND |

## POST /incident-reports/code

A code to the address given.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** Anyone may ask. A code to the address typed, to prove it; nothing is stored. Limited per address and per contact; the answer is the same for any address. (0058, ADR 0037)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/public/incident_reports.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).

## POST /incident-reports

Report an incident, with the code.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC | PUBLIC |

- **Who:** public.
- **Route guard:** `Public; no session dependency`.
- **Resolved gate:** `Public; no session dependency`.
- **Rules:** Anyone with the code sent to the address they give (400 otherwise): no account and no anonymous report. Name, title and what happened are required; the rest may be left. The report takes its `INC-` number and waits in the shared intake on no clock; both offices are told, and the reporter is given the number and nothing else. Submission is not access to anything. (0058, ADR 0037)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/public/incident_reports.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/breach/intake.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/dependencies/authorization.py).
