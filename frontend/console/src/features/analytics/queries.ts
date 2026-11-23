/**
 * Reading the catalogue, the figures, the reports and the settings.
 */
"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getAnalyticsSettings,
  getAuditReport,
  getCatalogue,
  getFigures,
  getInventory,
  listReports,
  listSchedules,
} from "@/features/analytics/api";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";
import type {
  AnalyticsSettings,
  AuditReport,
  Catalogue,
  Figures,
  FiguresParams,
  Inventory,
  PeriodParams,
  Report,
  ReportSchedule,
} from "@/types";

/** What this role may see. It changes only with a release, so it is kept. */
export function useCatalogue() {
  return useQuery<Catalogue, ApiError>({
    queryKey: keys.analytics.catalogue,
    queryFn: getCatalogue,
    staleTime: 10 * 60_000,
  });
}

/** One section's figures. The previous answer stays on screen while a new
 *  period or breakdown is counted, so the tiles do not blink empty. */
export function useFigures(params: FiguresParams, enabled = true) {
  return useQuery<Figures, ApiError>({
    queryKey: keys.analytics.figures({ ...params }),
    queryFn: () => getFigures(params),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export function useInventory(office: string | undefined, enabled = true) {
  return useQuery<Inventory, ApiError>({
    queryKey: keys.analytics.inventory({ office }),
    queryFn: () => getInventory(office),
    enabled,
  });
}

export function useAuditReport(
  key: string,
  params: PeriodParams & { cursor?: string; limit?: number },
  enabled = true,
) {
  return useQuery<AuditReport, ApiError>({
    queryKey: keys.analytics.audit(key, { ...params }),
    queryFn: () => getAuditReport(key, params),
    enabled: enabled && Boolean(key),
    placeholderData: keepPreviousData,
  });
}

export function useAnalyticsSettings(enabled = true) {
  return useQuery<AnalyticsSettings, ApiError>({
    queryKey: keys.analytics.settings,
    queryFn: getAnalyticsSettings,
    enabled,
  });
}

/** While a report is being made, look again every few seconds; otherwise
 *  now and then, for the ones a schedule makes. */
export function useReports(enabled = true) {
  return useQuery<Report[], ApiError>({
    queryKey: keys.analytics.reports,
    // The first load is somebody looking; every look after it is the poll.
    queryFn: ({ client }) =>
      listReports(client.getQueryData(keys.analytics.reports) !== undefined),
    enabled,
    refetchInterval: (q) =>
      q.state.data?.some((r) => r.status === "queued") ? 3_000 : 60_000,
  });
}

export function useSchedules(enabled = true) {
  return useQuery<ReportSchedule[], ApiError>({
    queryKey: keys.analytics.schedules,
    queryFn: listSchedules,
    enabled,
  });
}
