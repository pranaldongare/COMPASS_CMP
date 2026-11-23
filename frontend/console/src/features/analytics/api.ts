/**
 * Analytics, audit and health reports, and reports made as files (ADR 0045).
 *
 * The catalogue says what the signed-in role may see; the figures are counted
 * from the record when asked; a report is made in the background (202) and
 * read back from the list until it is ready, then downloaded through the
 * one download helper so its headers are read the same way as every other
 * file the console hands out.
 */

import {
  apiDelete,
  apiDownload,
  BACKGROUND,
  apiGet,
  apiPatch,
  apiPost,
  apiPut,
  queryString,
} from "@/lib/api";
import type {
  Acknowledged,
  AnalyticsSettings,
  AuditReport,
  Catalogue,
  Figures,
  FiguresParams,
  Inventory,
  PeriodParams,
  Report,
  ReportInput,
  ReportSchedule,
  ScheduleInput,
  TargetInput,
  Uuid,
} from "@/types";

export function getCatalogue(): Promise<Catalogue> {
  return apiGet<Catalogue>("/analytics/catalogue");
}

export function getFigures(params: FiguresParams): Promise<Figures> {
  const { keys, ...rest } = params;
  const qs = queryString(rest);
  // `keys` repeats, which `queryString` does not do.
  const extra = (keys ?? []).map((k) => `keys=${encodeURIComponent(k)}`).join("&");
  const joined = extra ? `${qs ? `${qs}&` : "?"}${extra}` : qs;
  return apiGet<Figures>(`/analytics/figures${joined}`);
}

export function getInventory(office?: string): Promise<Inventory> {
  return apiGet<Inventory>(`/analytics/inventory${queryString({ office })}`);
}

export function getAuditReport(
  key: string,
  params: PeriodParams & { cursor?: string; limit?: number },
): Promise<AuditReport> {
  return apiGet<AuditReport>(
    `/analytics/audit-reports/${encodeURIComponent(key)}${queryString({ ...params })}`,
  );
}

export function getAnalyticsSettings(): Promise<AnalyticsSettings> {
  return apiGet<AnalyticsSettings>("/analytics/settings");
}

export function setTarget(key: string, input: TargetInput): Promise<AnalyticsSettings> {
  return apiPut<AnalyticsSettings>(`/analytics/targets/${encodeURIComponent(key)}`, input);
}

/** Back to the catalogue's default target and amber line. */
export function resetTarget(key: string): Promise<AnalyticsSettings> {
  return apiDelete<AnalyticsSettings>(`/analytics/targets/${encodeURIComponent(key)}`);
}

export function setThreshold(small_number_threshold: number): Promise<AnalyticsSettings> {
  return apiPut<AnalyticsSettings>("/analytics/settings/threshold", {
    small_number_threshold,
  });
}

/** `background`: a re-poll nobody asked for, which must not keep an idle
 *  session alive (the API's `X-CMP-Background`). */
export function listReports(background = false): Promise<Report[]> {
  return apiGet<Report[]>("/reports", background ? BACKGROUND : undefined);
}

export function getReport(uuid: Uuid): Promise<Report> {
  return apiGet<Report>(`/reports/${uuid}`);
}

/** Asks for a report: it is queued (202) and made in the background. */
export function createReport(input: ReportInput): Promise<Report> {
  return apiPost<Report>("/reports", input);
}

export function deleteReport(uuid: Uuid): Promise<Acknowledged> {
  return apiDelete<Acknowledged>(`/reports/${uuid}`);
}

export function downloadReport(uuid: Uuid) {
  return apiDownload(`/reports/${uuid}/file`);
}

export function listSchedules(): Promise<ReportSchedule[]> {
  return apiGet<ReportSchedule[]>("/reports/schedules");
}

export function createSchedule(input: ScheduleInput): Promise<ReportSchedule> {
  return apiPost<ReportSchedule>("/reports/schedules", input);
}

export function setScheduleActive(uuid: Uuid, active: boolean): Promise<ReportSchedule> {
  return apiPatch<ReportSchedule>(`/reports/schedules/${uuid}`, { active });
}

export function deleteSchedule(uuid: Uuid): Promise<Acknowledged> {
  return apiDelete<Acknowledged>(`/reports/schedules/${uuid}`);
}
