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

/** An HR activity (ADR 0033): a project of the Legal office, made by an HR
 *  PoC from an approved template version, live as it is created. */
export interface HrActivity {
  activity_uuid: Uuid;
  name: string;
  /** The one free text, served inside the notice. */
  description: string | null;
  status: string;
  category_uuid: Uuid;
  category_code: string;
  category_name: string;
  version_uuid: Uuid;
  template_version: number;
  version_status: string;
  reconsent_required: boolean;
  template_uuid: Uuid;
  template_code: string;
  template_title: string;
  created_by_uuid: Uuid;
  created_by_name: string;
  notice_uuid: Uuid | null;
  notice_code: string | null;
  notice_version: number | null;
  consent_count: number;
  link_status: string | null;
  created_at: Timestamp;
  updated_at: Timestamp;
}

export interface HrActivityLink {
  link_uuid: Uuid;
  status: string;
  expires_at: Timestamp;
  use_count: number;
  /** `sso` (employees, through the organisation) or `otp` (a code). */
  audience_mode: "sso" | "otp";
  url_path: string | null;
}

export interface HrActivityDetail extends HrActivity {
  link: HrActivityLink | null;
}

/** What the wizard offers: a category, its approved versions and purposes. */
export interface ActivityOptionPurpose {
  purpose_uuid: Uuid;
  purpose_code: string;
  name: string;
  is_mandatory: boolean;
  display_order: number;
}

export interface ActivityOptionVersion {
  version_uuid: Uuid;
  version: number;
  template_uuid: Uuid;
  template_code: string;
  template_title: string;
  slot_guidance: string | null;
  slot_max_length: number;
  reconsent_required: boolean;
  purposes: ActivityOptionPurpose[];
}

export interface ActivityOptionCategory {
  category_uuid: Uuid;
  category_code: string;
  name: string;
  versions: ActivityOptionVersion[];
}

export interface HrActivityCreated {
  activity_uuid: Uuid;
  notice_uuid: Uuid | null;
  link_uuid: Uuid;
  url_path: string;
  expires_at: Timestamp;
  audience_mode: "sso" | "otp";
}
