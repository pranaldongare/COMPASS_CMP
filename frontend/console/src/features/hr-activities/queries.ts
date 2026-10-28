/** Reading HR activities (ADR 0033). */
"use client";

import { useQuery } from "@tanstack/react-query";

import { activityOptions, getHrActivity, listHrActivities } from "@/features/hr-activities/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type { ActivityOptionCategory, HrActivity, HrActivityDetail, Uuid } from "@/types";

export function useHrActivities(filters: { status?: string; category?: Uuid; q?: string } = {}) {
  return useQuery<HrActivity[], ApiError>({
    queryKey: keys.hrActivity.list(filters),
    queryFn: () => listHrActivities(filters),
  });
}

export function useHrActivity(uuid: Uuid | undefined) {
  return useQuery<HrActivityDetail, ApiError>({
    queryKey: keys.hrActivity.detail(uuid ?? ""),
    queryFn: () => getHrActivity(uuid!),
    enabled: Boolean(uuid),
  });
}

/** What the wizard can make an activity from; only for the HR PoC. */
export function useActivityOptions(enabled = true) {
  return useQuery<ActivityOptionCategory[], ApiError>({
    queryKey: keys.hrActivity.options,
    queryFn: activityOptions,
    enabled,
  });
}
