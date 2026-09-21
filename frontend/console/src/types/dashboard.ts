/**
 * The dashboard payload. One endpoint, role-aware — the response shape differs
 * by role but the call does not, so the console has one loading path.
 */

import type { AuditEntry } from "@/types/audit";
import type { Role } from "@/types/enums";

/** One thing that needs this person today: a count, how urgent, where to act. */
export interface AttentionRow {
  key: string;
  label: string;
  count: number;
  severity: "critical" | "warning" | "info";
  /** A route, or an anchor (`#q-…`) to a queue further down the same page. */
  href: string;
}

export interface DashboardData {
  role: Role;
  counts: Record<string, number>;
  queues: Array<{ name: string; slug?: string; href?: string | null; items: Array<Record<string, unknown>> }>;
  /** Only rows with something to count; empty means nothing needs them today. */
  attention: AttentionRow[];
  /**
   * Recent activity, as audit entries — for every role.
   *
   * It was `Record<string, unknown>[]` because each role's endpoint returned a
   * different shape: project rows for an R&D User, exports for a DCO, a partial
   * audit projection for a DPO. The panel then guessed at a label from whichever
   * columns happened to be present, and could say that something changed without
   * saying what or who.
   *
   * Now one shape, so one renderer, and the dashboard panel cannot disagree with
   * the audit trail it is drawn from.
   */
  recent: AuditEntry[];
}
