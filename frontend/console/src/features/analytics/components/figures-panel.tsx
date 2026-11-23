/**
 * One section's figures - the scorecard, the analytics, your work, health,
 * data quality - grouped under their headings in the catalogue's order.
 */
"use client";

import * as React from "react";

import { Alert, Skeleton } from "@/components/ui/primitives";
import { FigureTile } from "@/features/analytics/components/figure-tile";
import {
  periodParams,
  type AnalyticsFilters,
} from "@/features/analytics/components/toolbar";
import { officeLabel } from "@/features/analytics/format";
import { useFigures } from "@/features/analytics/queries";
import type { Catalogue, Figure } from "@/types";

export function FiguresPanel({
  section,
  catalogue,
  filters,
  dims,
}: {
  section: string;
  catalogue: Catalogue;
  filters: AnalyticsFilters;
  /** The breakdowns this section allows: a stale `dim` from another tab is
   *  not sent. */
  dims: string[];
}) {
  const period = periodParams(filters);
  const dim = dims.includes(filters.dim) ? filters.dim : undefined;
  const office = catalogue.may_choose_office ? filters.office || undefined : undefined;
  const query = useFigures(
    {
      section,
      ...(period ?? { period: "this_month" }),
      office,
      dim,
      compare: filters.compare,
    },
    period !== null,
  );

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

  if (period === null) return null;
  if (query.isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
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
  const dimLabel = dim
    ? (catalogue.dimensions.find((d) => d.key === dim)?.label ?? dim)
    : null;

  return (
    <div className="space-y-8" aria-busy={query.isFetching || undefined}>
      <p className="text-sm text-text-muted" aria-live="polite">
        {data.period.label}
        {catalogue.may_choose_office && <> · {officeLabel(data.office)}</>}
        {data.previous && filters.compare && <> · compared with {data.previous.label}</>}
      </p>
      {groups.length === 0 && (
        <p className="text-sm text-text-muted">
          There are no figures in this section for your role.
        </p>
      )}
      {groups.map(({ group, items }) => (
        <section key={group} aria-label={group}>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-text-muted uppercase">
            {group}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((f) => (
              <FigureTile
                key={f.key}
                figure={f}
                threshold={data.threshold}
                previousLabel={data.previous?.label ?? null}
                grain={data.grain}
                dimLabel={dim && f.dims.includes(dim) ? dimLabel : null}
                compare={filters.compare}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
