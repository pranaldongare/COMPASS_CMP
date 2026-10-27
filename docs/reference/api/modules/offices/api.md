# Offices API

Generated from `backend/api/openapi.json`. **1 operations.**

For each operation the information is deliberately ordered as **API → Validation → Payload → Response**.

## Contents

1. [`GET /offices`](#1_get_offices)

<a id="1_get_offices"></a>
## 1. `GET /offices` — The offices an account can work in

### API

- **Operation ID:** `list_offices_offices_get`
- **Access:** Role-controlled `offices` operation. See [`../../roles/README.md`](../../roles/README.md).

### Validation

No path, query, header, or cookie parameters are declared for this operation.

### Payload

No request body.

### Response

| Status | Description | Content type | Schema |
|---:|---|---|---|
| `200` | Successful Response | `application/json` | array of [`OfficeOut`](#schema-officeout) |

**Example `200` `application/json` response:**

```json
[
  {
    "office_uuid": "00000000-0000-4000-8000-000000000000",
    "office_code": "string",
    "name": "string"
  }
]
```
