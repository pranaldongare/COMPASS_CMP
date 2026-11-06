/**
 * Personal data breaches (S3-01): the register, its determination, assessment
 * and duties.
 *
 * The server owns every clock. A duty's `clock` is computed there from due
 * times stored when the duty was created; this module only describes it, and
 * nothing in the console adds hours to anything.
 */
import type { DateOnly, Timestamp, Uuid } from "@/types/primitives";
import type { TicketMessage } from "@/types/rights";

export type BreachStatus = "open" | "closed";
export type BreachOutcome = "pending" | "yes" | "no";
export type BreachLocationKind = "platform" | "processor" | "data_source" | "other";
export type BreachDutyKind = "org_board" | "cert_in" | "board_intimation" | "board_report" | "principals";
export type BreachDutyState = "outstanding" | "done" | "not_applicable";

export interface BreachLocation {
  kind: BreachLocationKind;
  processor_uuid: Uuid | null;
  processor_name: string | null;
  source_uuid: Uuid | null;
  source_name: string | null;
  detail: string | null;
}

export interface BreachClock {
  /** No statutory hours: read as time elapsed, against the internal target. */
  without_delay: boolean;
  seconds_remaining: number | null;
  overdue: boolean;
  seconds_elapsed: number | null;
  /** When the internal target falls. Null while no target is configured. */
  target_at: Timestamp | null;
  past_target: boolean;
}

export interface BreachDutyEvent {
  event_uuid: Uuid;
  kind: "completed" | "not_applicable" | "reinstated" | "extended" | "reopened";
  occurred_at: Timestamp | null;
  reference: string | null;
  note: string | null;
  /** On a report to the organisation's board: to whom. */
  reported_to: string | null;
  due_at: Timestamp | null;
  requested_at: Timestamp | null;
  determination_uuid: Uuid | null;
  recorded_at: Timestamp;
  recorded_by_name: string | null;
}

export interface BreachDuty {
  obligation_uuid: Uuid;
  duty: BreachDutyKind;
  label: string;
  basis: string;
  created_at: Timestamp;
  state: BreachDutyState;
  due_at: Timestamp | null;
  anchored_at: Timestamp | null;
  completed_at: Timestamp | null;
  reference: string | null;
  /** The organisation's board: to whom it was reported. */
  reported_to: string | null;
  extended_until: Timestamp | null;
  extension_requested_at: Timestamp | null;
  clock: BreachClock;
  events: BreachDutyEvent[];
}

export interface BreachDetermination {
  determination_uuid: Uuid;
  outcome: BreachOutcome;
  reasoning: string;
  became_aware_at: Timestamp | null;
  determined_at: Timestamp;
  determined_by_name: string | null;
}

export interface BreachCategory {
  category: string;
  /** Whether the exposed values were sealed. */
  sealed: boolean;
  /** Whether the key that seals them was exposed too. */
  key_exposed: boolean;
}

/** The facts Rule 7 asks for, as of one revision. */
export interface BreachAssessmentFacts {
  nature_extent: string | null;
  likely_impact: string | null;
  consequences: string | null;
  circumstances: string | null;
  mitigation: string | null;
  protective_steps: string | null;
  caused_by_findings: string | null;
  remedial_measures: string | null;
  contact_point: string | null;
}

export interface BreachAssessment extends BreachAssessmentFacts {
  assessment_uuid: Uuid;
  revision: number;
  began_at: Timestamp | null;
  categories: BreachCategory[];
  revised_at: Timestamp;
  revised_by_name: string | null;
}

export interface BreachStatusChange {
  from_status: BreachStatus | null;
  to_status: BreachStatus;
  reason: string | null;
  changed_at: Timestamp;
  changed_by_name: string | null;
}

export type BreachAttachmentKind = "email" | "proof" | "chat" | "other" | "approval" | "sent_mail";

/** A file kept with an incident as evidence (2026-10-06). Never replaced or
 *  removed; the name and the note are sealed. */
export interface BreachAttachment {
  attachment_uuid: Uuid;
  kind: BreachAttachmentKind;
  note: string | null;
  file_name: string;
  sha256: string;
  size_bytes: number;
  content_type: string;
  added_at: Timestamp;
  added_by_name: string | null;
}

