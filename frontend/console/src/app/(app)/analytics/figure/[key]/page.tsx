/**
 * One figure, in full (2026-11-24): what a tile opens.
 *
 * Its value against the period before and its target; its line, by day, week
 * or month, with the target and the amber band behind it; its breakdowns, one
 * at a time; exactly what it counts; and the numbers behind the line as a
 * table to read or download. The period and office it was opened with are in
 * the address, so the page can be shared as it is, and "Back" returns to the
 * tab it came from.
 *
 * Only the catalogue's figures, for the roles the catalogue gives them to:
 * the server refuses any other, and the page says so.
 */
"use client";

import { ArrowLeft, Download, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { sectionsFor } from "@/components/layout/nav";
import { Alert, Button, Skeleton } from "@/components/ui/primitives";
import { BreakdownBars } from "@/features/analytics/components/charts";
import { RagBadge } from "@/features/analytics/components/figure-tile";
import { MakeReport } from "@/features/analytics/components/make-report";
import {
  AnalyticsToolbar,
  periodParams,
  useAnalyticsFilters,
} from "@/features/analytics/components/toolbar";
import {
  ChartCard,
  LineChart,
  MeterList,
  Segmented,
} from "@/features/analytics/components/viz";
import {
  bucketLabel,
  changeTone,
  formatChange,
  formatValue,
  officeLabel,
  shownValue,
  statusOf,
  targetText,
  withheldText,
} from "@/features/analytics/format";
import { overviewHref, registerFor } from "@/features/analytics/links";
import { useCatalogue, useFigures } from "@/features/analytics/queries";
import { canSee } from "@/lib/permissions";
import { cn } from "@/lib/format";
import { useAuth } from "@/providers";
import type { Catalogue, Figure, MetricInfo } from "@/types";

/** The report a tab makes, for "Make a report" here. */
const REPORT_OF: Record<string, string> = {
  management: "management_scorecard",
  analytics: "analytics_summary",
  mine: "my_analytics",
  health: "health",
  quality: "data_quality",
};

export default function FigurePage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-96" />}>
      <FigurePageView />
    </React.Suspense>
  );
}

function FigurePageView() {
  const { key } = useParams<{ key: string }>();
  const metricKey = decodeURIComponent(key);
  const catalogue = useCatalogue();
  const info = catalogue.data?.metrics.find((m) => m.key === metricKey);

  if (catalogue.isLoading) return <Skeleton className="h-96" />;
  if (catalogue.isError) {
    return (
      <Alert tone="danger" title="Could not open Analytics">
        {catalogue.error.userMessage()}
      </Alert>
    );
  }
  if (!info) {
    return (
      <>
        <PageHeader title="Figure" />
        <Alert tone="info" title="This figure is not one your role reads">
          <Link href="/analytics" className="underline">
            Back to Analytics
          </Link>
        </Alert>
      </>
    );
  }
  return <FigureDetail catalogue={catalogue.data!} info={info} />;
}

