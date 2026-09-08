/**
 * Rights requests and nominations: the data principal's side, thin.
 *
 * Two audiences share one record here. The public form and the nominee's
 * entry points need no session and answer neutrally; the data principal's
 * calls are scoped to her by the server. The DPO's register lives on the staff
 * console. Nothing here decides anything - the clock, the gates and the early
 * exits are the server's, and these functions carry the answer back.
 */

import { apiDelete, apiDownload, apiGet, apiPost } from "@/lib/api";
import type {
  Acknowledged,
  AuditEntry,
  MyRequest,
  Nomination,
  NominationView,
  NomineeOf,
  PublicRequestReceipt,
  PublicVerifyResult,
  RightsRequestType,
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

/** Nominations that name *her* - somebody else's, where she is the nominee. */
export function listNominationsNamingMe(): Promise<NomineeOf[]> {
  return apiGet<NomineeOf[]>("/me/nominee-of");
}
