/**
 * Personal data breaches (S3-01): the register, its determination, assessment
 * and duties.
 *
 * The server owns every clock. A duty's `clock` is computed there from due
 * times stored when the duty was created; this module only describes it, and
 * nothing in the console adds hours to anything.
 */
import type { Timestamp, Uuid } from "@/types/primitives";

export type BreachStatus = "open" | "closed";
export type BreachOutcome = "pending" | "yes" | "no";
export type BreachLocationKind = "platform" | "processor" | "data_source" | "other";
export type BreachDutyKind = "cert_in" | "board_intimation" | "board_report" | "principals";
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

export interface BreachTransition {
  to: BreachStatus;
  allowed: boolean;
  blocked_by: string | null;
  blockers: string[];
  reason_required: boolean;
}

export interface BreachSummary {
  breach_uuid: Uuid;
  reference: string;
  title: string;
  status: BreachStatus;
  detected_at: Timestamp;
  location: BreachLocation;
  determination: BreachOutcome;
  obligations: BreachDuty[];
}

export interface Breach extends Omit<BreachSummary, "obligations"> {
  became_aware_at: Timestamp | null;
  began_at: Timestamp | null;
  began_at_recorded: Timestamp | null;
  recorded_at: Timestamp;
  recorded_by_name: string | null;
  determinations: BreachDetermination[];
  assessment: BreachAssessment | null;
  assessment_revisions: number;
  obligations: BreachDuty[];
  status_history: BreachStatusChange[];
  transitions: BreachTransition[];
  /** The internal target for "without delay", in hours. Null while unset. */
  without_delay_target_hours: number | null;
}

export interface BreachInput {
  title: string;
  detected_at: Timestamp;
  began_at?: Timestamp | null;
  location_kind: BreachLocationKind;
  processor_uuid?: Uuid | null;
  source_uuid?: Uuid | null;
  location_detail?: string | null;
}

export interface BreachAssessmentInput extends Partial<BreachAssessmentFacts> {
  began_at?: Timestamp | null;
  categories: BreachCategory[];
}

/* ------------------------------------------------ who it touched (S3-02) */

export type BreachScopeKind = "processor" | "data_source" | "platform";

/** Where to look. A processor or a source by uuid; the platform by tables
 *  and a window of when their rows were written. */
export interface BreachScope {
  kind: BreachScopeKind;
  processor_uuid?: Uuid | null;
  source_uuid?: Uuid | null;
  tables?: string[];
  since?: Timestamp | null;
  until?: Timestamp | null;
}

/** Which exports, assets or tables put a person on the list. Ids only. */
export interface BreachEvidence {
  exports: string[];
  assets: string[];
  tables: string[];
}

export interface BreachPerson {
  person_uuid: Uuid;
  full_name: string | null;
  role: string;
  has_email: boolean;
  has_mobile: boolean;
  found_by: BreachScopeKind | "dpo";
  evidence: BreachEvidence;
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
  platform_tables: string[];
}
