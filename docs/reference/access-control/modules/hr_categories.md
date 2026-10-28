# HR categories: endpoint access

[Guide](../README.md) · [Role legend](../roles_and_scopes.md) · [Implementation notes](../implementation_notes.md)

7 operations; 7 appear in the existing OpenAPI/API docs. Added with the HR track (ADR 0033); evidence links point at `HEAD`.

| Method | Endpoint | Who has access | Authentication / anonymous |
| --- | --- | --- | --- |
| GET | `/hr/categories` | `legal`, `hr_user`, `admin` | Full session; anonymous NO |
| POST | `/hr/categories` | `legal` | Full session; anonymous NO |
| GET | `/hr/categories/{category_uuid}` | `legal`, `hr_user`, `admin` | Full session; anonymous NO |
| PATCH | `/hr/categories/{category_uuid}` | `legal` | Full session; anonymous NO |
| POST | `/hr/categories/{category_uuid}/status` | `legal` | Full session; anonymous NO |
| GET | `/hr/categories/{category_uuid}/processors` | `legal`, `hr_user`, `admin` | Full session; anonymous NO |
| PUT | `/hr/categories/{category_uuid}/processors` | `legal` | Full session; anonymous NO |

## GET /hr/categories

The Legal office's categories.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |

- **Who:** `legal`, `hr_user`, `admin`.
- **Route guard:** `HrCategoryReader`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", hidden=True))]`.
- **Rules:** Within the caller's office (`cmp_office_visible`); an HR PoC's are those assigned to them. `status` and `q` filter. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /hr/categories

Create Category.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `legal`.
- **Route guard:** `HrCategoryWriter`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", write=True, hidden=True))]`.
- **Rules:** In the caller's office. The code is upper case, 2-24 characters, unique (409 `category_code_taken`). (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## GET /hr/categories/{category_uuid}

Get Category.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |

- **Who:** `legal`, `hr_user`, `admin`.
- **Route guard:** `HrCategoryReader`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", hidden=True))]`.
- **Rules:** With its live processors (respondent name and address sealed) and its HR PoCs. 404 outside the office or, for an HR PoC, outside their assignments. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## PATCH /hr/categories/{category_uuid}

Update Category.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `legal`.
- **Route guard:** `HrCategoryWriter`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", write=True, hidden=True))]`.
- **Rules:** Name and description; the code is fixed. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## POST /hr/categories/{category_uuid}/status

Retire or reactivate.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `legal`.
- **Route guard:** `HrCategoryWriter`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", write=True, hidden=True))]`.
- **Rules:** 409 `category_status_unchanged` when already so. A retired category takes no new template. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## GET /hr/categories/{category_uuid}/processors

List Category Processors.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | ALL | NO | NO | NO | NO | NO | NO | ALL | SCOPED |

- **Who:** `legal`, `hr_user`, `admin`.
- **Route guard:** `HrCategoryReader`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", hidden=True))]`.
- **Rules:** The live processors, as on the category. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).

## PUT /hr/categories/{category_uuid}/processors

Set the processors that hold a category's data.

| DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder | Legal PoC | HR PoC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NO | NO | NO | NO | NO | NO | NO | NO | ALL | NO |

- **Who:** `legal`.
- **Route guard:** `HrCategoryWriter`.
- **Resolved gate:** `Annotated[Principal, Depends(RequireResource("hr_category", write=True, hidden=True))]`.
- **Rules:** The whole set; one left out is marked removed, never deleted. Each processor active; a respondent an active member of staff of the category's office (422). 409 on a retired category. (2026-10-28, 0052) A role with no grant (the DPO's) is answered 404, not 403, as for another office's records. (2026-10-28, 0052)
- **Evidence:** [source 1](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/api/routers/v1/hr_categories.py), [source 2](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/domain/hr/categories.py), [source 3](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/db/repositories/hr_categories.py), [source 4](https://github.com/pranaldongare/COMPASS_CMP/blob/HEAD/backend/api/src/cmp/core/permissions.py).
