/**
 * The HR track's registry (ADR 0033): the Legal office's categories of HR
 * activity, the processors that hold each one's data, and the HR PoCs
 * assigned to run activities in it.
 */

import type { Timestamp, Uuid } from "@/types/primitives";

/** What a processor is to a category: the HR system of record, a database
 *  the data is copied into, or a vendor that runs the activity. */
export type CategoryProcessorRole = "hrms" | "database" | "vendor";

export interface HrCategory {
  category_uuid: Uuid;
  /** Short and stable: `WELLNESS`, `CSR`, `BGV`. */
  category_code: string;
  name: string;
  description: string | null;
  status: "active" | "retired";
  office_code: string;
  processor_count: number;
  poc_count: number;
  template_count: number;
  created_at: Timestamp;
  updated_at: Timestamp;
  retired_at: Timestamp | null;
}

export interface CategoryProcessor {
  processor_uuid: Uuid;
  legal_name: string;
  is_in_house: boolean;
  processor_status: string;
  processor_role: CategoryProcessorRole;
  /** Who answers for it on the category's requests; null means the
   *  activity's HR PoC. Name and address are sealed, opened by the portal. */
  respondent_uuid: Uuid | null;
  respondent_name: string | null;
  respondent_email: string | null;
  added_at: Timestamp;
}

/** An HR PoC assigned to a category. */
export interface CategoryPoc {
  uuid: Uuid;
  full_name: string;
  email: string | null;
  status: string;
  assigned_at: Timestamp;
}

export interface HrCategoryDetail extends HrCategory {
  processors: CategoryProcessor[];
  pocs: CategoryPoc[];
}

/** A category on an HR PoC's account page. */
export interface PocCategory {
  category_uuid: Uuid;
  category_code: string;
  name: string;
  status: string;
}

/** An HR PoC, for a picker. */
export interface HrPoc {
  uuid: Uuid;
  full_name: string;
  email: string | null;
}
