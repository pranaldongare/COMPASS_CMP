/**
 * Every request the breach register makes (S3-01).
 *
 * The DPO's alone; any other role is answered 404 by the server. Nothing here
 * talks to a regulator - a submission is recorded after a person has made it,
 * with the reference the regulator returned.
 */

import { apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import type {
  Breach,
  BreachAffected,
  BreachPreview,
  BreachScope,
  BreachAssessment,
  BreachAssessmentInput,
  BreachDutyKind,
  BreachInput,
  BreachNotices,
  BreachNoticeWords,
  BreachOutcome,
  BreachStatus,
  BreachSummary,
  Timestamp,
  Uuid,
} from "@/types";

export function listBreaches(status?: BreachStatus): Promise<BreachSummary[]> {
  return apiGet<BreachSummary[]>(`/breaches${queryString({ status })}`);
}

export function getBreach(uuid: Uuid): Promise<Breach> {
  return apiGet<Breach>(`/breaches/${uuid}`);
}

export function recordBreach(body: BreachInput): Promise<Breach> {
  return apiPost<Breach>("/breaches", body);
}

export function determineBreach(
  uuid: Uuid,
  body: { outcome: BreachOutcome; reasoning: string; became_aware_at?: Timestamp | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/determinations`, body);
}

export function listAssessments(uuid: Uuid): Promise<BreachAssessment[]> {
  return apiGet<BreachAssessment[]>(`/breaches/${uuid}/assessments`);
}

export function assessBreach(uuid: Uuid, body: BreachAssessmentInput): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/assessments`, body);
}

export function markCertIn(uuid: Uuid): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/cert-in`, {});
}

export function completeDuty(
  uuid: Uuid,
  duty: BreachDutyKind,
  body: { occurred_at: Timestamp; reference: string; note?: string | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/obligations/${duty}/complete`, body);
}

export function extendReport(
  uuid: Uuid,
  body: {
    requested_at: Timestamp;
    allowed_until: Timestamp;
    reference?: string | null;
    note?: string | null;
  },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/obligations/board_report/extension`, body);
}

export function transitionBreach(
  uuid: Uuid,
  body: { to: BreachStatus; reason?: string | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/transition`, body);
}

/* ------------------------------------------------- who it touched (S3-02) */

export function listAffected(uuid: Uuid, cursor?: string | null): Promise<BreachAffected> {
  return apiGet<BreachAffected>(`/breaches/${uuid}/affected${queryString({ cursor })}`);
}

export function previewAffected(uuid: Uuid, scopes: BreachScope[]): Promise<BreachPreview> {
  return apiPost<BreachPreview>(`/breaches/${uuid}/affected/preview`, { scopes });
}

export function confirmAffected(
  uuid: Uuid,
  body: { scopes: BreachScope[]; exclude: Uuid[]; add: Uuid[]; note?: string | null },
): Promise<BreachAffected> {
  return apiPost<BreachAffected>(`/breaches/${uuid}/affected`, body);
}

/* ---------------------------------------------- telling the people (S3-03) */

export function getNotices(uuid: Uuid): Promise<BreachNotices> {
  return apiGet<BreachNotices>(`/breaches/${uuid}/notices`);
}

export function draftNotice(uuid: Uuid, words: Partial<BreachNoticeWords>): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices`, words);
}

export function editNotice(
  uuid: Uuid,
  noticeUuid: Uuid,
  words: Partial<BreachNoticeWords>,
): Promise<BreachNotices> {
  return apiPut<BreachNotices>(`/breaches/${uuid}/notices/${noticeUuid}`, words);
}

export function approveNotice(uuid: Uuid, noticeUuid: Uuid): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices/${noticeUuid}/approve`, {});
}

export function sendNotice(uuid: Uuid): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices/send`, {});
}
