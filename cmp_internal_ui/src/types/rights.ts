/**
 * Rights requests - sections 11 to 14 of the Act - and nominations.
 *
 * Two views of one record. The DPO's `RightsRequest` carries the verification
 * notes, the holders and the erasure scope; the data principal's `MyRequest`
 * carries what she is entitled to see of her own request and nothing that is
 * ours. Both carry the `Clock`, because every date on the flow is expressed
 * relative to D0 (receipt) and D (the published response period), and the
 * server computes those so the console and the acknowledgement email agree.
 */

import type { DateOnly, Timestamp, Uuid } from "@/types/primitives";

export type RightsRequestType = "access" | "correction" | "erasure" | "grievance";
export type RightsRequestStatus =
  | "received"
  | "in_progress"
  | "awaiting_holders"
  | "collating"
  | "closed";
export type RightsRequestOutcome =
  | "complete"
  | "partial"
  | "no_records"
  | "refused"
  | "not_verified"
  | "reclassified_withdrawal"
  | "upheld"
  | "not_upheld";
export type RightsRequestChannel = "portal" | "public_form" | "staff_logged" | "nominee";
export type RightsVerificationStatus = "pending" | "verified" | "failed";
export type RightsVerificationMethod = "session" | "code" | "manual";
export type RightsTicketStatus = "pending" | "issued" | "escalated" | "returned" | "unreturned";
export type RightsItemState = "proposed" | "decided" | "instructed" | "applied";
export type RightsScopeDecision = "erase" | "redact" | "retain" | "quarantine";
export type RightsTriggerEvent = "death" | "incapacity";
export type NominationStatus = "pending" | "active" | "declined" | "revoked";

export const RIGHTS_REQUEST_TYPES = [
  "access",
  "correction",
  "erasure",
  "grievance",
] as const satisfies readonly RightsRequestType[];

export const RIGHTS_REQUEST_STATUSES = [
  "received",
  "in_progress",
  "awaiting_holders",
  "collating",
  "closed",
] as const satisfies readonly RightsRequestStatus[];

/** One named point on the clock. `passed` is decided by the server's now. */
export interface ClockCheckpoint {
  key: "received" | "acknowledge" | "tickets" | "halfway" | "collate" | "due";
  label: string;
  at: Timestamp;
  passed: boolean;
}

/**
 * The clock column of the flow diagrams. D0 is `received_at`, D is `due_at`,
 * and the checkpoints between them are the ones the diagrams name.
 */
export interface Clock {
  received_at: Timestamp;
  due_at: Timestamp;
  acknowledge_by: Timestamp;
  tickets_by: Timestamp;
  halfway_at: Timestamp;
  collate_by: Timestamp;
  /** Negative once overdue. The sign is the point. */
  days_remaining: number;
  overdue: boolean;
  /** Past the collation checkpoint and still open. */
  at_risk: boolean;
  /** 0 to 1, clamped. */
  progress: number;
  checkpoints: ClockCheckpoint[];
  next_checkpoint: ClockCheckpoint["key"] | null;
}

/** A row of the DPO's register. */
export interface RightsRequestRow {
  request_uuid: Uuid;
  reference: string;
  request_type: RightsRequestType;
  original_type: RightsRequestType | null;
  status: RightsRequestStatus;
  outcome: RightsRequestOutcome | null;
  channel: RightsRequestChannel;
  subject_uuid: Uuid | null;
  subject_name: string | null;
  submitted_name: string | null;
  submitted_contact: string;
  received_at: Timestamp;
  due_at: Timestamp;
  acknowledged_at: Timestamp | null;
  verification_status: RightsVerificationStatus;
  about_dpo: boolean;
  linked_reference: string | null;
  holder_count: number;
  tickets_outstanding: number;
  closed_at: Timestamp | null;
  clock: Clock;
}

/** One party that holds her data, and the ticket issued to it. */
export interface RightsHolder {
  holder_uuid: Uuid;
  label: string;
  derived_from: "export_line" | "asset_consent" | "manual";
  /** What named this holder: export and asset uuids. Empty for a manual one. */
  evidence: { exports?: string[]; assets?: string[] };
  processor_uuid: Uuid | null;
  processor_name: string | null;
  is_in_house: boolean | null;
  confirmed_at: Timestamp | null;
  confirmed_by_name: string | null;
  ticket_status: RightsTicketStatus;
  instruction: string | null;
  responder_name: string | null;
  responder_contact: string | null;
  issued_at: Timestamp | null;
  due_at: Timestamp | null;
  escalated_at: Timestamp | null;
  returned_at: Timestamp | null;
  return_summary: string | null;
  return_evidence_hash: string | null;
  created_at: Timestamp;
  /** How this holder is reached: an account on the portal, or a mailed
   *  instruction the Privacy Office tracks by hand on `contact_log`. */
  channel: HolderChannel;
  respondent_uuid: Uuid | null;
  responder_user_uuid: Uuid | null;
  responder_user_name: string | null;
  contact_log: HolderContact[];
}

export type HolderChannel = "portal" | "email";

/** One line on a holder's contact log: what passed, when, to whom. */
export interface HolderContact {
  at: Timestamp;
  kind: string;
  to: string | null;
  by: number | null;
  note: string | null;
}

