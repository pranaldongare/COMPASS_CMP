/**
 * The audit trail.
 *
 * Read-only by construction: the table is append-only, enforced by a trigger,
 * and there is no endpoint that would edit or remove a row. The only write-ish
 * operation is the verification below, which reads the chain and reports on it
 * - and the CSV download, which the server records as an event in the trail
 * itself, because taking a copy of the evidence is an act on it.
 *
 * The list, the summary and the download take the same filters, so the three
 * always describe one question.
 */

import { apiDownload, apiGet, queryString } from "@/lib/api";
import type {
  AuditEntry,
  AuditLookupHit,
  AuditSummary,
  AuditVerification,
  AuditVocabulary,
  Page,
} from "@/types";

export function listAudit(
  filters: Record<string, unknown> = {},
): Promise<Page<AuditEntry>> {
  return apiGet<Page<AuditEntry>>(`/audit${queryString(filters)}`);
}

export function getAuditSummary(
  filters: Record<string, unknown> = {},
): Promise<AuditSummary> {
  return apiGet<AuditSummary>(`/audit/summary${queryString(filters)}`);
}

export function getAuditVocabulary(): Promise<AuditVocabulary> {
  return apiGet<AuditVocabulary>("/audit/vocabulary");
}

export function lookupAudit(kind: string, q: string): Promise<AuditLookupHit[]> {
  return apiGet<AuditLookupHit[]>(`/audit/lookup${queryString({ kind, q })}`);
}

/** The rows the filters select, as a file. Newest first, capped server-side. */
export function downloadAudit(filters: Record<string, unknown> = {}) {
  return apiDownload(`/audit/export.csv${queryString(filters)}`);
}

/**
 * Recompute the SHA-256 hash chain and report the first break, if any.
 *
 * Expensive — it walks the table — which is why the hook that calls it is
 * disabled until somebody explicitly asks.
 */
export function verifyAuditChain(): Promise<AuditVerification> {
  return apiGet<AuditVerification>("/audit/verify");
}
