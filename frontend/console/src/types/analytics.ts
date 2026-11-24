/**
 * Analytics, audit and health reports, and reports made as files (ADR 0045).
 *
 * The page is driven by the catalogue: which sections the signed-in role has,
 * whether they may choose an office, the metrics with their units and
 * breakdowns, the periods, the report kinds and the audit reports. Nothing
 * here hard-codes who sees what - the server's catalogue says so, from the
 * same matrix it enforces with.
 *
 * Figures are counts. A count of people above nought and below the threshold
 * is withheld: `suppressed` is true and `value` is null. Withheld is not zero,
 * and the page never shows it as one.
 */

import type { Timestamp, Uuid } from "@/types/primitives";

/** The sections of the Analytics page, in the server's order. */
export type AnalyticsSection =
  | "management"
  | "analytics"
  | "mine"
  | "audit"
  | "health"
  | "quality"
  | "inventory"
  | "reports";

export type MetricUnit = "count" | "percent" | "days" | "hours";
export type MetricKind = "count" | "median" | "ratio" | "snapshot" | "live";
export type RagStatus = "green" | "amber" | "red";
export type ReportFormat = "pdf" | "xlsx" | "csv";
export type ReportStatus = "queued" | "ready" | "failed";
export type OfficeCode = "rnd" | "hr";

export interface Choice {
  key: string;
  label: string;
}

export interface MetricInfo {
  key: string;
  title: string;
  /** Exactly what is counted, in words. */
  definition: string;
  unit: string;
  section: string;
  /** The heading it sits under on its page. */
  group: string;
  kind: string;
  /** The breakdowns it may be split by. */
  dims: string[];
  /** Counts people, so small numbers are withheld. */
  people: boolean;
  /** For a rate: the two counts it divides. */
  numerator: string | null;
  denominator: string | null;
  higher_is_better: boolean;
}

export interface ReportKindInfo {
  key: string;
  title: string;
  description: string;
  formats: string[];
  /** May be made on a cadence and mailed. */
  schedulable: boolean;
  /** Who a schedule of it may be mailed to, as role keys. */
  recipient_roles: string[];
}

export interface AuditReportInfo {
  key: string;
  title: string;
  description: string;
}

export interface Catalogue {
  role: string;
  /** The session's office; null for management and the administrator. */
  office: string | null;
  /** Management only: the figures may be of one office or both. */
  may_choose_office: boolean;
  sections: string[];
  metrics: MetricInfo[];
  dimensions: Choice[];
  periods: Choice[];
  cadences: Choice[];
  reports: ReportKindInfo[];
  audit_reports: AuditReportInfo[];
}

export interface AnalyticsPeriod {
  preset: string;
  start: Timestamp;
  end: Timestamp;
  label: string;
  start_date: string;
  end_date: string;
}

export interface FigurePoint {
  bucket: string | null;
  value: number | null;
  suppressed: boolean;
}

export interface FigurePart {
  key: string | null;
  label: string;
  value: number | null;
  suppressed: boolean;
}

export interface Figure {
  key: string;
  title: string;
  definition: string;
  unit: string;
  section: string;
  group: string;
  kind: string;
  dims: string[];
  /** For a rate: the two counts it divides, so a page can say "x of y". */
  numerator: string | null;
  denominator: string | null;
  /** Null when withheld, or when there is nothing to divide by. */
  value: number | null;
  suppressed: boolean;
  previous: number | null;
  previous_suppressed: boolean;
  /** `value - previous`, in the figure's unit. */
  change: number | null;
  target: number | null;
  /** The line between amber and red; null when amber is the target itself. */
  amber: number | null;
  higher_is_better: boolean;
  status: string | null;
  series: FigurePoint[];
  breakdown: FigurePart[];
}

export interface Figures {
  period: AnalyticsPeriod;
  previous: AnalyticsPeriod | null;
  office: string | null;
  dim: string | null;
  grain: string | null;
  /** Fewer people than this is withheld. */
  threshold: number;
  metrics: Figure[];
}

export interface FiguresParams {
  section?: string;
  keys?: string[];
  period?: string;
  start?: string;
  end?: string;
  office?: string;
  dim?: string;
  compare?: boolean;
  trend?: boolean;
  /** The line's bucket, instead of the period's own: day, week or month. */
  grain?: string;
}

export interface PeriodParams {
  period: string;
  start?: string;
  end?: string;
}

/** The record of processing: rows as the register has them. */
export interface Inventory {
  purposes: Record<string, unknown>[];
  processors: Record<string, unknown>[];
  sources: Record<string, unknown>[];
}

export interface AuditReportRow {
  log_uuid: Uuid;
  event_type: string;
  entity_type?: string | null;
  occurred_at: Timestamp;
  actor_uuid?: Uuid | null;
  actor_name?: string | null;
  actor_role?: string | null;
  subject_uuid?: Uuid | null;
  subject_name?: string | null;
  detail?: Record<string, unknown> | null;
}

export interface AuditReportCount {
  key: string;
  count: number;
}

/** The shape of the rows the report selects (the audit trail's summary). */
export interface AuditReportSummary {
  total?: number;
  first_at?: Timestamp | null;
  last_at?: Timestamp | null;
  by_event?: AuditReportCount[];
  by_group?: AuditReportCount[];
  by_actor_role?: AuditReportCount[];
  by_day?: { day: string; count: number }[];
  days?: number;
}

export interface AuditReport {
  key: string;
  title: string;
  description: string;
  events: string[];
  period: AnalyticsPeriod;
  items: AuditReportRow[];
  next_cursor: string | null;
  total: number;
  summary: Record<string, unknown>;
}

export interface MetricTarget {
  key: string;
  title: string;
  unit: string;
  section: string;
  group: string;
  higher_is_better: boolean;
  default_target: number | null;
  default_amber: number | null;
  /** In force: the administrator's if customised, else the default. */
  target: number | null;
  amber: number | null;
  customised: boolean;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export interface AnalyticsSettings {
  /** 1-100. A count of fewer people than this is withheld; 1 withholds nothing. */
  small_number_threshold: number;
  updated_at: Timestamp | null;
  updated_by_name: string | null;
  targets: MetricTarget[];
}

export interface TargetInput {
  target: number;
  amber?: number | null;
}

export interface Report {
  report_uuid: Uuid;
  kind: string;
  title: string;
  params: Record<string, unknown>;
  office: string | null;
  format: string;
  status: string;
  file_sha256: string | null;
  file_bytes: number | null;
  /** Why it failed, when it did. */
  error: string | null;
  requested_by_name: string | null;
  requested_role: string;
  /** Set when a schedule made it. */
  schedule_uuid: Uuid | null;
  created_at: Timestamp;
  ready_at: Timestamp | null;
}

export interface ReportInput {
  kind: string;
  format: ReportFormat;
  period?: string | null;
  start?: string | null;
  end?: string | null;
  office?: OfficeCode | null;
  audit?: string | null;
  entity_type?: "rights_request" | "breach" | null;
  entity_uuid?: Uuid | null;
}

export interface ReportSchedule {
  schedule_uuid: Uuid;
  kind: string;
  title: string;
  params: Record<string, unknown>;
  format: string;
  cadence: string;
  recipient_roles: string[];
  office: string | null;
  active: boolean;
  created_by_name: string | null;
  created_role: string;
  created_at: Timestamp;
  last_run_at: Timestamp | null;
  next_run_at: Timestamp;
}

export interface ScheduleInput {
  kind: string;
  format: ReportFormat;
  cadence: "weekly" | "monthly" | "quarterly";
  recipient_roles: string[];
  office?: OfficeCode | null;
  audit?: string | null;
}
