# API documentation

Reference for **253 operations over 221 paths**, grouped by OpenAPI module/tag.

## How to read an endpoint

Every endpoint uses the requested order:

1. **API** — method, path, operation ID, access and behavior.
2. **Validation** — path/query/header/cookie parameters and constraints.
3. **Payload** — request content type, schema and generated shape, when a body exists.
4. **Response** — status codes, content types, schemas and generated shapes.

Generated values are structural examples, not production credentials or semantically valid business records. Service-layer validation can add rules beyond those expressible in OpenAPI.

## Modules

| Module | Operations | File |
|---|---:|---|
| Audit | 7 | [`modules/audit/api.md`](modules/audit/api.md) |
| Auth | 14 | [`modules/auth/api.md`](modules/auth/api.md) |
| Consent | 12 | [`modules/consent/api.md`](modules/consent/api.md) |
| Cross-Border Transfers | 3 | [`modules/cross_border_transfers/api.md`](modules/cross_border_transfers/api.md) |
| Dashboard | 3 | [`modules/dashboard/api.md`](modules/dashboard/api.md) |
| Delegations | 6 | [`modules/delegations/api.md`](modules/delegations/api.md) |
| Exchange | 19 | [`modules/exchange/api.md`](modules/exchange/api.md) |
| Legal Holds | 3 | [`modules/legal_holds/api.md`](modules/legal_holds/api.md) |
| Me | 26 | [`modules/me/api.md`](modules/me/api.md) |
| Messages | 5 | [`modules/messages/api.md`](modules/messages/api.md) |
| Notices | 22 | [`modules/notices/api.md`](modules/notices/api.md) |
| Projects | 27 | [`modules/projects/api.md`](modules/projects/api.md) |
| Public Consent | 6 | [`modules/public_consent/api.md`](modules/public_consent/api.md) |
| Public Information | 10 | [`modules/public_information/api.md`](modules/public_information/api.md) |
| Registry | 23 | [`modules/registry/api.md`](modules/registry/api.md) |
| Rights | 44 | [`modules/rights/api.md`](modules/rights/api.md) |
| System | 5 | [`modules/system/api.md`](modules/system/api.md) |
| Tickets | 5 | [`modules/tickets/api.md`](modules/tickets/api.md) |
| Users | 13 | [`modules/users/api.md`](modules/users/api.md) |

## Roles

See [`roles/README.md`](roles/README.md) for all seven roles, their read/write permissions, row scope, navigation, and enforcement notes.

## Source and regeneration

- API source: `backend/api/openapi.json`
- Role source: `backend/api/src/cmp/core/permissions.py`
- Regenerate: `python3 docs/tools/generate-api-docs.py`

Do not hand-edit generated module or role files; update the API schema or permission matrix and regenerate.
