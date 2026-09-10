/**
 * Rights requests: the DPO's register, thin.
 *
 * The register is gated on the `rights_request` resource. The public form,
 * the nominee's entry points and the data principal's own calls live on her
 * portal, a separate deployment. Nothing here decides anything - the clock,
 * the gates and the early exits are the server's, and these functions carry
 * the answer back.
 */

import { apiDownload, apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import { config } from "@/lib/config";
import type { ListFilters } from "@/lib/query";
import type {
  AuditEntry,
  GrievanceDecisionResult,
  Page,
  RightsHolder,
  RightsRequest,
  RightsRequestDetail,
  RightsRequestRow,
  RightsRequestType,
  RightsScopeDecision,
  RightsScopeItem,
  RightsTransitionOption,
  Uuid,
  MyTicket,
  HolderThread,
  TicketDetail,
} from "@/types";

/* ==========================================================================
   The DPO's register - /requests
   ========================================================================== */

export interface RequestFilters extends ListFilters {
  overdue?: boolean;
}

export function listRequests(filters: RequestFilters = {}): Promise<Page<RightsRequestRow>> {
  return apiGet<Page<RightsRequestRow>>(`/requests${queryString(filters)}`);
}

export function getRequest(uuid: Uuid): Promise<RightsRequestDetail> {
  return apiGet<RightsRequestDetail>(`/requests/${uuid}`);
}

export function getRequestTransitions(
  uuid: Uuid,
): Promise<{ current: string; available: RightsTransitionOption[] }> {
  return apiGet(`/requests/${uuid}/transitions`);
}

export function getRequestTrail(uuid: Uuid): Promise<AuditEntry[]> {
  return apiGet<AuditEntry[]>(`/requests/${uuid}/trail`);
}

/** The trail of the request this one is about, reached through this one:
 * whoever may decide a grievance may read how the original was handled. */
export function getLinkedTrail(uuid: Uuid): Promise<AuditEntry[]> {
  return apiGet<AuditEntry[]>(`/requests/${uuid}/linked/trail`);
}

export interface LogRequestInput {
  request_type: RightsRequestType;
  contact: string;
  name?: string | null;
  request_text: string;
  subject_uuid?: Uuid | null;
  about_dpo?: boolean;
}

/** A request that arrived by email. Same record as the other channels. */
export function logRequest(body: LogRequestInput): Promise<RightsRequest> {
  return apiPost<RightsRequest>("/requests", body);
}

const action = (uuid: Uuid, name: string) => `/requests/${uuid}/${name}`;

export const acknowledge = (uuid: Uuid) => apiPost<RightsRequest>(action(uuid, "acknowledge"), {});
export const sendVerificationCode = (uuid: Uuid) =>
  apiPost<RightsRequest>(action(uuid, "verification/code"), {});
export const confirmVerificationCode = (uuid: Uuid, code: string) =>
  apiPost<RightsRequest>(action(uuid, "verification/confirm"), { code });
export const verifyManually = (uuid: Uuid, note: string) =>
  apiPost<RightsRequest>(action(uuid, "verification/manual"), { note });
export const failVerification = (uuid: Uuid, note?: string | null) =>
  apiPost<RightsRequest>(action(uuid, "verification/fail"), { note: note ?? null });
export const classify = (uuid: Uuid, body: { request_type: RightsRequestType; note?: string | null }) =>
  apiPost<RightsRequest>(action(uuid, "classify"), body);
export const refuse = (uuid: Uuid, reason: string) =>
  apiPost<RightsRequest>(action(uuid, "refuse"), { reason });
export const treatAsWithdrawal = (uuid: Uuid, note?: string | null) =>
  apiPost<RightsRequest>(action(uuid, "withdrawal"), { note: note ?? null });
export const confirmIntent = (uuid: Uuid) => apiPost<RightsRequest>(action(uuid, "intent"), {});
export const recordEvent = (uuid: Uuid, body: { evidenced: boolean; note?: string | null }) =>
  apiPost<RightsRequest>(action(uuid, "event"), body);
export const escalate = (uuid: Uuid) => apiPost<RightsRequest>(action(uuid, "escalate"), {});
export const assignReviewer = (uuid: Uuid, reviewer_uuid: Uuid) =>
  apiPost<RightsRequest>(action(uuid, "reviewer"), { reviewer_uuid });
export const transitionRequest = (uuid: Uuid, body: { to: string; reason?: string | null }) =>
  apiPost<RightsRequest>(action(uuid, "transition"), body);

export const deriveHolders = (uuid: Uuid) =>
  apiPost<RightsHolder[]>(action(uuid, "holders/derive"), {});
export interface HolderInput {
  label?: string | null;
  processor_uuid?: Uuid | null;
  responder_name?: string | null;
  responder_contact?: string | null;
}
export const addHolder = (uuid: Uuid, body: HolderInput) =>
  apiPost<RightsHolder>(action(uuid, "holders"), body);
export interface ConfirmHolderInput {
  responder_name?: string | null;
  responder_contact?: string | null;
  /** One of the processor's registered respondents; decides the channel. */
  respondent_uuid?: Uuid | null;
}
export const confirmHolder = (uuid: Uuid, holderUuid: Uuid, body: ConfirmHolderInput) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/confirm`), body);

export interface ContactInput {
  kind: "mail_sent" | "chased" | "reply_noted" | "note";
  note?: string | null;
  /** Re-send the instruction to the address on record, and log that it went. */
  send?: boolean;
}
export const logContact = (uuid: Uuid, holderUuid: Uuid, body: ContactInput) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/contact`), body);