export interface BreachTransition {
  to: BreachStatus;
  allowed: boolean;
  blocked_by: string | null;
  blockers: string[];
  reason_required: boolean;
}

export interface BreachSummary {
  breach_uuid: Uuid;
  /** What it is quoted by: the breach reference once recorded, the incident's until then. */
  reference: string;
  /** INC-YYYY-NNNN from logging onwards (a row logged before 0038 carries BR-). */
  incident_reference: string;
  /** BR-YYYY-NNNN, issued by the first determination of yes. Null until then. */
  breach_reference: string | null;
  title: string;
  status: BreachStatus;
  detected_at: Timestamp;
  location: BreachLocation;
  determination: BreachOutcome;
  obligations: BreachDuty[];
  /** When anything last happened to it - it, its notices or its tickets -
   *  from the audit trail. The register's "recent activity". */
  last_activity_at: Timestamp;
  /** Its tickets issued or returned, and those past their answer-by. */
  tickets_open: number;
  tickets_overdue: number;
}

export interface Breach
  extends Omit<BreachSummary, "obligations" | "last_activity_at" | "tickets_open" | "tickets_overdue"> {
  /** When the first yes recorded it as a breach, and who made it. */
  breach_recorded_at: Timestamp | null;
  breach_recorded_by_name: string | null;
  became_aware_at: Timestamp | null;
  began_at: Timestamp | null;
  began_at_recorded: Timestamp | null;
  /** What else was said when it was logged (0047). */
  logged: BreachLogged;
  cyber_attack: BreachCyberAttack | null;
  /** Who reported it through the public link. Null if the office logged it. */
  reported: BreachReported | null;
  recorded_at: Timestamp;
  recorded_by_name: string | null;
  determinations: BreachDetermination[];
  assessment: BreachAssessment | null;
  assessment_revisions: number;
  obligations: BreachDuty[];
  status_history: BreachStatusChange[];
  /** Files kept with it, oldest first. */
  attachments: BreachAttachment[];
  transitions: BreachTransition[];
  /** The internal target for "without delay", in hours. Null while unset. */
  without_delay_target_hours: number | null;
}

/** Who reported an incident through the public link (0058). Sealed. */
export interface BreachReported {
  reporter_name: string;
  reporter_email: string;
  received_at: Timestamp;
  /** When they say they noticed it. Nothing is anchored on it. */
  noticed_at: Timestamp | null;
  cyber_attack: BreachCyberAttack | null;
}

/** A report waiting in the shared intake, as the list shows it. */
export interface IncidentReportRow {
  report_uuid: Uuid;
  reference: string;
  reporter_name: string;
  reporter_email: string;
  title: string;
  noticed_at: Timestamp | null;
  received_at: Timestamp;
  cyber_attack: BreachCyberAttack | null;
}

/** A page of the shared intake, oldest first. */
export interface IncidentReportPage {
  items: IncidentReportRow[];
  /** Every report waiting, not only this page's. */
  total: number;
  limit: number;
  offset: number;
}

/** One waiting report with everything it said, for an office to read. */
export interface IncidentReport extends IncidentReportRow {
  logged: BreachLogged;
}

/** A report an office did not take up: kept, with who dismissed it and why. */
export interface DismissedReport {
  reference: string;
  reporter_name: string;
  reporter_email: string;
  title: string;
  received_at: Timestamp;
  dismissed_at: Timestamp;
  dismissed_by_name: string | null;
  dismissal_reason: string;
}

/** What else is known when an incident is logged (0047): every one optional
 *  free text, sealed, fixed once logged. */
export interface BreachLogged {
  origin?: string | null;
  discovery?: string | null;
  affected_systems?: string | null;
  incident_details?: string | null;
  impact_scale?: string | null;
  countries_involved?: string | null;
  data_nature?: string | null;
  subject_types?: string | null;
  entities_involved?: string | null;
  third_parties?: string | null;
}

/** Is it a cyber attack? Yes makes it reportable to CERT-In at once. */
export type BreachCyberAttack = "yes" | "no" | "unknown";

