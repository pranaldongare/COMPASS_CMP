/**
 * Reading the breach register.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { getBreach, listBreaches } from "@/features/breach/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { Breach, BreachStatus, BreachSummary, Uuid } from "@/types";

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