function FigureDetail({ catalogue, info }: { catalogue: Catalogue; info: MetricInfo }) {
  const { me } = useAuth();
  const search = useSearchParams();
  const [filters, set] = useAnalyticsFilters();
  const period = periodParams(filters);
  const office = catalogue.may_choose_office ? filters.office || undefined : undefined;
  const base = { ...(period ?? { period: "this_month" }), office };
  const [grain, setGrain] = React.useState<string | undefined>(undefined);
  const keys = [info.key, info.numerator, info.denominator].filter((k): k is string =>
    Boolean(k),
  );

  const main = useFigures(
    { ...base, keys, compare: filters.compare, grain },
    period !== null,
  );
  const dims = info.dims.filter(
    (d) => d !== "office" || (catalogue.may_choose_office && !office),
  );
  const [dim, setDim] = React.useState(dims[0]);
  const split = useFigures(
    { ...base, keys, dim, compare: false, trend: false },
    period !== null && Boolean(dim),
  );

  const back = overviewHref(new URLSearchParams(search.toString()));
  const fig = main.data?.metrics.find((m) => m.key === info.key);
  const num = info.numerator
    ? main.data?.metrics.find((m) => m.key === info.numerator)
    : undefined;
  const den = info.denominator
    ? main.data?.metrics.find((m) => m.key === info.denominator)
    : undefined;
  const threshold = main.data?.threshold ?? 1;
  const register = registerFor(info.key);
  // The register's page as the sidebar has it - only for a role given it.
  const registerPage =
    register && canSee(me, register.nav)
      ? sectionsFor(me)
          .flatMap((sec) => sec.items)
          .find((i) => i.key === register.nav)
      : undefined;
  const reportKind = REPORT_OF[info.section];
  const canReport = (me?.writes ?? []).includes("report") && reportKind && period;

  return (
    <>
      <PageHeader
        title={info.title}
        actions={
          <>
            <Link
              href={back}
              className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-border-strong bg-surface px-3 text-sm font-medium text-text hover:bg-surface-hover"
            >
              <ArrowLeft className="size-4" aria-hidden="true" />
              Back to the overview
            </Link>
            {canReport && (
              <MakeReport
                catalogue={catalogue}
                kind={reportKind}
                params={{
                  ...(info.section === "quality" ? {} : period),
                  ...(office ? { office: office as "rnd" | "hr" } : {}),
                }}
              />
            )}
          </>
        }
      />

      <AnalyticsToolbar
        catalogue={catalogue}
        filters={filters}
        set={set}
        dims={[]}
        showCompare
      />

      {main.isLoading || !main.data ? (
        main.isError ? (
          <Alert tone="danger" title="Could not count this figure">
            {main.error.userMessage()}
          </Alert>
        ) : (
          <Skeleton className="h-72" />
        )
      ) : !fig ? null : (
        <div className="space-y-5">
          <Headline
            fig={fig}
            num={num}
            den={den}
            threshold={threshold}
            previousLabel={main.data.previous?.label ?? null}
            periodLabel={main.data.period.label}
            officeText={catalogue.may_choose_office ? officeLabel(main.data.office) : null}
            compare={filters.compare}
          />

          <div className="grid [grid-template-columns:repeat(auto-fit,minmax(min(100%,24rem),1fr))] gap-5">
            <TrendCard
              fig={fig}
              num={num}
              den={den}
              threshold={threshold}
              grain={main.data.grain}
              periodDays={periodDays(main.data.period.start, main.data.period.end)}
              onGrain={setGrain}
            />

            {dims.length > 0 && dim && (
              <BreakdownCard
                fig={split.data?.metrics.find((m) => m.key === info.key)}
                num={
                  info.numerator
                    ? split.data?.metrics.find((m) => m.key === info.numerator)
                    : undefined
                }
                den={
                  info.denominator
                    ? split.data?.metrics.find((m) => m.key === info.denominator)
                    : undefined
                }
                loading={split.isLoading}
                dims={dims}
                dim={dim}
                onDim={setDim}
                catalogue={catalogue}
                threshold={threshold}
              />
            )}

            <section className="space-y-4 rounded-xl border border-border bg-surface p-5 shadow-[var(--shadow-xs)]">
              <h3 className="font-semibold text-text">About this figure</h3>
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2.5 text-sm">
                <dt className="text-text-muted">Counts</dt>
                <dd className="text-text">{fig.definition}</dd>
                {den && (
                  <>
                    <dt className="text-text-muted">Out of</dt>
                    <dd className="text-text">{den.title}</dd>
                  </>
                )}
                {fig.target !== null && (
                  <>
                    <dt className="text-text-muted">Target</dt>
                    <dd className="text-text">
                      {targetText(fig.target, fig.unit, fig.higher_is_better)}
                      {fig.amber !== null && fig.amber !== fig.target && (
                        <>, watch to {formatValue(fig.amber, fig.unit)}</>
                      )}
                      . Set by the administrator.
                    </dd>
                  </>
                )}
                {info.people && (
                  <>
                    <dt className="text-text-muted">Small numbers</dt>
                    <dd className="text-text">{withheldText(threshold)}</dd>
                  </>
                )}
                <dt className="text-text-muted">Source</dt>
                <dd className="text-text">
                  Counted when asked, from the live record - not a copy.
                </dd>
              </dl>
              {register && registerPage && (
                <Link
                  href={registerPage.href}
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 text-sm font-semibold text-text hover:bg-surface-hover"
                >
                  Open {register.label}
                  <ExternalLink className="size-3.5" aria-hidden="true" />
                </Link>
              )}
            </section>
          </div>
        </div>
      )}
    </>
  );
}

