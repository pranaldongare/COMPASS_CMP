/**
 * Reading rights requests.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getMyRequest,
  listMyNominations,
  listNominationsNamingMe,
  listMyRequestTrail,
  listMyRequests,
} from "@/features/rights/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { AuditEntry, MyRequest, Nomination, NomineeOf, Uuid } from "@/types";

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

export function useNominationsNamingMe() {
  return useQuery<NomineeOf[], ApiError>({
    queryKey: keys.me.nomineeOf,
    queryFn: listNominationsNamingMe,
  });
}
