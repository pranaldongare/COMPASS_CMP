/**
 * Rights requests and nominations: every endpoint, thin.
 *
 * Three audiences share one record. The public form and the nominee's entry
 * points need no session and answer neutrally; the data principal's calls are
 * scoped to her by the server; the DPO's register is gated on the
 * `rights_request` resource. Nothing here decides anything - the clock, the
 * gates and the early exits are the server's, and these functions carry the
 * answer back.
 */

import { apiDelete, apiDownload, apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import type { ListFilters } from "@/lib/query";
import type {
  Acknowledged,
  AuditEntry,
  GrievanceDecisionResult,
  MyRequest,
  Nomination,
  NominationView,
  Page,
  PublicRequestReceipt,
  PublicVerifyResult,
  RightsHolder,
  RightsRequest,
  RightsRequestDetail,
  RightsRequestRow,
  RightsRequestType,
  RightsScopeDecision,
  RightsScopeItem,
  RightsTransitionOption,
  RightsTriggerEvent,
  Uuid,
} from "@/types";

/* ==========================================================================
   Public - no session
   ========================================================================== */

export interface RightEntry {
  right: string;
  /** The section of the Act it comes from. Cited, not paraphrased. */
  section: string;
  description: string;
}

export interface RightsPayload {
  dpo_contact: string;
  how_to_exercise: RightEntry[];
  withdraw_consent: string;
  response_period_days: number;
  grievance_period_days: number;
  response_time: string;
  board_complaint: string;
}

export function getRights(): Promise<RightsPayload> {
  return apiGet<RightsPayload>("/rights");
}

export interface PublicRequestInput {
  request_type: RightsRequestType;
  contact: string;
  name?: string | null;
  request_text: string;
}

/** Recorded either way. The reply is the same neutral sentence whatever happened. */
export function submitPublicRequest(body: PublicRequestInput): Promise<PublicRequestReceipt> {
  return apiPost<PublicRequestReceipt>("/rights/requests", body);
}

export function verifyPublicRequest(body: {
  reference: string;
  code: string;
}): Promise<PublicVerifyResult> {
  return apiPost<PublicVerifyResult>("/rights/requests/verify", body);
}

export function getNomination(token: string): Promise<NominationView> {
  return apiGet<NominationView>(`/rights/nominations/${encodeURIComponent(token)}`);
}

/** A code to one of the contacts recorded on the nomination. The link alone proves only the link. */
export function requestNominationCode(
  token: string,
  medium: "mobile" | "email",
): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/rights/nominations/${encodeURIComponent(token)}/code`, { medium });
}

export function acceptNomination(token: string, code: string): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/rights/nominations/${encodeURIComponent(token)}/accept`, { code });
}

export function declineNomination(token: string, code: string): Promise<Acknowledged> {
  return apiPost<Acknowledged>(`/rights/nominations/${encodeURIComponent(token)}/decline`, { code });
}

/** The code goes to the contact *she* recorded, never the one typed now. */
export function nomineeStart(body: { nomination_uuid: string; contact: string }): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/rights/nominee/start", body);
}

export interface NomineeRequestInput {
  nomination_uuid: string;
  code: string;
  request_type: RightsRequestType;
  request_text: string;
  trigger_event: RightsTriggerEvent;
  evidence: File | null;
}

export function nomineeRequest(input: NomineeRequestInput): Promise<PublicRequestReceipt> {
  const form = new FormData();
  form.set("nomination_uuid", input.nomination_uuid);
  form.set("code", input.code);
  form.set("request_type", input.request_type);
  form.set("request_text", input.request_text);
  form.set("trigger_event", input.trigger_event);
  if (input.evidence) form.set("evidence", input.evidence);
  return apiPost<PublicRequestReceipt>("/rights/nominee/requests", form);
}

/* ==========================================================================
   The data principal - /me
   ========================================================================== */

export function listMyRequests(): Promise<MyRequest[]> {
  return apiGet<MyRequest[]>("/me/requests");
}

export function getMyRequest(uuid: Uuid): Promise<MyRequest> {
  return apiGet<MyRequest>(`/me/requests/${uuid}`);
}

export interface MyRequestInput {
  request_type: RightsRequestType;
  request_text: string;
  about_dpo?: boolean;
}

export function makeRequest(body: MyRequestInput): Promise<MyRequest> {
  return apiPost<MyRequest>("/me/requests", body);
}

export function listMyRequestTrail(uuid: Uuid): Promise<AuditEntry[]> {
  return apiGet<AuditEntry[]>(`/me/requests/${uuid}/trail`);
}

export function downloadMyResponse(uuid: Uuid) {
  return apiDownload(`/me/requests/${uuid}/download`);
}

/** She disputes the response: a grievance under s.13, linked to this request. */
export function disputeRequest(
  uuid: Uuid,
  body: { text: string; about_dpo?: boolean },
): Promise<MyRequest> {
  return apiPost<MyRequest>(`/me/requests/${uuid}/dispute`, body);
}

export function listMyNominations(): Promise<Nomination[]> {
  return apiGet<Nomination[]>("/me/nominations");
}

export interface NominationInput {
  nominee_name: string;
  nominee_mobile: string;
  nominee_email?: string | null;
  rights: RightsRequestType[];
}

export function nominate(body: NominationInput): Promise<Nomination> {
  return apiPost<Nomination>("/me/nominations", body);
}

export function revokeNomination(uuid: Uuid): Promise<Nomination> {
  return apiDelete<Nomination>(`/me/nominations/${uuid}`);
}

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
export const confirmHolder = (
  uuid: Uuid,
  holderUuid: Uuid,
  body: { responder_name?: string | null; responder_contact?: string | null },
) => apiPost<RightsHolder>(action(uuid, `holders/${holderUuid}/confirm`), body);
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