/** A ticket as the team it is addressed to sees it. */
export interface MyTicket {
  holder_uuid: Uuid;
  request_uuid: Uuid;
  reference: string;
  request_type: RightsRequestType;
  request_status: string;
  label: string;
  subject_name: string | null;
  instruction: string | null;
  ticket_status: RightsTicketStatus;
  issued_at: Timestamp | null;
  due_at: Timestamp | null;
  escalated_at: Timestamp | null;
  returned_at: Timestamp | null;
  return_summary: string | null;
  return_evidence_hash: string | null;
}

/**
 * One appearance of her in a collected asset, and what is to happen to it.
 *
 * `other_subjects` is the number that decides the shape of the decision: zero
 * is ordinary erasure; anything else is redaction, because deleting the file
 * would erase the other people's validly given consent along with her
 * contribution. Disposition sits on her junction row, never on the asset.
 */
export interface RightsScopeItem {
  item_uuid: Uuid;
  other_subjects: number;
  state: RightsItemState;
  decision: RightsScopeDecision | null;
  basis: string | null;
  retain_until: DateOnly | null;
  floor_passed_at: Timestamp | null;
  decided_at: Timestamp | null;
  decided_by_name: string | null;
  applied_at: Timestamp | null;
  disposition: string | null;
  disposition_at: Timestamp | null;
  subject_role: string;
  asset_uuid: Uuid;
  asset_type: string;
  source_asset_ref: string;
  source_code: string;
  source_name: string;
  processor_name: string | null;
  project_uuid: Uuid;
  project_name: string;
  collected_on: DateOnly;
  holder_uuid: Uuid | null;
  holder_label: string | null;
  holder_ticket_status: RightsTicketStatus | null;
}

/** What this user may do next, and why anything else is blocked. */
export interface RightsTransitionOption {
  to: RightsRequestStatus;
  allowed: boolean;
  /** `respond` for closure: made by the respond action, which records the outcome. */
  via: "transition" | "respond";
  blocked_by?: string;
  reason_required?: boolean;
}

/** The DPO's full view of one request. */
export interface RightsRequest extends RightsRequestRow {
  request_text: string;
  subject_email: string | null;
  subject_mobile: string | null;
  verification_method: RightsVerificationMethod | null;
  verified_at: Timestamp | null;
  verified_by_name: string | null;
  verification_note: string | null;
  classified_at: Timestamp | null;
  refusal_reason: string | null;
  intent_confirmed_at: Timestamp | null;
  linked_request_uuid: Uuid | null;
  linked_request_type: RightsRequestType | null;
  nomination_uuid: Uuid | null;
  nominee_name: string | null;
  nominee_contact: string | null;
  trigger_event: RightsTriggerEvent | null;
  trigger_evidence_hash: string | null;
  trigger_evidenced_at: Timestamp | null;
  reviewer_uuid: Uuid | null;
  reviewer_name: string | null;
  escalated_at: Timestamp | null;
  grievance_upheld: boolean | null;
  remedy_text: string | null;
  response_text: string | null;
  response_file_hash: string | null;
  responded_at: Timestamp | null;
  download_expires_at: Timestamp | null;
  created_at: Timestamp;
  updated_at: Timestamp;
  holders_confirmed: number;
  tickets_issued: number;
  tickets_returned: number;
  item_count: number;
  items_undecided: number;
}

export interface RightsRequestDetail extends RightsRequest {
  holders: RightsHolder[];
  items: RightsScopeItem[];
  transitions: RightsTransitionOption[];
}

/** Her own request. Nothing here is ours. */
export interface MyRequest {
  request_uuid: Uuid;
  reference: string;
  request_type: RightsRequestType;
  status: RightsRequestStatus;
  outcome: RightsRequestOutcome | null;
  channel: RightsRequestChannel;
  request_text: string;
  received_at: Timestamp;
  due_at: Timestamp;
  acknowledged_at: Timestamp | null;
  verification_status: RightsVerificationStatus;
  responded_at: Timestamp | null;
  response_text: string | null;
  refusal_reason: string | null;
  remedy_text: string | null;
  grievance_upheld: boolean | null;
  /** True while the released file can still be fetched from her account. */
  download_available: boolean;
  download_expires_at: Timestamp | null;
  linked_reference: string | null;
  closed_at: Timestamp | null;
  clock: Clock;
}

export interface Nomination {
  nomination_uuid: Uuid;
  nominee_name: string;
  nominee_mobile: string | null;
  nominee_email: string | null;
  rights: RightsRequestType[];
  status: NominationStatus;
  accept_expires_at: Timestamp | null;
  accepted_at: Timestamp | null;
  declined_at: Timestamp | null;
  revoked_at: Timestamp | null;
  created_at: Timestamp;
}

/** A contact recorded on a nomination, masked: enough to recognise, nothing to use. */
export interface NominationMedium {
  kind: "mobile" | "email";
  masked: string;
}

/** The acceptance link, as the nominee sees it. */
export interface NominationView {
  principal_name: string;
  nominee_name: string;
  rights: RightsRequestType[];
  accept_expires_at: Timestamp | null;
  /** The nominee chooses which of these the code goes to. */
  mediums: NominationMedium[];
}

/** The public form's reply. Neutral: it says the same thing whatever happened. */
export interface PublicRequestReceipt {
  reference: string;
  message: string;
}

export interface PublicVerifyResult {
  ok: boolean;
  reference: string;
  message: string;
}

export interface GrievanceDecisionResult {
  request: RightsRequest;
  rerun_reference: string | null;
  rerun_uuid: Uuid | null;
}
