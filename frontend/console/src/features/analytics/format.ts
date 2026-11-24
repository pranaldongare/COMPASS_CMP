/**
 * How a figure reads: its unit, its comparison, its status, and - when it is
 * withheld - "< N", never nought.
 */

import { statusLabel } from "@/components/ui/status";
import { isApiError } from "@/lib/errors";

const NUMBER = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });

/** A value in its unit: 1,284 / 92.5% / 4.5 days / 1 hour. */
export function formatValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return "—";
  const n = NUMBER.format(value);
  switch (unit) {
    case "percent":
      return `${n}%`;
    case "days":
      return `${n} ${value === 1 ? "day" : "days"}`;
    case "hours":
      return `${n} ${value === 1 ? "hour" : "hours"}`;
    default:
      return n;
  }
}

/** A change, signed: +12 / −2.5 points / +1 day. A percentage moves in
 *  points - 80% to 90% is ten points, not 12.5 per cent. */
export function formatChange(change: number, unit: string): string {
  const sign = change > 0 ? "+" : change < 0 ? "−" : "±";
  const size = Math.abs(change);
  const n = NUMBER.format(size);
  switch (unit) {
    case "percent":
      return `${sign}${n} ${size === 1 ? "point" : "points"}`;
    case "days":
      return `${sign}${n} ${size === 1 ? "day" : "days"}`;
    case "hours":
      return `${sign}${n} ${size === 1 ? "hour" : "hours"}`;
    default:
      return `${sign}${n}`;
  }
}

/** Whether a change is good news, bad news or neither. */
export function changeTone(
  change: number | null,
  higherIsBetter: boolean,
): "good" | "bad" | "flat" {
  if (change === null || change === 0) return "flat";
  return change > 0 === higherIsBetter ? "good" : "bad";
}

/** What "withheld" means, said the same way everywhere. */
export function withheldText(threshold: number): string {
  return `Fewer than ${threshold} people. A count this small is withheld so nobody can be picked out of it.`;
}

/** A figure as shown: its value in its unit, or "< N" when withheld. */
export function shownValue(
  value: number | null,
  suppressed: boolean,
  unit: string,
  threshold: number,
): string {
  if (suppressed) return `< ${threshold}`;
  return formatValue(value, unit);
}

export const RAG: Record<
  string,
  { label: string; tone: "success" | "warning" | "danger" }
> = {
  green: { label: "On target", tone: "success" },
  amber: { label: "Watch", tone: "warning" },
  red: { label: "Off target", tone: "danger" },
};

/** The target as a sentence fragment: "at least 90%", "at most 3 days". */
export function targetText(target: number, unit: string, higherIsBetter: boolean): string {
  return `${higherIsBetter ? "at least" : "at most"} ${formatValue(target, unit)}`;
}

export const OFFICES = [
  { value: "rnd", label: "R&D (DPO office)" },
  { value: "hr", label: "HR (Legal office)" },
] as const;

export function officeLabel(office: string | null | undefined): string {
  if (!office) return "All offices";
  return OFFICES.find((o) => o.value === office)?.label ?? office;
}

export const FORMAT_LABEL: Record<string, string> = {
  pdf: "PDF",
  xlsx: "Excel (.xlsx)",
  csv: "CSV",
};

/** A role by its title, as the rest of the console names it. */
export function roleTitle(role: string | null | undefined): string {
  if (!role) return "System";
  if (role === "system") return "System";
  return statusLabel("role", role);
}

/** "2026-11-01" as a short date for an axis or a table. */
export function bucketLabel(bucket: string | null, grain: string | null): string {
  if (!bucket) return "—";
  const d = new Date(`${bucket.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return bucket;
  if (grain === "month")
    return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

/** The server's words for a failure, or a plain fallback. */
export function errorText(err: unknown, fallback: string): string {
  return isApiError(err) ? err.userMessage() : fallback;
}

/**
 * A value judged against a figure's target and amber line, as the server
 * judges the figure itself (`service.status`): for a part of a breakdown, a
 * point of a line. Null without a target, or without a value.
 */
export function statusOf(
  f: { target: number | null; amber: number | null; higher_is_better: boolean },
  value: number | null,
): "green" | "amber" | "red" | null {
  if (value === null || f.target === null) return null;
  const line = f.amber ?? f.target;
  if (f.higher_is_better)
    return value >= f.target ? "green" : value >= line ? "amber" : "red";
  return value <= f.target ? "green" : value <= line ? "amber" : "red";
}
