/**
 * Reading, summarising and verifying the audit trail.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getAuditSummary,
  getAuditVocabulary,
  listAudit,
  lookupAudit,
  verifyAuditChain,
} from "@/features/audit/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  AuditEntry,
  AuditLookupHit,
  AuditSummary,
  AuditVerification,
  AuditVocabulary,
  Page,
} from "@/types";

export function useAudit(filters: Record<string, unknown> = {}) {
  return useQuery<Page<AuditEntry>, ApiError>({
    queryKey: keys.audit.list(filters),
    queryFn: () => listAudit(filters),
  });
}

export function useAuditSummary(filters: Record<string, unknown> = {}) {
  return useQuery<AuditSummary, ApiError>({
    queryKey: keys.audit.summary(filters),
    queryFn: () => getAuditSummary(filters),
  });
}

/** Rarely changes: it is the code's vocabulary. Kept for the session. */
export function useAuditVocabulary() {
  return useQuery<AuditVocabulary, ApiError>({
    queryKey: keys.audit.vocabulary,
    queryFn: getAuditVocabulary,
    staleTime: 60 * 60 * 1000,
  });
}

export function useAuditLookup(kind: string, q: string, enabled = true) {
  return useQuery<AuditLookupHit[], ApiError>({
    queryKey: keys.audit.lookup(kind, q),
    queryFn: () => lookupAudit(kind, q),
    enabled: enabled && Boolean(kind) && q.length > 0,
    staleTime: 30 * 1000,
  });
}

export function useAuditVerify(enabled = false) {
  return useQuery<AuditVerification, ApiError>({
    queryKey: keys.audit.verify,
    queryFn: () => verifyAuditChain(),
    // Walking the whole chain is not free. Run it on request, not on page load.
    enabled,
    staleTime: 0,
    gcTime: 0,
  });
}