function periodDays(start: string, end: string): number {
  return Math.max(1, Math.round((Date.parse(end) - Date.parse(start)) / 86_400_000));
}

function Headline({
  fig,
  num,
  den,
  threshold,
  previousLabel,
  periodLabel,
  officeText,
  compare,
}: {
  fig: Figure;
  num?: Figure;
  den?: Figure;
  threshold: number;
  previousLabel: string | null;
  periodLabel: string;
  officeText: string | null;
  compare: boolean;
}) {
  const tone = changeTone(fig.change, fig.higher_is_better);
  const stats: Array<[string, string]> = [];
  if (num && den) {
    stats.push([num.title, shownValue(num.value, num.suppressed, num.unit, threshold)]);
    stats.push([den.title, shownValue(den.value, den.suppressed, den.unit, threshold)]);
  }
  if (compare && fig.previous !== null) {
    stats.push([
      previousLabel ?? "Previous period",
      shownValue(fig.previous, fig.previous_suppressed, fig.unit, threshold),
    ]);
  }
  if (fig.target !== null) {
    stats.push(["Target", targetText(fig.target, fig.unit, fig.higher_is_better)]);
  }
  return (
    <div className="grid [grid-template-columns:repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-3">
      <div className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-xs)] sm:col-span-2">
        <p className="text-xs text-text-muted">
          {periodLabel}
          {officeText && <> · {officeText}</>}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <p className="tabular text-[2rem] leading-none font-bold tracking-tight text-text">
            {shownValue(fig.value, fig.suppressed, fig.unit, threshold)}
          </p>
          <RagBadge status={fig.status} />
        </div>
        {compare && fig.change !== null && (
          <p
            className={cn(
              "mt-2 text-sm font-medium",
              tone === "good" && "text-success-text",
              tone === "bad" && "text-danger-text",
              tone === "flat" && "text-text-muted",
            )}
          >
            {formatChange(fig.change, fig.unit)}{" "}
            {tone === "good" ? "better" : tone === "bad" ? "worse" : ""} than{" "}
            {previousLabel ?? "the period before"}
          </p>
        )}
        {fig.suppressed && (
          <p className="mt-2 text-xs text-text-subtle">{withheldText(threshold)}</p>
        )}
        {!fig.suppressed && fig.value === null && (
          <p className="mt-2 text-xs text-text-subtle">
            Nothing to count in this period
            {den ? `: no ${den.title.toLowerCase()} yet` : ""}.
          </p>
        )}
      </div>
      {stats.map(([k, v]) => (
        <div key={k} className="rounded-xl bg-bg-subtle p-4">
          <p className="text-xs text-text-muted">{k}</p>
          <p className="tabular mt-1 text-lg font-semibold text-text">{v}</p>
        </div>
      ))}
    </div>
  );
}

