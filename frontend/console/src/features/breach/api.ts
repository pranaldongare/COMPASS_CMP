/**
 * Every request the breach register makes (S3-01).
 *
 * The DPO's alone; any other role is answered 404 by the server. Nothing here
 * talks to a regulator - a submission is recorded after a person has made it,
 * with the reference the regulator returned.
 */

import { apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import { config } from "@/lib/config";
import type {
  BreachAttachmentKind,
  Breach,
  BreachAffected,
  BreachAssessment,
  BreachAssessmentInput,
  BreachDutyKind,
  BreachInput,
  BreachIntimation,
  BreachNoticeWords,
  BreachNotices,
  BreachOutcome,
  BreachPreview,
  BreachReport,
  BreachScope,
  BreachStatus,
  BreachSummary,
  BreachTicket,
  BreachTicketDetail,
  MyBreachTicket,
  MyBreachTicketDetail,
  OrgBoardBrief,
  ReturnOutcome,
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
  body: { occurred_at: Timestamp; reference?: string | null; reported_to?: string | null; note?: string | null },
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

/* ----------------------------------------------- the Board's documents (S3-04) */

export function getIntimation(uuid: Uuid): Promise<BreachIntimation> {
  return apiGet<BreachIntimation>(`/breaches/${uuid}/board/intimation`);
}

export function getReport(uuid: Uuid): Promise<BreachReport> {
  return apiGet<BreachReport>(`/breaches/${uuid}/board/report`);
}

/* ---------------------------------------- the organisation's board (S3-07) */

export function getOrgBoardBrief(uuid: Uuid): Promise<OrgBoardBrief> {
  return apiGet<OrgBoardBrief>(`/breaches/${uuid}/org-board/brief`);
}

/* -------------------------------------------------- breach tickets (S3-08) */

export interface TicketMessageInput {
  body: string;
  evidence: File | null;
}

function messageForm(input: TicketMessageInput): FormData {
  const form = new FormData();
  form.set("body", input.body);
  if (input.evidence) form.set("evidence", input.evidence);
  return form;
}

const tickets = (uuid: Uuid) => `/breaches/${uuid}/tickets`;

/** What a browser often leaves blank for a saved email or a log: the type
 *  the API checks, read off the extension. */
const TYPE_BY_EXTENSION: Record<string, string> = {
  eml: "message/rfc822",
  msg: "application/vnd.ms-outlook",
  txt: "text/plain",
  log: "text/plain",
  csv: "text/csv",
};

/** Keep a file with the incident (2026-10-06): an email, a proof, a chat. */
export function addBreachAttachment(
  uuid: Uuid,
  input: { file: File; kind: BreachAttachmentKind; note?: string | null },
): Promise<Breach> {
  const ext = input.file.name.split(".").pop()?.toLowerCase() ?? "";
  const typed =
    input.file.type || !TYPE_BY_EXTENSION[ext]
      ? input.file
      : new File([input.file], input.file.name, { type: TYPE_BY_EXTENSION[ext] });
  const form = new FormData();
  form.set("file", typed, typed.name);
  form.set("kind", input.kind);
  if (input.note?.trim()) form.set("note", input.note.trim());
  return apiPost<Breach>(`/breaches/${uuid}/attachments`, form);
}

/** Where a file kept with an incident is downloaded; every download is audited. */
export const breachAttachmentUrl = (uuid: Uuid, attachmentUuid: Uuid) =>
  `${config.apiUrl}/breaches/${uuid}/attachments/${attachmentUuid}`;

export function listBreachTickets(uuid: Uuid): Promise<BreachTicket[]> {
  return apiGet<BreachTicket[]>(tickets(uuid));
}

/** Somebody named by an address rather than picked (S3-09): the server finds
 *  their account, or makes a breach-only login for them. */
export interface PersonByEmail {
  full_name: string;
  email: string;
  mobile?: string | null;
}

export function assignBreachTicket(
  uuid: Uuid,
  body: ({ user_uuid: Uuid } | PersonByEmail) & { instruction: string; answer_by?: string | null },
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(tickets(uuid), body);
}

export function getBreachTicket(uuid: Uuid, ticketUuid: Uuid): Promise<BreachTicketDetail> {
  return apiGet<BreachTicketDetail>(`${tickets(uuid)}/${ticketUuid}`);
}

export function messageBreachHolder(
  uuid: Uuid,
  ticketUuid: Uuid,
  input: TicketMessageInput,
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(`${tickets(uuid)}/${ticketUuid}/messages`, messageForm(input));
}

/** send_back, close, withdraw or reopen: the path is the move, hyphenated. */
export function moveBreachTicket(
  uuid: Uuid,
  ticketUuid: Uuid,
  move: "send_back" | "close" | "withdraw" | "reopen",
  reason?: string,
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(
    `${tickets(uuid)}/${ticketUuid}/${move.replace("_", "-")}`,
    move === "close" ? {} : { reason },
  );
}

/** Where the office downloads a file on a ticket's thread. */
export const breachTicketFileUrl = (uuid: Uuid, ticketUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}${tickets(uuid)}/${ticketUuid}/messages/${messageUuid}/evidence`;

export function myBreachTickets(): Promise<MyBreachTicket[]> {
  return apiGet<MyBreachTicket[]>("/breach-tickets");
}

export function myBreachTicket(ticketUuid: Uuid): Promise<MyBreachTicketDetail> {
  return apiGet<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}`);
}

export function messageBreachOffice(ticketUuid: Uuid, input: TicketMessageInput): Promise<MyBreachTicketDetail> {
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/messages`, messageForm(input));
}

export function returnBreachTicket(
  ticketUuid: Uuid,
  input: { summary: string; outcome: ReturnOutcome; evidence: File | null },
): Promise<MyBreachTicketDetail> {
  const form = new FormData();
  form.set("summary", input.summary);
  form.set("outcome", input.outcome);
  if (input.evidence) form.set("evidence", input.evidence);
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/return`, form);
}

/** A holder brings in a colleague, who gets their own ticket (S3-09). The
 *  answer is the adder's own ticket, whatever happened to the colleague's
 *  account. */
export function addBreachColleague(
  ticketUuid: Uuid,
  body: PersonByEmail & { note: string },
): Promise<MyBreachTicketDetail> {
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/colleagues`, body);
}

/** Where a holder downloads a file on their breach ticket's thread. */
export const myBreachTicketFileUrl = (ticketUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}/breach-tickets/${ticketUuid}/messages/${messageUuid}/evidence`;
