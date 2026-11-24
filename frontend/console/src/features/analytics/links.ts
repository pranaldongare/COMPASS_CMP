/**
 * Where a figure leads: its own page, with the filters it was read under, and
 * the register whose records it counts.
 */
import type { AnalyticsFilters } from "@/features/analytics/components/toolbar";
import type { NavKey } from "@/lib/permissions";

/** A figure's page, carrying the period, office and comparison, and the tab
 *  it was opened from so "Back" returns there. */
export function figureHref(
  key: string,
  filters: Pick<AnalyticsFilters, "period" | "start" | "end" | "office" | "compare">,
  from: string,
): string {
  const q = new URLSearchParams();
  if (filters.period) q.set("period", filters.period);
  if (filters.period === "custom") {
    if (filters.start) q.set("start", filters.start);
    if (filters.end) q.set("end", filters.end);
  }
  if (filters.office) q.set("office", filters.office);
  if (!filters.compare) q.set("compare", "off");
  q.set("from", from);
  return `/analytics/figure/${encodeURIComponent(key)}?${q.toString()}`;
}

/** The overview a figure's page returns to, with the same filters. */
export function overviewHref(params: URLSearchParams): string {
  const q = new URLSearchParams();
  for (const k of ["period", "start", "end", "office", "compare"]) {
    const v = params.get(k);
    if (v) q.set(k, v);
  }
  const tab = params.get("from");
  if (tab) q.set("tab", tab);
  const s = q.toString();
  return s ? `/analytics?${s}` : "/analytics";
}

const REGISTER: Array<[prefix: string, nav: NavKey, label: string]> = [
  ["rights.", "requests", "Rights requests"],
  ["erasure.", "requests", "Rights requests"],
  ["holders.", "requests", "Rights requests"],
  ["breach.", "breaches", "Breaches"],
  ["delivery.", "breaches", "Breaches"],
  ["consent.", "consents", "Consents"],
  ["funnel.links_opened", "links", "Consent links"],
  ["funnel.", "consents", "Consents"],
  ["projects.", "projects", "Projects"],
  ["hr.", "hr-activities", "HR activities"],
  ["mine.projects", "projects", "Projects"],
  ["mine.links", "links", "Consent links"],
  ["mine.sites", "sites", "Collection sites"],
  ["mine.tickets", "tickets", "My tasks"],
  ["mine.", "consents", "Consents"],
  ["quality.processors", "processors", "Processors"],
  ["health.", "audit", "Audit trail"],
];

/** The register behind a figure - the page holding the records it counts -
 *  or null. Offered only to a role the server gave that page. */
export function registerFor(key: string): { nav: NavKey; label: string } | null {
  const hit = REGISTER.find(([prefix]) => key.startsWith(prefix));
  return hit ? { nav: hit[1], label: hit[2] } : null;
}
