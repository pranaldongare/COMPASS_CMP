/**
 * A processor's retention action, by its link (ADR 0047).
 *
 * As a holder ticket's link (0049): the link alone reads which review it is
 * and where a code will go; the code, sent to the address the link was sent
 * to, opens the action for an hour in an HttpOnly cookie the API sets.
 */
import { apiGet, apiPost } from "@/lib/api";

import type { Outcome, RetentionAnswer, ReviewKind } from "@/features/retention/types";

export interface RetentionLink {
  reference: string;
  holder_label: string;
  kind: ReviewKind;
  /** Where the code goes, masked. */
  code_goes_to: string | null;
  status: "open" | "answered" | "accepted" | "sent_back" | "not_needed";
  due_at: string;
  signed_in: boolean;
}

export interface RetentionLinkAction {
  action: {
    action_uuid: string;
    label: string;
    status: RetentionLink["status"];
    outcome: Outcome | null;
    reason: string | null;
    keep_until: string | null;
    due_at: string;
    answered_at: string | null;
    sent_back_reason: string | null;
    evidence_name?: string | null;
    evidence_hash?: string | null;
  };
  review: {
    reference: string;
    kind: ReviewKind;
    project_name: string;
    is_activity: boolean;
    purpose_code: string;
    purpose_name: string;
    people: number;
    first_due_at: string | null;
    last_due_at: string | null;
  };
}

const base = (token: string) => `/retention-links/${encodeURIComponent(token)}`;

export const getRetentionLink = (token: string) => apiGet<RetentionLink>(base(token));

export const sendRetentionCode = (token: string) =>
  apiPost<{ ok: boolean; message?: string }>(`${base(token)}/code`, {});

export const verifyRetentionCode = (token: string, code: string) =>
  apiPost<{ ok: boolean; message?: string }>(`${base(token)}/verify`, { code });

export const signOutRetention = (token: string) =>
  apiPost<void>(`${base(token)}/sign-out`, {});

export const getRetentionAction = (token: string) =>
  apiGet<RetentionLinkAction>(`${base(token)}/action`);

export const answerRetention = (token: string, body: RetentionAnswer) =>
  apiPost<RetentionLinkAction>(`${base(token)}/answer`, body);

/** Proof for the answer: one file, replaced by the next, before answering. */
export function uploadRetentionEvidence(token: string, file: File) {
  const form = new FormData();
  form.set("evidence", file);
  return apiPost<RetentionLinkAction>(`${base(token)}/evidence`, form);
}
