/**
 * Reading rights requests.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getRequest,
  holderThread,
  listMyTickets,
  myTicket,
  getRequestTrail,
  listRequests,
  type RequestFilters,
} from "@/features/rights/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  AuditEntry,
  HolderThread,
  MyTicket,
  Page,
  RightsRequestDetail,
  RightsRequestRow,
  TicketDetail,
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

/* --------------------------------------------------- the respondent's side */

export function useMyTickets() {
  return useQuery<MyTicket[], ApiError>({
    queryKey: keys.tickets.mine,
    queryFn: listMyTickets,
    // Unread counts and dates change while the page is open.
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

/**
 * A thread is a conversation, and the other side may be writing while it is
 * open: it refreshes itself while on screen, so a reply appears without a
 * reload. Reading it marks it read.
 */
const THREAD_REFRESH_MS = 20_000;

/** Enabled only while the thread is open on screen. */
export function useHolderThread(uuid: Uuid, holderUuid: Uuid | undefined) {
  return useQuery<HolderThread, ApiError>({
    queryKey: keys.rights.thread(uuid, holderUuid ?? ""),
    queryFn: () => holderThread(uuid, holderUuid!),
    enabled: Boolean(holderUuid),
    staleTime: 0,
    refetchInterval: THREAD_REFRESH_MS,
    refetchOnWindowFocus: true,
  });
}

export function useMyTicket(holderUuid: Uuid | undefined) {
  return useQuery<TicketDetail, ApiError>({
    queryKey: keys.tickets.detail(holderUuid ?? ""),
    queryFn: () => myTicket(holderUuid!),
    enabled: Boolean(holderUuid),
    staleTime: 0,
    refetchInterval: THREAD_REFRESH_MS,
    refetchOnWindowFocus: true,
  });
}
