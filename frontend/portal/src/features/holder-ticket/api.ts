/**
 * An outside holder's ticket, by its link (0049, 2026-10-08).
 *
 * The link alone reads what it opens; a code sent to the address on the ticket
 * opens an hour on it, held in an HttpOnly cookie the API sets. Nothing here
 * stores anything: the cookie is the only state, and the server keeps it.
 */
import { apiDownload, apiGet, apiPost } from "@/lib/api";

export type ReturnOutcome = "done" | "partial" | "failed";

export const OUTCOME_COPY: Record<ReturnOutcome, string> = {
  done: "Did all of it",
  partial: "Did only part of it",
  failed: "Could not do it",
};

export interface HolderLink {
  reference: string;
  holder_label: string;
  request_type: string;
  /** Where the code goes, masked. */
  code_goes_to: string | null;
  state: string;
  state_label: string;
  due_at: string | null;
  signed_in: boolean;
}

export interface HolderMessage {
  message_uuid: string;
  author_side: "office" | "holder" | "system";
  author_name: string | null;
  kind: "brief" | "instruction" | "message" | "return" | "escalation" | "status";
  body: string;
  evidence_hash: string | null;
  evidence_name: string | null;
  created_at: string;
}

export interface HolderItem {
  item_uuid: string;
  decision: "erase" | "redact" | "retain" | "quarantine";
  retain_until: string | null;
  other_subjects: number;
  asset_type: string;
  source_asset_ref: string;
  source_name: string;
  project_name: string;
  collected_on: string;
}

export interface HolderTicket {
  holder_uuid: string;
  reference: string;
  request_type: string;
  request_status: string;
  label: string;
  instruction: string | null;
  ticket_status: string;
  due_at: string | null;
  returned_at: string | null;
  return_summary: string | null;
  return_outcome: ReturnOutcome | null;
  sent_back_at: string | null;
  sent_back_reason: string | null;
  accepted_at: string | null;
  state: string;
  state_label: string;
  overdue: boolean;
}

export interface HolderTicketDetail {
  ticket: HolderTicket;
  messages: HolderMessage[];
  items: HolderItem[];
}

const base = (token: string) => `/holder-tickets/${encodeURIComponent(token)}`;

export const getLink = (token: string) => apiGet<HolderLink>(base(token));

export const sendCode = (token: string) =>
  apiPost<{ ok: boolean; message?: string }>(`${base(token)}/code`, {});

export const verifyCode = (token: string, code: string) =>
  apiPost<{ ok: boolean; message?: string }>(`${base(token)}/verify`, { code });

export const signOut = (token: string) => apiPost<void>(`${base(token)}/sign-out`, {});

export const getTicket = (token: string) => apiGet<HolderTicketDetail>(`${base(token)}/ticket`);

export function writeMessage(token: string, body: string, file: File | null) {
  const form = new FormData();
  form.set("body", body);
  if (file) form.set("evidence", file);
  return apiPost<HolderTicketDetail>(`${base(token)}/messages`, form);
}

export function giveAnswer(
  token: string,
  input: { summary: string; outcome: ReturnOutcome; file: File | null },
) {
  const form = new FormData();
  form.set("summary", input.summary);
  form.set("outcome", input.outcome);
  if (input.file) form.set("evidence", input.file);
  return apiPost<HolderTicketDetail>(`${base(token)}/answer`, form);
}

export const downloadFile = (token: string, messageUuid: string) =>
  apiDownload(`${base(token)}/messages/${encodeURIComponent(messageUuid)}/evidence`);
