/**
 * Asking for reports, scheduling them, and the administrator's targets and
 * threshold.
 *
 * A target or the threshold changes what every figure says, so both
 * invalidate every figure as well as the settings. A report is queued; the
 * list is invalidated and then polled until it is made.
 */
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createReport,
  createSchedule,
  deleteReport,
  deleteSchedule,
  resetTarget,
  setScheduleActive,
  setTarget,
  setThreshold,
} from "@/features/analytics/api";
import { keys, type Result } from "@/lib/query";
import type {
  Acknowledged,
  AnalyticsSettings,
  Report,
  ReportInput,
  ReportSchedule,
  ScheduleInput,
  TargetInput,
  Uuid,
} from "@/types";

function useSettled(): (fresh: AnalyticsSettings) => void {
  const qc = useQueryClient();
  return (fresh) => {
    qc.setQueryData(keys.analytics.settings, fresh);
    void qc.invalidateQueries({ queryKey: keys.analytics.all });
  };
}

export function useSetTarget(): Result<
  AnalyticsSettings,
  { key: string; input: TargetInput }
> {
  const settled = useSettled();
  return useMutation({
    mutationFn: ({ key, input }: { key: string; input: TargetInput }) =>
      setTarget(key, input),
    onSuccess: settled,
  });
}

export function useResetTarget(): Result<AnalyticsSettings, string> {
  const settled = useSettled();
  return useMutation({ mutationFn: (key: string) => resetTarget(key), onSuccess: settled });
}

export function useSetThreshold(): Result<AnalyticsSettings, number> {
  const settled = useSettled();
  return useMutation({ mutationFn: (n: number) => setThreshold(n), onSuccess: settled });
}

export function useCreateReport(): Result<Report, ReportInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ReportInput) => createReport(input),
    onSuccess: (made) => {
      qc.setQueryData<Report[]>(keys.analytics.reports, (old) =>
        old ? [made, ...old.filter((r) => r.report_uuid !== made.report_uuid)] : old,
      );
      void qc.invalidateQueries({ queryKey: keys.analytics.reports, exact: true });
    },
  });
}

export function useDeleteReport(): Result<Acknowledged, Uuid> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (uuid: Uuid) => deleteReport(uuid),
    onSuccess: () =>
      void qc.invalidateQueries({ queryKey: keys.analytics.reports, exact: true }),
  });
}

export function useCreateSchedule(): Result<ReportSchedule, ScheduleInput> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ScheduleInput) => createSchedule(input),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.analytics.schedules }),
  });
}

export function useSetScheduleActive(): Result<
  ReportSchedule,
  { uuid: Uuid; active: boolean }
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ uuid, active }: { uuid: Uuid; active: boolean }) =>
      setScheduleActive(uuid, active),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.analytics.schedules }),
  });
}

export function useDeleteSchedule(): Result<Acknowledged, Uuid> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (uuid: Uuid) => deleteSchedule(uuid),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.analytics.schedules }),
  });
}
