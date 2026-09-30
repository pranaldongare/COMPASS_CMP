/**
 * Reading her breach notices.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { listMyBreachNotices } from "@/features/breach-notices/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { MyBreachNotice } from "@/types";

export function useMyBreachNotices() {
  return useQuery<MyBreachNotice[], ApiError>({
    queryKey: keys.breachNotices.all,
    queryFn: listMyBreachNotices,
  });
}
