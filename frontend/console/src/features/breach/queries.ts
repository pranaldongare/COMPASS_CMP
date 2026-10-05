/**
 * Reading the breach register.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { getBreach, listBreaches, myBreachTicket, myBreachTickets } from "@/features/breach/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  Breach,
  BreachStatus,
  BreachSummary,
  MyBreachTicket,
  MyBreachTicketDetail,
  Uuid,
} from "@/types";

export function useBreaches(status?: BreachStatus) {
  return useQuery<BreachSummary[], ApiError>({
    queryKey: keys.breach.list({ status }),
    queryFn: () => listBreaches(status),
    // Every clock on the page moves; a minute is fine-grained enough to read.
    refetchInterval: 60_000,
  });
}

export function useBreach(uuid: Uuid | undefined) {
  return useQuery<Breach, ApiError>({
    queryKey: keys.breach.detail(uuid ?? ""),
    queryFn: () => getBreach(uuid!),
    enabled: Boolean(uuid),
    refetchInterval: 60_000,
  });
}

/** Breach tickets addressed to me (S3-08). Every member of staff may hold one. */
export function useMyBreachTickets() {
  return useQuery<MyBreachTicket[], ApiError>({
    queryKey: keys.breach.mine(),
    queryFn: myBreachTickets,
    refetchInterval: 60_000,
  });
}

export function useMyBreachTicket(ticketUuid: Uuid | undefined) {
  return useQuery<MyBreachTicketDetail, ApiError>({
    queryKey: keys.breach.myTicket(ticketUuid ?? ""),
    queryFn: () => myBreachTicket(ticketUuid!),
    enabled: Boolean(ticketUuid),
  });
}