export interface BreachInput extends BreachLogged {
  title: string;
  detected_at: Timestamp;
  began_at?: Timestamp | null;
  location_kind: BreachLocationKind;
  processor_uuid?: Uuid | null;
  source_uuid?: Uuid | null;
  location_detail?: string | null;
  cyber_attack?: BreachCyberAttack | null;
}

export interface BreachAssessmentInput extends Partial<BreachAssessmentFacts> {
  began_at?: Timestamp | null;
  categories: BreachCategory[];
}

/* ------------------------------------------------ the people affected (S3-02) */

export type BreachScopeKind = "project" | "processor" | "data_source";

/** Where to look: a project or activity, a vendor or a data source, by uuid.
 *  A project may narrow to consents given in a period. */
export interface BreachScope {
  kind: BreachScopeKind;
  project_uuid?: Uuid | null;
  processor_uuid?: Uuid | null;
  source_uuid?: Uuid | null;
  since?: Timestamp | null;
  until?: Timestamp | null;
}

/** Which records put a person on the list. Ids only. */
export interface BreachEvidence {
  projects: string[];
  exports: string[];
  assets: string[];
  tables: string[];
}

/** A project or activity with people in it, to choose from. */
export interface BreachProjectOption {
  project_uuid: Uuid;
  project_name: string;
  is_activity: boolean;
  people: number;
}

export interface BreachPerson {
  person_uuid: Uuid;
  full_name: string | null;
  role: string;
  has_email: boolean;
  has_mobile: boolean;
  /** `upload`: matched by email or mobile in a list somebody sent (2026-10-07).
   *  `platform`: listed before tables stopped being a way to look. */
  found_by: BreachScopeKind | "dpo" | "upload" | "platform";
  evidence: BreachEvidence;
}

/** A list of the people a breach affected, or of its assets (2026-10-07). */
export type BreachListKind = "contacts" | "assets";

/** What a list comes to: checked (nothing written), or taken. */
export interface BreachListReport {
  kind: BreachListKind;
  rows_read: number;
  /** People with an account the file matched, not yet listed. */
  matched_people: number;
  /** People with no account, kept as this breach's contacts. */
  new_contacts: number;
  /** Rows already on the list, or repeated: skipped. */
  already_listed: number;
  /** Rows that could not be read; the first fifty are in `errors`. */
  unreadable: number;
  /** Assets only: people in them who consented to nothing - nobody to trace. */
  untraceable: number;
  would_add: number;
  errors: { row: number; message: string }[];
  more_errors: number;
  upload_uuid?: Uuid | null;
}

/** Somebody affected who has no account: told by email and SMS. */
export interface BreachContact {
  contact_uuid: Uuid;
  full_name: string | null;
  email: string | null;
  mobile: string | null;
  added_at: Timestamp;
  upload_uuid: Uuid;
  upload_kind: BreachListKind;
}

export interface BreachUpload {
  upload_uuid: Uuid;
  kind: BreachListKind;
  file_name: string;
  sha256: string;
  rows_read: number;
  matched_people: number;
  new_contacts: number;
  already_listed: number;
  unreadable: number;
  untraceable: number;
  added_at: Timestamp;
  added_by_name: string | null;
}

export interface BreachContacts {
  total: number;
  contacts: BreachContact[];
  next_cursor: string | null;
  uploads: BreachUpload[];
}

export interface BreachAffectedPerson extends BreachPerson {
  affected_uuid: Uuid;
  /** The revision that first listed them. */
  revision: number;
}

export interface BreachCandidate extends BreachPerson {
  already_listed: boolean;
}

export interface BreachPreview {
  scopes: Record<string, unknown>[];
  derived: number;
  already_listed: number;
  would_add: number;
  /** A sample of the people found; `derived` is the count. */
  people: BreachCandidate[];
}

export interface BreachAffectedRevision {
  revision_uuid: Uuid;
  revision: number;
  scopes: Record<string, unknown>[];
  derived: number;
  added_by_hand: number;
  excluded: number;
  newly_listed: number;
  note: string | null;
  confirmed_at: Timestamp;
  confirmed_by_name: string | null;
}

