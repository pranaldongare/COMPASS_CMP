/**
 * Retention reviews (ADR 0047): what to do when a consent's validity runs out,
 * and when its data must go.
 *
 * Not tickets. A review is one project or HR activity, one purpose and one
 * month: the people in it are counted, and each one responsible - the
 * project's DCO Admin, the activity's HR PoC, every processor holding the
 * data - is asked once, as an action. The officer accepts each answer or sends
 * it back, and closes the review when every one is settled. The night finds
 * the cohorts; `refresh` does the night's work now.
 */
import { apiDownload, apiGet, apiPost, apiPut } from "@/lib/api";
import type { Timestamp } from "@/types";

import type { Outcome, RetentionAnswer, ReviewKind } from "@/features/retention/types";

export type { Outcome, RetentionAnswer, ReviewKind };

export type ReviewStatus = "upcoming" | "due" | "in_progress" | "closed";
export type ActionStatus = "open" | "answered" | "accepted" | "sent_back" | "not_needed";

export interface RetentionAction {
  action_uuid: string;
  review_uuid: string;
  reference: string;
  review_kind: ReviewKind;
  kind: "owner" | "processor" | "datavault";
  label: string;
  channel: "console" | "link" | "automatic" | "none";
  assignee_name: string | null;
  status: ActionStatus;
  outcome: Outcome | null;
  reason: string | null;
  keep_until: string | null;
  reconsent: boolean | null;
  due_at: Timestamp;
  answered_at: Timestamp | null;
  answered_by_name: string | null;
  accepted_at: Timestamp | null;
  accepted_by_name: string | null;
  sent_back_reason: string | null;
  /** The proof attached, if any: its name and SHA-256. */
  evidence_name?: string | null;
  evidence_hash?: string | null;
  overdue: boolean;
}

export interface RetentionReview {
  review_uuid: string;
  reference: string;
  kind: ReviewKind;
  status: ReviewStatus;
  office: string;
  cohort: string;
  project_uuid: string;
  project_name: string;
  project_status: string;
  is_activity: boolean;
  purpose_code: string;
  purpose_name: string;
  retention_days: number | null;
  validity_days: number | null;
  lapse_behaviour: string;
  notify_before_erasure: boolean;
  people: number;
  held: number;
  renewed: number;
  first_due_at: Timestamp | null;
  last_due_at: Timestamp | null;
  actions: number;
  actions_open: number;
  actions_to_review: number;
  reconsent: "asked" | "confirmed" | "declined" | "sent" | null;
  opened_at: Timestamp | null;
  closed_at: Timestamp | null;
  closed_by_name: string | null;
  close_note: string | null;
}

export interface RetentionPerson {
  consent_uuid: string;
  consent_no: number;
  person_no: number;
  due_at: Timestamp;
  ended_by: "withdrawal" | "validity";
  state: "in" | "held" | "renewed";
  notified_at: Timestamp | null;
  invited_at: Timestamp | null;
}

export interface RetentionReviewDetail extends RetentionReview {
  people_list: RetentionPerson[];
  actions_list: RetentionAction[];
}

