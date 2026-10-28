/**
 * HR activities (ADR 0033): made by an HR PoC from an approved template
 * version, live as they are created. Their consents are read where every
 * project's are, and their link replaced or revoked where every link is.
 */

import { apiGet, apiPost, queryString } from "@/lib/api";
import type {
  ActivityOptionCategory,
  HrActivity,
  HrActivityCreated,
  HrActivityDetail,
  Uuid,
} from "@/types";

export interface ActivityInput {
  category_uuid: Uuid;
  template_version_uuid: Uuid;
  purpose_uuids: Uuid[];
  name: string;
  description: string;
  audience_mode: "sso" | "otp";
  link_expires_at: string;
}

export interface UpgradeInput {
  template_version_uuid: Uuid;
  purpose_uuids: Uuid[];
  description: string;
}

export function listHrActivities(
  filters: { status?: string; category?: Uuid; q?: string } = {},
): Promise<HrActivity[]> {
  return apiGet<HrActivity[]>(`/hr/activities${queryString(filters)}`);
}

export function getHrActivity(uuid: Uuid): Promise<HrActivityDetail> {
  return apiGet<HrActivityDetail>(`/hr/activities/${uuid}`);
}

export function activityOptions(): Promise<ActivityOptionCategory[]> {
  return apiGet<ActivityOptionCategory[]>("/hr/activities/options");
}

export function createHrActivity(body: ActivityInput): Promise<HrActivityCreated> {
  return apiPost<HrActivityCreated>("/hr/activities", body);
}

export function upgradeHrActivity(
  uuid: Uuid,
  body: UpgradeInput,
): Promise<{ activity_uuid: Uuid; notice_uuid: Uuid; version: number; reconsent_requested: number }> {
  return apiPost(`/hr/activities/${uuid}/upgrade`, body);
}

export function closeHrActivity(
  uuid: Uuid,
  reason: string | null,
): Promise<{ project_uuid: Uuid; to: string; links_revoked: number }> {
  return apiPost(`/hr/activities/${uuid}/close`, { reason });
}