export interface BreachAffected {
  total: number;
  revisions: BreachAffectedRevision[];
  people: BreachAffectedPerson[];
  next_cursor: string | null;
  /** The tables a platform scope may name. */
}

/* --------------------------------------------- telling the people (S3-03) */

/** Rule 7(1)(a) to (e). */
export interface BreachNoticeWords {
  what_happened: string;
  consequences: string;
  measures: string;
  protective_steps: string;
  contact: string;
}

export interface BreachNotice extends BreachNoticeWords {
  notice_uuid: Uuid;
  version: number;
  /** An approved notice does not change; an update is a new version. */
  state: "draft" | "approved";
  created_at: Timestamp;
  created_by_name: string | null;
  updated_at: Timestamp;
  approved_at: Timestamp | null;
  approved_by_name: string | null;
}

/** How many people are in each state, per version and channel. */
export interface BreachDeliveryCount {
  notice_uuid: Uuid;
  version: number;
  channel: "portal" | "email" | "sms";
  status: "queued" | "delivered" | "failed";
  people: number;
  last_at: Timestamp;
}

export interface BreachDeliveryFailure {
  version: number;
  channel: "portal" | "email" | "sms";
  attempt: number;
  detail: Record<string, unknown>;
  recorded_at: Timestamp;
  /** Exactly one: an account, or a contact with no account. */
  person_uuid: Uuid | null;
  contact_uuid?: Uuid | null;
  full_name: string | null;
}

export interface BreachNotices {
  versions: BreachNotice[];
  /** Rule 7(2)(b)(vi): the account of notices to principals. */
  account: BreachDeliveryCount[];
  failures: BreachDeliveryFailure[];
  listed: number;
  /** Of `listed`, contacts with no account: email and SMS only. */
  contacts: number;
  /** Listed people with no version yet whose every channel has an outcome. */
  unnotified: number;
  contents: { key: keyof BreachNoticeWords; label: string }[];
  duty: string;
  /** Why nothing may be sent yet - not recorded as a breach - or null. */
  send_blocked_by: string | null;
}

/* -------------------------------------------------- breach tickets (S3-08) */

export type BreachTicketState = "issued" | "returned" | "closed" | "withdrawn";
export type BreachTicketMoveKind = "return" | "send_back" | "close" | "withdraw" | "reopen";

/** A move this side may make now, as the server says. Neither side keeps the table. */
export interface BreachTicketMove {
  move: BreachTicketMoveKind;
  reason_required: boolean;
}

export interface BreachTicketEvent {
  event_uuid: Uuid;
  kind: "returned" | "sent_back" | "closed" | "withdrawn" | "reopened" | "date_changed";
  outcome: "done" | "partial" | "failed" | null;
  summary: string | null;
  reason: string | null;
  /** With a date_changed: the date it replaced, and the new one. */
  date_before?: DateOnly | null;
  date_after?: DateOnly | null;
  occurred_at: Timestamp;
  actor_name: string | null;
}

/** A breach ticket as the office reads it. */
export interface BreachTicket {
  ticket_uuid: Uuid;
  holder_uuid: Uuid;
  holder_name: string | null;
  assigned_by_name: string | null;
  /** Set when a holder added this person as a colleague (S3-09). */
  parent_ticket_uuid: Uuid | null;
  added_by_name: string | null;
  state: BreachTicketState;
  answer_by: DateOnly | null;
  overdue: boolean;
  created_at: Timestamp;
  unread: number;
  last_activity_at: Timestamp | null;
  events: BreachTicketEvent[];
  moves: BreachTicketMove[];
  may_write: boolean;
  /** Whether the date may be changed now. */
  may_change_date: boolean;
  /** The holder's breach-only login (S3-09): pending until they set a
   *  password, then active, then ended. Null for a member of staff. */
  temporary_access: TemporaryAccess | null;
}

export type TemporaryAccess = "pending" | "active" | "ended";

export interface BreachTicketDetail {
  ticket: BreachTicket;
  instruction: string;
  messages: TicketMessage[];
}