export interface RetentionSettings {
  reminder_days: number[];
  notice_hours: number;
  action_days: number;
  escalate_after_days: number;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export type RetentionSettingsInput = Omit<
  RetentionSettings,
  "updated_at" | "updated_by_name"
>;

export interface HolderAction {
  action: RetentionAction;
  review: Pick<
    RetentionReview,
    | "reference"
    | "kind"
    | "project_name"
    | "is_activity"
    | "purpose_code"
    | "purpose_name"
    | "people"
    | "first_due_at"
    | "last_due_at"
    | "retention_days"
    | "validity_days"
    | "status"
  >;
}

export interface SweepResult {
  reviews_made: number;
  people_added: number;
  holds_changed: number;
  renewed: number;
  fell_due: number;
  actions_opened: number;
  reminders: number;
  chased: number;
  escalated: number;
  people_told: number;
}

export const retentionKeys = {
  all: ["retention"] as const,
  reviews: (kind: string, status: string) =>
    ["retention", "reviews", kind, status] as const,
  review: (uuid: string) => ["retention", "review", uuid] as const,
  settings: ["retention", "settings"] as const,
  mine: ["retention-actions"] as const,
  action: (uuid: string) => ["retention-actions", uuid] as const,
};

export function listReviews(kind: string, status: string): Promise<RetentionReview[]> {
  const q = new URLSearchParams();
  if (kind) q.set("kind", kind);
  if (status) q.set("status", status);
  const s = q.toString();
  return apiGet<RetentionReview[]>(`/retention/reviews${s ? `?${s}` : ""}`);
}

export function getReview(uuid: string): Promise<RetentionReviewDetail> {
  return apiGet<RetentionReviewDetail>(`/retention/reviews/${uuid}`);
}

export function refreshReviews(): Promise<SweepResult> {
  return apiPost<SweepResult>("/retention/refresh", {});
}

export function acceptAction(review: string, action: string): Promise<RetentionAction> {
  return apiPost<RetentionAction>(
    `/retention/reviews/${review}/actions/${action}/accept`,
    {},
  );
}

export function sendBackAction(
  review: string,
  action: string,
  reason: string,
): Promise<RetentionAction> {
  return apiPost<RetentionAction>(
    `/retention/reviews/${review}/actions/${action}/send-back`,
    {
      reason,
    },
  );
}

export function actionNotNeeded(review: string, action: string): Promise<RetentionAction> {
  return apiPost<RetentionAction>(
    `/retention/reviews/${review}/actions/${action}/not-needed`,
    {},
  );
}

export function closeReview(review: string, note: string | null): Promise<RetentionReview> {
  return apiPost<RetentionReview>(`/retention/reviews/${review}/close`, { note });
}

/** The certificate of a closed review (PDF to file, CSV to work with). */
export function downloadCertificate(review: string, format: "pdf" | "csv") {
  return apiDownload(`/retention/reviews/${review}/certificate?format=${format}`);
}

export function getRetentionSettings(): Promise<RetentionSettings> {
  return apiGet<RetentionSettings>("/retention/settings");
}

export function saveRetentionSettings(
  body: RetentionSettingsInput,
): Promise<RetentionSettings> {
  return apiPut<RetentionSettings>("/retention/settings", body);
}

export function myActions(): Promise<RetentionAction[]> {
  return apiGet<RetentionAction[]>("/retention-actions");
}

export function myAction(uuid: string): Promise<HolderAction> {
  return apiGet<HolderAction>(`/retention-actions/${uuid}`);
}

/** Proof for an answer: one file, replaced by the next, before answering. */
export function uploadEvidence(uuid: string, file: File): Promise<RetentionAction> {
  const form = new FormData();
  form.set("evidence", file);
  return apiPost<RetentionAction>(`/retention-actions/${uuid}/evidence`, form);
}

export function downloadMyEvidence(uuid: string) {
  return apiDownload(`/retention-actions/${uuid}/evidence`);
}

export function downloadEvidence(review: string, action: string) {
  return apiDownload(`/retention/reviews/${review}/actions/${action}/evidence`);
}

export function answerAction(
  uuid: string,
  body: RetentionAnswer,
): Promise<RetentionAction> {
  return apiPost<RetentionAction>(`/retention-actions/${uuid}/answer`, body);
}

export const KIND_LABEL: Record<ReviewKind, string> = {
  validity: "Consent validity",
  retention: "Data retention",
};

export const STATUS_LABEL: Record<ReviewStatus, string> = {
  upcoming: "Upcoming",
  due: "Due",
  in_progress: "In progress",
  closed: "Closed",
};

export const ACTION_LABEL: Record<ActionStatus, string> = {
  open: "Waiting for an answer",
  answered: "Answered: to review",
  accepted: "Accepted",
  sent_back: "Sent back",
  not_needed: "Not needed",
};

export const OUTCOME_LABEL: Record<Outcome, string> = {
  erased: "Erased",
  anonymised: "Anonymised",
  kept: "Kept, with a reason",
  not_held: "Not held",
  reviewed: "Reviewed",
};

export function actionTone(
  status: ActionStatus,
  overdue: boolean,
): "neutral" | "accent" | "success" | "warning" | "danger" | "info" {
  if (status === "accepted") return "success";
  if (status === "not_needed") return "neutral";
  if (status === "answered") return "info";
  return overdue ? "danger" : "warning";
}

export function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}
