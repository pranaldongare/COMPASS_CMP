/**
 * The Legal office's categories of HR activity (0052, ADR 0033).
 *
 * Written and retired by the Legal PoC, with the processors that hold each
 * one's data. An HR PoC reads the ones assigned to them; the administrator
 * assigns them, on the account's page.
 */

import { apiGet, apiPatch, apiPost, apiPut, queryString } from "@/lib/api";
import type {
  CategoryProcessor,
  CategoryProcessorRole,
  HrCategory,
  HrCategoryDetail,
  HrPoc,
  PocCategory,
  Uuid,
} from "@/types";

export interface HrCategoryInput {
  category_code: string;
  name: string;
  description?: string | null;
}

export interface CategoryProcessorInput {
  processor_uuid: Uuid;
  processor_role: CategoryProcessorRole;
  respondent_user_uuid?: Uuid | null;
}

const base = (uuid: Uuid) => `/hr/categories/${uuid}`;

export function listHrCategories(
  filters: { status?: string; q?: string } = {},
): Promise<HrCategory[]> {
  return apiGet<HrCategory[]>(`/hr/categories${queryString(filters)}`);
}

export function getHrCategory(uuid: Uuid): Promise<HrCategoryDetail> {
  return apiGet<HrCategoryDetail>(base(uuid));
}

export function createHrCategory(body: HrCategoryInput): Promise<HrCategory> {
  return apiPost<HrCategory>("/hr/categories", body);
}

export function updateHrCategory(
  uuid: Uuid,
  body: {
    name?: string | null;
    description?: string | null;
    default_person_type?: "external" | "vendor" | "candidate" | "visitor" | null;
  },
): Promise<HrCategory> {
  return apiPatch<HrCategory>(base(uuid), body);
}

export function setHrCategoryStatus(
  uuid: Uuid,
  status: "active" | "retired",
): Promise<HrCategory> {
  return apiPost<HrCategory>(`${base(uuid)}/status`, { status });
}

/** The whole set; one left out is marked removed. */
export function setCategoryProcessors(
  uuid: Uuid,
  processors: CategoryProcessorInput[],
): Promise<CategoryProcessor[]> {
  return apiPut<CategoryProcessor[]>(`${base(uuid)}/processors`, { processors });
}

/** Active HR PoCs, for a picker; `category` keeps those assigned to it. */
export function listHrPocs(filters: { category?: Uuid } = {}): Promise<HrPoc[]> {
  return apiGet<HrPoc[]>(`/users/hr-pocs${queryString(filters)}`);
}

/** The whole set of an HR PoC's categories; what is left out is taken away. */
export function setUserCategories(
  userUuid: Uuid,
  categoryUuids: Uuid[],
): Promise<PocCategory[]> {
  return apiPut<PocCategory[]>(`/users/${userUuid}/categories`, {
    category_uuids: categoryUuids,
  });
}
