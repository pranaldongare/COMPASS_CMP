/**
 * Reporting an incident: the public link's two calls, thin.
 *
 * A code to the address typed, then the report with that code. Neither takes a
 * session. Nothing is stored until the code comes back, and what the reporter
 * is given is a reference and nothing else (ADR 0037).
 */

import { apiPost } from "@/lib/api";
import type { Acknowledged } from "@/types";

export type CyberAttackAnswer = "yes" | "no" | "unknown";

export interface IncidentReportInput {
  name: string;
  email: string;
  code: string;
  title: string;
  incident_details: string;
  noticed_at: string | null;
  origin: string | null;
  discovery: string | null;
  affected_systems: string | null;
  impact_scale: string | null;
  countries_involved: string | null;
  data_nature: string | null;
  subject_types: string | null;
  entities_involved: string | null;
  third_parties: string | null;
  cyber_attack: CyberAttackAnswer | null;
}

export interface IncidentReportReceipt {
  /** INC-YYYY-NNNN: what they may quote. */
  reference: string;
  message: string;
}

/** The code goes to the address typed: it is theirs to prove. */
export function requestReportCode(email: string): Promise<Acknowledged> {
  return apiPost<Acknowledged>("/incident-reports/code", { email });
}

export function submitIncidentReport(body: IncidentReportInput): Promise<IncidentReportReceipt> {
  return apiPost<IncidentReportReceipt>("/incident-reports", body);
}
