/**
 * Reading rights requests.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getRequest,
  getRequestTrail,
  listRequests,
  type RequestFilters,
} from "@/features/rights/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { AuditEntry, Page, RightsRequestDetail, RightsRequestRow, Uuid } from "@/types";

/* ------------------------------------------------------------- the DPO */

export function useRequests(filters: RequestFilters = {}) {
  return useQuery<Page<RightsRequestRow>, ApiError>({
    queryKey: keys.rights.list(filters),
    queryFn: () => listRequests(filters),
  });
}

export function useRequest(uuid: Uuid | undefined) {
  return useQuery<RightsRequestDetail, ApiError>({
    queryKey: keys.rights.detail(uuid ?? ""),
    queryFn: () => getRequest(uuid!),
    enabled: Boolean(uuid),
  });
}

export function useRequestTrail(uuid: Uuid | undefined) {
  return useQuery<AuditEntry[], ApiError>({
    queryKey: keys.rights.trail(uuid ?? ""),
    queryFn: () => getRequestTrail(uuid!),
    enabled: Boolean(uuid),
  });
}
