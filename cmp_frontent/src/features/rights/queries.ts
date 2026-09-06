/**
 * Reading rights requests.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getMyRequest,
  getRequest,
  getRequestTrail,
  listMyNominations,
  listMyRequestTrail,
  listMyRequests,
  listRequests,
  type RequestFilters,
} from "@/features/rights/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  AuditEntry,
  MyRequest,
  Nomination,
  Page,
  RightsRequestDetail,
  RightsRequestRow,
  Uuid,
} from "@/types";

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

/* ------------------------------------------------------ the principal */

export function useMyRequests() {
  return useQuery<MyRequest[], ApiError>({
    queryKey: keys.me.requests,
    queryFn: listMyRequests,
  });
}

export function useMyRequest(uuid: Uuid | undefined) {
  return useQuery<MyRequest, ApiError>({
    queryKey: keys.me.request(uuid ?? ""),
    queryFn: () => getMyRequest(uuid!),
    enabled: Boolean(uuid),
  });
}

export function useMyRequestTrail(uuid: Uuid | undefined) {
  return useQuery<AuditEntry[], ApiError>({
    queryKey: keys.me.requestTrail(uuid ?? ""),
    queryFn: () => listMyRequestTrail(uuid!),
    enabled: Boolean(uuid),
  });
}

export function useMyNominations() {
  return useQuery<Nomination[], ApiError>({
    queryKey: keys.me.nominations,
    queryFn: listMyNominations,
  });
}