/** The ticket's thread as the office reads it. Reading marks it read. */
export const holderThread = (uuid: Uuid, holderUuid: Uuid) =>
  apiGet<HolderThread>(action(uuid, `holders/${holderUuid}/thread`));
export interface MessageInput {
  body: string;
  evidence: File | null;
}
function messageForm(input: MessageInput): FormData {
  const form = new FormData();
  form.set("body", input.body);
  if (input.evidence) form.set("evidence", input.evidence);
  return form;
}
export const postToHolder = (uuid: Uuid, holderUuid: Uuid, input: MessageInput) =>
  apiPost<HolderThread>(action(uuid, `holders/${holderUuid}/thread`), messageForm(input));
export interface SendBackInput {
  reason: string;
  due_at?: string | null;
}
/** Not satisfied with the return: the ticket is open again, with the reason and a date. */
export const sendBackTicket = (uuid: Uuid, holderUuid: Uuid, body: SendBackInput) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/send-back`), body);
export const withdrawTicket = (uuid: Uuid, holderUuid: Uuid, reason: string) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/withdraw`), { reason });
export interface ReassignInput {
  respondent_uuid?: Uuid | null;
  responder_name?: string | null;
  responder_contact?: string | null;
}
export const reassignHolder = (uuid: Uuid, holderUuid: Uuid, body: ReassignInput) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/reassign`), body);
export const remindHolder = (uuid: Uuid, holderUuid: Uuid) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/remind`), {});
/** Where a file attached to a message is downloaded from, on the office's side. */
export const holderMessageAttachmentUrl = (uuid: Uuid, holderUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}/requests/${uuid}/holders/${holderUuid}/messages/${messageUuid}/evidence`;
export const issueTickets = (uuid: Uuid, body: { instruction?: string | null; due_at?: string | null }) =>
  apiPost<RightsHolder[]>(action(uuid, "tickets"), body);
export function returnTicket(
  uuid: Uuid,
  holderUuid: Uuid,
  input: { summary: string; evidence: File | null },
): Promise<RightsHolder> {
  const form = new FormData();
  form.set("summary", input.summary);
  if (input.evidence) form.set("evidence", input.evidence);
  return apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/return`), form);
}
export const escalateTicket = (uuid: Uuid, holderUuid: Uuid) =>
  apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/escalate`), {});

export const deriveScope = (uuid: Uuid) =>
  apiPost<RightsScopeItem[]>(action(uuid, "scope/derive"), {});
export interface DecideItemInput {
  decision: RightsScopeDecision;
  basis: string;
  retain_until?: string | null;
  holder_uuid?: Uuid | null;
}
export const decideItem = (uuid: Uuid, itemUuid: Uuid, body: DecideItemInput) =>
  apiPut<RightsScopeItem>(action(uuid, `scope/${itemUuid}`), body);
export const applyItem = (uuid: Uuid, itemUuid: Uuid) =>
  apiPost<RightsScopeItem>(action(uuid, `scope/${itemUuid}/apply`), {});

export const respond = (uuid: Uuid, body: { outcome: string; response_text: string }) =>
  apiPost<RightsRequest>(action(uuid, "respond"), body);
export interface GrievanceDecisionInput {
  upheld: boolean;
  remedy_text?: string | null;
  response_text: string;
  rerun?: boolean;
}
export const decideGrievance = (uuid: Uuid, body: GrievanceDecisionInput) =>
  apiPost<GrievanceDecisionResult>(action(uuid, "decide"), body);

export function downloadResponse(uuid: Uuid) {
  return apiDownload(`/requests/${uuid}/download`);
}

/* ===========================================================================
   The respondent's side - tickets addressed to me
   =========================================================================== */

export function listMyTickets(): Promise<MyTicket[]> {
  return apiGet<MyTicket[]>("/tickets");
}

export function returnMyTicket(
  holderUuid: Uuid,
  input: { summary: string; evidence: File | null },
): Promise<MyTicket> {
  const form = new FormData();
  form.set("summary", input.summary);
  if (input.evidence) form.set("evidence", input.evidence);
  return apiPost<MyTicket>(`/tickets/${holderUuid}/return`, form);
}

/** One ticket with its brief and thread. Reading marks the office's messages read. */
export function myTicket(holderUuid: Uuid): Promise<TicketDetail> {
  return apiGet<TicketDetail>(`/tickets/${holderUuid}`);
}

export function messageOffice(holderUuid: Uuid, input: MessageInput): Promise<TicketDetail> {
  return apiPost<TicketDetail>(`/tickets/${holderUuid}/messages`, messageForm(input));
}

/** Where a file attached to a message is downloaded from, on the team's side. */
export const myMessageAttachmentUrl = (holderUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}/tickets/${holderUuid}/messages/${messageUuid}/evidence`;