/** Exactly what a holder is given (BD-13): nothing else from the register. */
export interface MyBreachTicket {
  ticket_uuid: Uuid;
  breach_reference: string;
  instruction: string;
  state: BreachTicketState;
  answer_by: DateOnly | null;
  created_at: Timestamp;
  unread: number;
  last_activity_at: Timestamp | null;
  moves: BreachTicketMove[];
  /** Whether they may bring in a colleague now: while the ticket is open. */
  may_add_colleague: boolean;
  /** Whether they may change the date now: while the ticket is open. */
  may_change_date: boolean;
}

export interface MyBreachTicketDetail {
  ticket: MyBreachTicket;
  messages: TicketMessage[];
}

/* -------------------------------------------- reports on a breach (0059) */

export type BreachDocumentKind =
  | "org_board"
  | "board_intimation"
  | "cert_in"
  | "board_report"
  | "closure";
export type BreachDocumentState = "draft" | "finalised" | "filed";

export interface BreachDocumentSection {
  key: string;
  label: string;
  required: boolean;
  /** Sealed; the API client opens it. */
  body: string | null;
}

export interface BreachDocumentProof {
  attachment_uuid: Uuid;
  kind: "approval" | "sent_mail";
  note: string | null;
  file_name: string;
  sha256: string;
  size_bytes: number;
  added_at: Timestamp;
  added_by_name: string | null;
}

/** One address a report was mailed to, its latest state. */
export interface BreachDocumentMailRecipient {
  recipient_uuid: Uuid;
  /** Sealed; null where the list holds only an address. */
  full_name: string | null;
  /** Sealed. */
  email: string;
  status: "queued" | "delivered" | "failed";
  attempt: number;
  /** Why it failed, as an error's class. */
  error: string | null;
  recorded_at: Timestamp;
  /** Taken off the list since: sending again leaves it as it stands. */
  removed: boolean;
}

/** What became of the mail to the organisation's board. */
export interface BreachDocumentMail {
  delivered: number;
  queued: number;
  failed: number;
  /** Of the queued, to addresses still on the list: lost before the worker saw
   *  them, which sending again queues again. */
  stale: number;
  /** How many addresses sending again would queue now. None on a draft, a
   *  superseded version, a report that may not go, an empty list or a closed
   *  breach. */
  retryable: number;
  recipients: BreachDocumentMailRecipient[];
}

/** One version of one report. */
export interface BreachDocument {
  report_uuid: Uuid;
  kind: BreachDocumentKind;
  title: string;
  version: number;
  state: BreachDocumentState;
  sections: BreachDocumentSection[];
  created_at: Timestamp;
  created_by_name: string | null;
  updated_at: Timestamp;
  finalised_at: Timestamp | null;
  finalised_by_name: string | null;
  filed_at: Timestamp | null;
  filed_reference: string | null;
  filed_by_name: string | null;
  evidence: BreachDocumentProof[];
  mail: BreachDocumentMail;
}

/** One kind of report, with every version of it, newest first. */
export interface BreachDocumentKindView {
  kind: BreachDocumentKind;
  title: string;
  basis: string;
  duty: BreachDutyKind | null;
  duty_state: BreachDutyState | null;
  /** Why it may not be written yet, in the server's words. */
  blocked_by: string | null;
  goes_to_regulator: boolean;
  versions: BreachDocument[];
}

export interface BreachDocuments {
  kinds: BreachDocumentKindView[];
  board_recipients: number;
  proofs: { kind: "approval" | "sent_mail"; label: string }[];
}

/** What a press of Try again answers: the reports, and how many it queued. */
export interface BreachDocumentsResent extends BreachDocuments {
  queued: number;
}

/* ---------------------------------------------- who hears of a breach (0058) */

export interface BreachBoardRecipient {
  recipient_uuid: Uuid;
  full_name: string | null;
  email: string;
  added_at: Timestamp;
  added_by_name: string | null;
}

export interface BreachSettings {
  intake_roles: string[];
  roles: { role: string; title: string }[];
  /** Always told, whatever is chosen. */
  officers: string[];
  board_recipients: BreachBoardRecipient[];
  /** The public link, to give out. */
  report_link: string;
}
