/** Writing HR activities (ADR 0033). An activity is a project: its views and
 *  every project view refresh with it. */
"use client";

import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";

import * as api from "@/features/hr-activities/api";
import { keys, prefixes, type Result } from "@/lib/query";
import type { HrActivityCreated, Uuid } from "@/types";

function settle(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: ["hr-activities"] });
  void qc.invalidateQueries({ queryKey: ["hr-activity"] });
  void qc.invalidateQueries({ queryKey: prefixes.anyProject });
  void qc.invalidateQueries({ queryKey: keys.consent.allLinks() });
}

export function useCreateHrActivity(): Result<HrActivityCreated, api.ActivityInput> {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.createHrActivity, onSuccess: () => settle(qc) });
}

export function useUpgradeHrActivity(
  uuid: Uuid,
): Result<Awaited<ReturnType<typeof api.upgradeHrActivity>>, api.UpgradeInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.upgradeHrActivity(uuid, body),
    onSuccess: () => settle(qc),
  });
}

export function useCloseHrActivity(
  uuid: Uuid,
): Result<Awaited<ReturnType<typeof api.closeHrActivity>>, string | null> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason) => api.closeHrActivity(uuid, reason),
    onSuccess: () => settle(qc),
  });
}