function TrendCard({
  fig,
  num,
  den,
  threshold,
  grain,
  periodDays: days,
  onGrain,
}: {
  fig: Figure;
  num?: Figure;
  den?: Figure;
  threshold: number;
  grain: string | null;
  periodDays: number;
  onGrain: (g: string) => void;
}) {
  const format = (n: number) =>
    fig.unit === "percent" ? `${n}%` : formatValue(n, "count");
  const points = fig.series.map((p) => ({
    label: bucketLabel(p.bucket, grain),
    value: p.suppressed ? null : p.value,
    text: shownValue(p.value, p.suppressed, fig.unit, threshold),
  }));
  const numAt = new Map((num?.series ?? []).map((p) => [p.bucket, p]));
  const denAt = new Map((den?.series ?? []).map((p) => [p.bucket, p]));
  const rows = fig.series.map((p, i) => {
    const prev = i > 0 ? fig.series[i - 1] : null;
    const v = p.suppressed ? null : p.value;
    const pv = prev && !prev.suppressed ? prev.value : null;
    const change = v !== null && pv !== null ? Math.round((v - pv) * 10) / 10 : null;
    const n = numAt.get(p.bucket);
    const d = denAt.get(p.bucket);
    return {
      when: bucketLabel(p.bucket, grain),
      value: shownValue(p.value, p.suppressed, fig.unit, threshold),
      num: n ? shownValue(n.value, n.suppressed, "count", threshold) : null,
      den: d ? shownValue(d.value, d.suppressed, "count", threshold) : null,
      change: change === null ? "—" : formatChange(change, fig.unit),
      status: statusOf(fig, v),
    };
  });
  const head = [
    "When",
    ...(num ? [num.title] : []),
    ...(den ? [den.title] : []),
    fig.title,
    "Change",
  ];

  function download() {
    // Every cell as text; one that would start a formula is neutralised.
    const safe = (s: string) => (/^[=+\-@]/.test(s) ? `'${s}` : s);
    const quote = (s: string) => `"${safe(s).replace(/"/g, '""')}"`;
    const body = [
      [...head, "Status"],
      ...rows.map((r) => [
        r.when,
        ...(num ? [r.num ?? ""] : []),
        ...(den ? [r.den ?? ""] : []),
        r.value,
        r.change,
        r.status ?? "",
      ]),
    ]
      .map((line) => line.map((c) => quote(String(c))).join(","))
      .join("\r\n");
    const url = URL.createObjectURL(new Blob([body], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fig.key}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <ChartCard
      title="Over the period"
      subtitle={
        fig.target !== null
          ? "The dashed line is the target; the shaded band runs from the amber line to it."
          : `By ${grain ?? "period"}`
      }
      className="lg:col-span-full"
      actions={
        <>
          {fig.kind !== "snapshot" && fig.kind !== "live" && (
            <Segmented
              label="Draw the line by"
              value={grain ?? ""}
              onChange={onGrain}
              options={[
                {
                  value: "day",
                  label: "Day",
                  disabled: days > 92,
                  title: days > 92 ? "Choose a shorter period to draw by day" : undefined,
                },
                { value: "week", label: "Week" },
                { value: "month", label: "Month" },
              ]}
            />
          )}
          {rows.length > 0 && (
            <Button variant="secondary" size="sm" onClick={download}>
              <Download className="size-4" aria-hidden="true" />
              CSV
            </Button>
          )}
        </>
      }
      table={
        rows.length > 0 ? (
          <table className="w-full text-sm">
            <caption className="sr-only">
              {fig.title}, by {grain}
            </caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                {head.map((h, i) => (
                  <th
                    key={h}
                    scope="col"
                    className={
                      i ? "px-2 py-2 text-right font-semibold" : "py-2 pr-2 font-semibold"
                    }
                  >
                    {h}
                  </th>
                ))}
                <th scope="col" className="py-2 pl-2 font-semibold">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.when} className="border-b border-border last:border-0">
                  <td className="py-2 pr-2">{r.when}</td>
                  {num && <td className="tabular px-2 py-2 text-right">{r.num ?? "—"}</td>}
                  {den && <td className="tabular px-2 py-2 text-right">{r.den ?? "—"}</td>}
                  <td className="tabular px-2 py-2 text-right font-semibold">{r.value}</td>
                  <td className="tabular px-2 py-2 text-right">{r.change}</td>
                  <td className="py-2 pl-2">
                    <RagBadge status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : undefined
      }
    >
      {fig.kind === "snapshot" || fig.kind === "live" ? (
        <p className="py-6 text-center text-sm text-text-subtle">
          This figure is how things stand now, so it has no line over the period.
        </p>
      ) : (
        <LineChart
          points={points}
          label={`${fig.title}, by ${grain ?? "period"}`}
          target={fig.target}
          amber={fig.amber}
          unit={fig.unit}
          format={format}
        />
      )}
    </ChartCard>
  );
}

function BreakdownCard({
  fig,
  num,
  den,
  loading,
  dims,
  dim,
  onDim,
  catalogue,
  threshold,
}: {
  fig?: Figure;
  num?: Figure;
  den?: Figure;
  loading: boolean;
  dims: string[];
  dim: string;
  onDim: (d: string) => void;
  catalogue: Catalogue;
  threshold: number;
}) {
  const name = (d: string) => catalogue.dimensions.find((x) => x.key === d)?.label ?? d;
  const parts = fig?.breakdown ?? [];
  const numBy = new Map((num?.breakdown ?? []).map((p) => [p.key, p]));
  const denBy = new Map((den?.breakdown ?? []).map((p) => [p.key, p]));
  const isRate = fig?.unit === "percent";
  const ordered = isRate
    ? [...parts].sort((a, b) => (a.value ?? 101) - (b.value ?? 101))
    : parts;
  return (
    <ChartCard
      title="Broken down"
      subtitle={
        isRate ? "Furthest from the target first · the line is the target" : "Largest first"
      }
      actions={
        dims.length > 1 ? (
          <Segmented
            label="Break down by"
            value={dim}
            onChange={onDim}
            options={dims.map((d) => ({ value: d, label: name(d) }))}
          />
        ) : undefined
      }
      table={
        <table className="w-full text-sm">
          <caption className="sr-only">By {name(dim).toLowerCase()}</caption>
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th scope="col" className="py-2 pr-2 font-semibold">
                {name(dim)}
              </th>
              <th scope="col" className="px-2 py-2 text-right font-semibold">
                {fig?.title}
              </th>
              {num && den && (
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  Of
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {ordered.map((p) => (
              <tr key={p.key ?? p.label} className="border-b border-border last:border-0">
                <td className="py-2 pr-2">{p.label}</td>
                <td className="tabular px-2 py-2 text-right">
                  {shownValue(p.value, p.suppressed, fig?.unit ?? "count", threshold)}
                </td>
                {num && den && (
                  <td className="tabular px-2 py-2 text-right">
                    {xOfY(numBy.get(p.key), denBy.get(p.key), threshold) ?? "—"}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      }
    >
      {loading || !fig ? (
        <div className="h-40 animate-pulse rounded-lg bg-bg-inset" aria-busy="true" />
      ) : isRate ? (
        <MeterList
          label={`${fig.title} by ${name(dim).toLowerCase()}`}
          target={fig.target}
          rows={ordered.map((p) => ({
            key: p.key ?? p.label,
            label: p.label,
            value: p.suppressed ? null : p.value,
            text: shownValue(p.value, p.suppressed, "percent", threshold),
            detail: xOfY(numBy.get(p.key), denBy.get(p.key), threshold) ?? undefined,
            badge: <RagBadge status={statusOf(fig, p.suppressed ? null : p.value)} />,
          }))}
        />
      ) : (
        <BreakdownBars
          label={`${fig.title} by ${name(dim).toLowerCase()}`}
          withheldNote={withheldText(threshold)}
          items={ordered.map((p) => ({
            key: p.key ?? p.label,
            label: p.label,
            value: p.suppressed ? null : p.value,
            text: shownValue(p.value, p.suppressed, fig.unit, threshold),
            withheld: p.suppressed,
          }))}
        />
      )}
    </ChartCard>
  );
}

function xOfY(
  n: { value: number | null; suppressed: boolean } | undefined,
  d: { value: number | null; suppressed: boolean } | undefined,
  threshold: number,
): string | null {
  if (!n || !d) return null;
  return `${shownValue(n.value, n.suppressed, "count", threshold)} of ${shownValue(d.value, d.suppressed, "count", threshold)}`;
}
