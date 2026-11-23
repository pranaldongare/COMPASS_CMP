/**
 * The Analytics page's one row of filters: the period (with the first and
 * last day when "Custom dates"), the office for management, the comparison
 * with the period before, and the breakdown the visible figures allow.
 *
 * Every choice lives in the address, so a link opens the page as it was.
 */
"use client";

import * as React from "react";

import {
  FilterBar,
  FilterDate,
  FilterSelect,
  FilterToggle,
  useFilterParam,
} from "@/components/data-display/resource-list";
import { OFFICES } from "@/features/analytics/format";
import type { Catalogue, PeriodParams } from "@/types";

export interface AnalyticsFilters {
  period: string;
  start: string;
  end: string;
  office: string;
  dim: string;
  compare: boolean;
}

export const DEFAULT_PERIOD = "this_month";

export function useAnalyticsFilters(): [
  AnalyticsFilters,
  {
    setPeriod: (v: string) => void;
    setStart: (v: string) => void;
    setEnd: (v: string) => void;
    setOffice: (v: string) => void;
    setDim: (v: string) => void;
    setCompare: (v: boolean) => void;
  },
] {
  const [period, setPeriod] = useFilterParam("period", DEFAULT_PERIOD);
  const [start, setStart] = useFilterParam("start");
  const [end, setEnd] = useFilterParam("end");
  const [office, setOffice] = useFilterParam("office");
  const [dim, setDim] = useFilterParam("dim");
  const [compareParam, setCompareParam] = useFilterParam("compare", "on");
  return [
    { period, start, end, office, dim, compare: compareParam !== "off" },
    {
      setPeriod,
      setStart,
      setEnd,
      setOffice,
      setDim,
      setCompare: (on) => setCompareParam(on ? "on" : "off"),
    },
  ];
}

/** The period as the API takes it; null while custom dates are incomplete
 *  or the wrong way round, so nothing is asked for until they make sense. */
export function periodParams(
  f: Pick<AnalyticsFilters, "period" | "start" | "end">,
): PeriodParams | null {
  if (f.period !== "custom") return { period: f.period };
  if (!f.start || !f.end || f.end < f.start) return null;
  return { period: "custom", start: f.start, end: f.end };
}

export function AnalyticsToolbar({
  catalogue,
  filters,
  set,
  dims,
  showCompare,
  showPeriod = true,
  showOffice = true,
}: {
  catalogue: Catalogue;
  filters: AnalyticsFilters;
  set: ReturnType<typeof useAnalyticsFilters>[1];
  /** The breakdowns the figures on show allow; none hides the choice. */
  dims: string[];
  showCompare: boolean;
  showPeriod?: boolean;
  /** Management's office choice, where the tab's figures can take one. */
  showOffice?: boolean;
}) {
  const periods = catalogue.periods.map((p) => ({ value: p.key, label: p.label }));
  const dimOptions = catalogue.dimensions
    .filter((d) => dims.includes(d.key))
    .map((d) => ({ value: d.key, label: d.label }));
  const backwards =
    filters.period === "custom" &&
    filters.start &&
    filters.end &&
    filters.end < filters.start;

  return (
    <>
      <FilterBar>
        {showPeriod && (
          <FilterSelect
            label="Period"
            value={filters.period}
            onChange={(v) => set.setPeriod(v || DEFAULT_PERIOD)}
            options={periods}
            allLabel={null}
          />
        )}
        {showPeriod && filters.period === "custom" && (
          <>
            <FilterDate
              label="From"
              value={filters.start}
              onChange={set.setStart}
              max={filters.end || undefined}
            />
            <FilterDate
              label="To"
              value={filters.end}
              onChange={set.setEnd}
              min={filters.start || undefined}
            />
          </>
        )}
        {showOffice && catalogue.may_choose_office && (
          <FilterSelect
            label="Office"
            value={filters.office}
            onChange={set.setOffice}
            options={[...OFFICES]}
            allLabel="All offices"
          />
        )}
        {dimOptions.length > 0 && (
          <FilterSelect
            label="Breakdown"
            value={dimOptions.some((d) => d.value === filters.dim) ? filters.dim : ""}
            onChange={set.setDim}
            options={dimOptions}
            allLabel="None"
          />
        )}
        {showCompare && (
          <FilterToggle
            label="Compare with previous period"
            checked={filters.compare}
            onChange={set.setCompare}
          />
        )}
      </FilterBar>
      {showPeriod && filters.period === "custom" && (!filters.start || !filters.end) && (
        <p className="-mt-2 mb-4 text-xs text-text-muted">
          Choose the first and the last day.
        </p>
      )}
      {showPeriod && backwards && (
        <p role="alert" className="-mt-2 mb-4 text-xs text-danger-text">
          The last day is before the first.
        </p>
      )}
    </>
  );
}

/** The breakdowns a section's figures allow, in the catalogue's order. Only
 *  management reads the offices side by side. */
export function dimsFor(catalogue: Catalogue, section: string): string[] {
  const allowed = new Set(
    catalogue.metrics.filter((m) => m.section === section).flatMap((m) => m.dims),
  );
  if (!catalogue.may_choose_office) allowed.delete("office");
  return catalogue.dimensions.map((d) => d.key).filter((k) => allowed.has(k));
}

export function useDimLabel(catalogue: Catalogue): (key: string) => string {
  return React.useCallback(
    (key: string) => catalogue.dimensions.find((d) => d.key === key)?.label ?? key,
    [catalogue],
  );
}
