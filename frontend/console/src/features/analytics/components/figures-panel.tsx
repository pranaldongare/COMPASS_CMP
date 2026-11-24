/**
 * One tab of figures - the scorecard, the analytics, your work, health, data
 * quality (2026-11-24 redesign).
 *
 * Read in the order the questions come: what needs attention (the figures off
 * target, worst first), how the platform is (health), then each group with
 * the charts that explain it and its figures as tiles. Every tile and flagged
 * figure opens the figure's own page; jump links take a long tab group by
 * group.
 */
"use client";

import * as React from "react";

import { Alert, Skeleton } from "@/components/ui/primitives";
import { AttentionStrip, FigureCard } from "@/features/analytics/components/figure-card";
import { HealthBoard } from "@/features/analytics/components/health-board";
import {
  OfficeComparison,
  chartsFor,
  type ChartContext,
} from "@/features/analytics/components/section-charts";
import {
  periodParams,
  type AnalyticsFilters,
} from "@/features/analytics/components/toolbar";
import { officeLabel } from "@/features/analytics/format";
import { figureHref } from "@/features/analytics/links";
import { useFigures } from "@/features/analytics/queries";
import type { Catalogue, Figure } from "@/types";

function slug(group: string): string {
  return `group-${group.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

export function FiguresPanel({
  section,
  catalogue,
  filters,
}: {
  section: string;
  catalogue: Catalogue;
  filters: AnalyticsFilters;
  /** Kept for the toolbar's sake; a breakdown is now on a figure's page. */
  dims?: string[];
}) {
  const period = periodParams(filters);
  const office = catalogue.may_choose_office ? filters.office || undefined : undefined;
  const base = { ...(period ?? { period: "this_month" }), office };
  const query = useFigures({ section, ...base, compare: filters.compare }, period !== null);

  const groups = React.useMemo(() => {
    const order: string[] = [];
    const by = new Map<string, Figure[]>();
    for (const f of query.data?.metrics ?? []) {
      if (!by.has(f.group)) {
        order.push(f.group);
        by.set(f.group, []);
      }
      by.get(f.group)!.push(f);
    }
    return order.map((g) => ({ group: g, items: by.get(g)! }));
  }, [query.data]);

  const hrefOf = React.useCallback(
    (key: string) => figureHref(key, filters, section),
    [filters, section],
  );

  if (period === null) return null;
  if (query.isLoading) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-16" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-36" />
          <Skeleton className="h-36" />
          <Skeleton className="h-36" />
        </div>
      </div>
    );
  }
  if (query.isError) {
    return (
      <Alert tone="danger" title="Could not count these figures">
        {query.error.userMessage()}
      </Alert>
    );
  }
  const data = query.data!;
  const ctx: ChartContext = {
    base,
    data,
    bothOffices: catalogue.may_choose_office && !office,
  };

  return (
    <div className="space-y-8" aria-busy={query.isFetching || undefined}>
      <p className="text-sm text-text-muted" aria-live="polite">
        {data.period.label}
        {catalogue.may_choose_office && <> · {officeLabel(data.office)}</>}
        {data.previous && filters.compare && <> · compared with {data.previous.label}</>}
      </p>

      {section === "health" && <HealthBoard data={data} hrefOf={hrefOf} />}
      {section !== "quality" && (
        <AttentionStrip figures={data.metrics} threshold={data.threshold} hrefOf={hrefOf} />
      )}

      {groups.length > 2 && (
        <nav aria-label="Groups on this tab" className="flex flex-wrap gap-2">
          {groups.map(({ group, items }) => (
            <a
              key={group}
              href={`#${slug(group)}`}
              className="inline-flex min-h-9 items-center gap-1.5 rounded-full border border-border bg-surface px-3 text-sm text-text-muted hover:border-accent-border hover:text-accent-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              {group}
              <span className="tabular text-xs text-text-subtle">{items.length}</span>
            </a>
          ))}
        </nav>
      )}

      {groups.length === 0 && (
        <p className="text-sm text-text-muted">
          There are no figures in this section for your role.
        </p>
      )}

      {section === "management" && ctx.bothOffices && (
        <div className="grid gap-4 lg:grid-cols-2">
          <OfficeComparison ctx={ctx} />
        </div>
      )}

      {groups.map(({ group, items }) => {
        const charts = chartsFor(section, group);
        return (
          <section
            key={group}
            id={slug(group)}
            aria-labelledby={`${slug(group)}-h`}
            className="scroll-mt-24 space-y-4"
          >
            <h2
              id={`${slug(group)}-h`}
              className="text-sm font-semibold tracking-wide text-text-muted uppercase"
            >
              {group}
            </h2>
            {charts.length > 0 && (
              <div className="grid [grid-template-columns:repeat(auto-fit,minmax(min(100%,26rem),1fr))] gap-4">
                {charts.map((Chart, i) => (
                  <Chart key={i} ctx={ctx} />
                ))}
              </div>
            )}
            <div className="grid [grid-template-columns:repeat(auto-fill,minmax(min(100%,15rem),1fr))] gap-4">
              {items.map((f) => (
                <FigureCard
                  key={f.key}
                  figure={f}
                  threshold={data.threshold}
                  previousLabel={data.previous?.label ?? null}
                  grain={data.grain}
                  compare={filters.compare}
                  href={hrefOf(f.key)}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
