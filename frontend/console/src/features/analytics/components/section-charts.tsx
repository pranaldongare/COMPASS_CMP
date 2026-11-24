/**
 * The charts each Analytics tab leads its groups with (2026-11-24 redesign).
 *
 * Every chart is drawn from the same figures endpoint as the tiles: a line of
 * a figure is its series, a split is the figure asked for again with a
 * breakdown (`dim`). A chart whose figures the role may not read is not
 * drawn - the server's refusal is the rule, not a list kept here - and every
 * chart has its Table view.
 */
"use client";

import * as React from "react";

import { RagBadge } from "@/features/analytics/components/figure-tile";
import { BreakdownBars } from "@/features/analytics/components/charts";
import {
  CAT,
  ChartCard,
  Donut,
  Funnel,
  Legend,
  MeterList,
  SegmentBar,
  Segmented,
  StackedColumns,
  type Part,
} from "@/features/analytics/components/viz";
import {
  bucketLabel,
  formatValue,
  shownValue,
  statusOf,
} from "@/features/analytics/format";
import { useFigures } from "@/features/analytics/queries";
import type { Figure, Figures, FiguresParams } from "@/types";

/** What every chart of a tab shares: the period, the office, and the
 *  tab's own figures (for lines drawn from their series). */
export interface ChartContext {
  base: FiguresParams;
  data: Figures;
  /** Management choosing both offices: the office split is offered. */
  bothOffices: boolean;
}

function byKey(data: Figures | undefined, key: string): Figure | undefined {
  return data?.metrics.find((m) => m.key === key);
}

/** A figure asked for again, split one way. Not asked when the role cannot
 *  read the first key - the tab's own figures say which it has. */
function useSplit(
  ctx: ChartContext,
  keys: string[],
  dim: string | undefined,
  enabled = true,
) {
  return useFigures(
    { ...ctx.base, keys, dim, compare: false, trend: false, section: undefined },
    enabled,
  );
}

function Table({
  head,
  rows,
  caption,
}: {
  head: string[];
  rows: (string | number)[][];
  caption: string;
}) {
  return (
    <table className="w-full text-sm">
      <caption className="sr-only">{caption}</caption>
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
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-border last:border-0">
            {r.map((c, j) => (
              <td key={j} className={j ? "tabular px-2 py-2 text-right" : "py-2 pr-2"}>
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Up to five parts, the rest folded into "Other". */
function toParts(
  fig: Figure | undefined,
  threshold: number,
  colors: readonly string[] = CAT,
): Part[] {
  const items = fig?.breakdown ?? [];
  const head = items.slice(0, items.length > 5 ? 4 : 5);
  const rest = items.slice(head.length);
  const parts: Part[] = head.map((p, i) => ({
    key: p.key ?? p.label,
    label: p.label,
    value: p.suppressed ? null : p.value,
    color: colors[i % colors.length],
    text: shownValue(p.value, p.suppressed, fig?.unit ?? "count", threshold),
  }));
  if (rest.length) {
    const v = rest.reduce((s, p) => s + (p.suppressed ? 0 : (p.value ?? 0)), 0);
    parts.push({
      key: "_other",
      label: "Other",
      value: v,
      color: "var(--viz-neutral)",
      text: formatValue(v, "count"),
    });
  }
  return parts;
}

/* ============================================================== management */

export function RightsByMonth({ ctx }: { ctx: ChartContext }) {
  const closed = byKey(ctx.data, "rights.closed");
  const onTime = byKey(ctx.data, "rights.closed_on_time");
  if (!closed || !onTime || closed.series.length < 2) return null;
  const late = new Map(onTime.series.map((p) => [p.bucket, p]));
  const buckets = closed.series.map((p) => {
    const t = late.get(p.bucket);
    const all = p.suppressed ? null : p.value;
    const ok = t && !t.suppressed ? t.value : null;
    return {
      label: bucketLabel(p.bucket, ctx.data.grain),
      values: [ok, all !== null && ok !== null ? Math.max(0, all - ok) : null],
    };
  });
  const series = [
    { label: "Closed on time", color: CAT[0] },
    { label: "Closed late", color: CAT[1] },
  ];
  return (
    <ChartCard
      title="Rights requests closed"
      subtitle={`On time and late, by ${ctx.data.grain ?? "period"} closed`}
      table={
        <Table
          caption="Rights requests closed, on time and late"
          head={["When", "On time", "Late", "All"]}
          rows={buckets.map((b) => [
            b.label,
            b.values[0] ?? "withheld",
            b.values[1] ?? "withheld",
            (b.values[0] ?? 0) + (b.values[1] ?? 0),
          ])}
        />
      }
    >
      <Legend items={series} />
      <StackedColumns
        buckets={buckets}
        series={series}
        label="Rights requests closed, on time and late"
      />
    </ChartCard>
  );
}

export function RequestMix({ ctx }: { ctx: ChartContext }) {
  const dims = ["type", "channel", ...(ctx.bothOffices ? ["office"] : [])];
  const [dim, setDim] = React.useState("type");
  const q = useSplit(
    ctx,
    ["rights.received"],
    dim,
    Boolean(byKey(ctx.data, "rights.received")),
  );
  if (!byKey(ctx.data, "rights.received") || q.isError) return null;
  const fig = byKey(q.data, "rights.received");
  const parts = toParts(fig, ctx.data.threshold);
  const names: Record<string, string> = {
    type: "Type",
    channel: "Channel",
    office: "Office",
  };
  return (
    <ChartCard
      title="What people asked for"
      subtitle={`Requests received, by ${names[dim].toLowerCase()}`}
      actions={
        <Segmented
          label="Split requests by"
          value={dim}
          onChange={setDim}
          options={dims.map((d) => ({ value: d, label: names[d] }))}
        />
      }
      table={
        <Table
          caption={`Requests received by ${names[dim].toLowerCase()}`}
          head={[names[dim], "Requests"]}
          rows={parts.map((p) => [p.label, p.text])}
        />
      }
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <Donut parts={parts} totalLabel="requests" label="Requests received" />
      )}
    </ChartCard>
  );
}

export function DutyMeters({ ctx }: { ctx: ChartContext }) {
  const has = Boolean(byKey(ctx.data, "breach.duty_on_time_rate"));
  const q = useSplit(
    ctx,
    ["breach.duty_on_time_rate", "breach.duties_on_time", "breach.duties_completed"],
    "duty",
    has,
  );
  if (!has || q.isError) return null;
  const rate = byKey(q.data, "breach.duty_on_time_rate");
  const done = new Map(
    (byKey(q.data, "breach.duties_completed")?.breakdown ?? []).map((p) => [p.key, p]),
  );
  const ok = new Map(
    (byKey(q.data, "breach.duties_on_time")?.breakdown ?? []).map((p) => [p.key, p]),
  );
  const rows = (rate?.breakdown ?? []).map((p) => {
    const d = done.get(p.key);
    const o = ok.get(p.key);
    const value = p.suppressed ? null : p.value;
    return {
      key: p.key ?? p.label,
      label: p.label,
      value,
      text: shownValue(p.value, p.suppressed, "percent", ctx.data.threshold),
      detail:
        d && o && !d.suppressed && !o.suppressed ? `${o.value} of ${d.value}` : undefined,
      badge: rate ? <RagBadge status={statusOf(rate, value)} /> : null,
    };
  });
  return (
    <ChartCard
      title="Breach duties met on time"
      subtitle="Each duty's share done inside its deadline · the line is the target"
      table={
        <Table
          caption="Breach duties met on time"
          head={["Duty", "On time", "Of"]}
          rows={rows.map((r) => [r.label, r.text, r.detail ?? "—"])}
        />
      }
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <MeterList rows={rows} target={rate?.target} label="Breach duties met on time" />
      )}
    </ChartCard>
  );
}

export function ConsentFunnel({ ctx }: { ctx: ChartContext }) {
  const keys = [
    "funnel.links_opened",
    "funnel.notices_served",
    "consent.given",
    "consent.withdrawn",
  ];
  const q = useSplit(ctx, keys, undefined);
  if (q.isError) return null;
  const v = (k: string) => {
    const f = byKey(q.data, k);
    return f && !f.suppressed ? f.value : null;
  };
  // A step can outnumber the one before - a notice read from the portal was
  // never a link opened - and a share over 100% would claim the impossible.
  const share = (a: number | null, b: number | null) =>
    a !== null && b && a <= b ? `${Math.round((a / b) * 100)}%` : null;
  const [opened, shown, given, withdrawn] = keys.map(v);
  const t = (k: string) => {
    const f = byKey(q.data, k);
    return shownValue(
      f?.value ?? null,
      f?.suppressed ?? false,
      "count",
      ctx.data.threshold,
    );
  };
  const steps = [
    { label: "Consent links opened", value: opened, text: t(keys[0]) },
    {
      label: "Notices shown",
      value: shown,
      text: t(keys[1]),
      between: share(shown, opened)
        ? `${share(shown, opened)} of those who opened a link saw the notice`
        : "More notices shown than links opened: some were read on the portal directly",
    },
    {
      label: "Consents given",
      value: given,
      text: t(keys[2]),
      between: share(given, shown)
        ? `${share(given, shown)} gave consent, in full or in part`
        : undefined,
    },
    {
      label: "Withdrawals",
      value: withdrawn,
      text: t(keys[3]),
      between: share(withdrawn, given)
        ? `${share(withdrawn, given)} later withdrew`
        : undefined,
    },
  ];
  return (
    <ChartCard
      title="From link to consent"
      subtitle="Each step, and the share carried from the step before"
      table={
        <Table
          caption="From link to consent"
          head={["Step", "People"]}
          rows={steps.map((s) => [s.label, s.text])}
        />
      }
    >
      {q.isLoading ? <Loading /> : <Funnel steps={steps} label="From link to consent" />}
    </ChartCard>
  );
}

export function ConsentOutcomes({ ctx }: { ctx: ChartContext }) {
  const q = useSplit(
    ctx,
    ["consent.given", "consent.partial", "funnel.declined", "consent.withdrawn"],
    undefined,
  );
  if (q.isError) return null;
  const f = (k: string) => byKey(q.data, k);
  const val = (k: string) => (f(k) && !f(k)!.suppressed ? f(k)!.value : null);
  const given = val("consent.given");
  const partial = val("consent.partial");
  const full = given !== null && partial !== null ? Math.max(0, given - partial) : given;
  const th = ctx.data.threshold;
  const parts: Part[] = [
    {
      key: "full",
      label: "Given in full",
      value: full,
      color: "var(--viz-1)",
      text: formatValue(full, "count"),
    },
    {
      key: "partial",
      label: "Given in part",
      value: partial,
      color: "var(--viz-2)",
      text: shownValue(partial, f("consent.partial")?.suppressed ?? false, "count", th),
    },
    {
      key: "declined",
      label: "Declined",
      value: val("funnel.declined"),
      color: "var(--viz-neutral)",
      text: shownValue(
        val("funnel.declined"),
        f("funnel.declined")?.suppressed ?? false,
        "count",
        th,
      ),
    },
    {
      key: "withdrawn",
      label: "Withdrawn",
      value: val("consent.withdrawn"),
      color: "var(--viz-3)",
      text: shownValue(
        val("consent.withdrawn"),
        f("consent.withdrawn")?.suppressed ?? false,
        "count",
        th,
      ),
    },
  ];
  return (
    <ChartCard
      title="How people answered the notice"
      subtitle="Decisions in the period. Declining is a person's choice, so it is grey, not red."
      table={
        <Table
          caption="How people answered"
          head={["Answer", "People"]}
          rows={parts.map((p) => [p.label, p.text])}
        />
      }
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <SegmentBar parts={parts} tall label="How people answered the notice" />
      )}
    </ChartCard>
  );
}

/** A count split one way, as ranked bars: projects by status, holders. */
export function RankedSplit({
  ctx,
  metric,
  dim,
  title,
  subtitle,
}: {
  ctx: ChartContext;
  metric: string;
  dim: string;
  title: string;
  subtitle: string;
}) {
  const has = Boolean(byKey(ctx.data, metric));
  const q = useSplit(ctx, [metric], dim, has);
  if (!has || q.isError) return null;
  const fig = byKey(q.data, metric);
  const items = (fig?.breakdown ?? []).map((p) => ({
    key: p.key ?? p.label,
    label: p.label,
    value: p.suppressed ? null : p.value,
    text: shownValue(p.value, p.suppressed, fig?.unit ?? "count", ctx.data.threshold),
    withheld: p.suppressed,
  }));
  return (
    <ChartCard
      title={title}
      subtitle={subtitle}
      table={
        <Table
          caption={title}
          head={["", fig?.title ?? title]}
          rows={items.map((i) => [i.label, i.text])}
        />
      }
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <BreakdownBars
          items={items}
          max={fig?.unit === "percent" ? 100 : undefined}
          label={title}
        />
      )}
    </ChartCard>
  );
}

/** Management, both offices chosen: the figures with a target, side by side. */
export function OfficeComparison({ ctx }: { ctx: ChartContext }) {
  const q = useFigures(
    { ...ctx.base, section: "management", dim: "office", compare: false, trend: false },
    ctx.bothOffices,
  );
  if (!ctx.bothOffices || q.isError) return null;
  // The rates and times with something to compare: a row of two dashes says
  // nothing.
  const rows = (q.data?.metrics ?? [])
    .filter((m) => m.target !== null || m.unit !== "count")
    .filter((m) =>
      m.breakdown.some(
        (b) => (b.key === "rnd" || b.key === "hr") && (b.suppressed || b.value !== null),
      ),
    )
    .slice(0, 8);
  if (!q.isLoading && rows.length === 0) return null;
  const cell = (m: Figure, office: string) => {
    const p = m.breakdown.find((b) => b.key === office);
    return p ? shownValue(p.value, p.suppressed, m.unit, ctx.data.threshold) : "—";
  };
  const width = (m: Figure, office: string) => {
    const p = m.breakdown.find((b) => b.key === office);
    const top =
      m.unit === "percent" ? 100 : Math.max(1, ...m.breakdown.map((b) => b.value ?? 0));
    return p && !p.suppressed && p.value !== null ? Math.max(2, (p.value / top) * 100) : 0;
  };
  return (
    <ChartCard
      title="Office by office"
      subtitle="The rates and times, each office alone"
      className="lg:col-span-2"
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Figures by office</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Figure
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  R&amp;D office
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  HR office
                </th>
                <th scope="col" className="w-40 py-2 pl-3 font-semibold">
                  <span className="sr-only">Comparison</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => (
                <tr key={m.key} className="border-b border-border last:border-0">
                  <td className="py-2.5 pr-3">{m.title}</td>
                  <td className="tabular px-2 py-2.5 text-right">{cell(m, "rnd")}</td>
                  <td className="tabular px-2 py-2.5 text-right">{cell(m, "hr")}</td>
                  <td className="py-2.5 pl-3" aria-hidden="true">
                    <span
                      className="block h-1.5 rounded-full bg-[var(--cat-1)]"
                      style={{ width: `${width(m, "rnd")}%` }}
                    />
                    <span
                      className="mt-1 block h-1.5 rounded-full bg-[var(--cat-2)]"
                      style={{ width: `${width(m, "hr")}%` }}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Legend
            className="mt-3"
            items={[
              { label: "R&D office", color: "var(--cat-1)" },
              { label: "HR office", color: "var(--cat-2)" },
            ]}
          />
        </div>
      )}
    </ChartCard>
  );
}

/* ================================================================ health */

export function SignInFailures({ ctx }: { ctx: ChartContext }) {
  const fig = byKey(ctx.data, "health.sign_in_failures");
  if (!fig || fig.series.length < 2) return null;
  const buckets = fig.series.map((p) => ({
    label: bucketLabel(p.bucket, ctx.data.grain),
    values: [p.suppressed ? null : p.value],
  }));
  return (
    <ChartCard
      title="Failed sign-ins"
      subtitle={`Wrong passwords and codes, by ${ctx.data.grain ?? "period"}`}
      table={
        <Table
          caption="Failed sign-ins"
          head={["When", "Failures"]}
          rows={buckets.map((b) => [b.label, b.values[0] ?? "withheld"])}
        />
      }
    >
      <StackedColumns
        buckets={buckets}
        series={[{ label: "Failed sign-ins", color: CAT[0] }]}
        label="Failed sign-ins"
      />
    </ChartCard>
  );
}

export function CodeSuccessByFlow({ ctx }: { ctx: ChartContext }) {
  const has = Boolean(byKey(ctx.data, "health.otp_success_rate"));
  const q = useSplit(ctx, ["health.otp_success_rate"], "flow", has);
  if (!has || q.isError) return null;
  const rate = byKey(q.data, "health.otp_success_rate");
  const rows = (rate?.breakdown ?? []).map((p) => ({
    key: p.key ?? p.label,
    label: p.label,
    value: p.suppressed ? null : p.value,
    text: shownValue(p.value, p.suppressed, "percent", ctx.data.threshold),
    badge: rate ? (
      <RagBadge status={statusOf(rate, p.suppressed ? null : p.value)} />
    ) : null,
  }));
  return (
    <ChartCard
      title="Codes entered correctly"
      subtitle="Share of one-time codes sent that were then entered, by flow"
      table={
        <Table
          caption="Codes entered correctly"
          head={["Flow", "Success"]}
          rows={rows.map((r) => [r.label, r.text])}
        />
      }
    >
      {q.isLoading ? (
        <Loading />
      ) : (
        <MeterList rows={rows} target={rate?.target} label="Codes entered correctly" />
      )}
    </ChartCard>
  );
}

/* ================================================================== mine */

export function MyProjects({ ctx }: { ctx: ChartContext }) {
  const keys = ["mine.consents_given", "mine.consents_withdrawn", "mine.links_opened"];
  const has = Boolean(byKey(ctx.data, keys[0]));
  const q = useSplit(ctx, keys, "project", has);
  if (!has || q.isError) return null;
  const split = (k: string) =>
    new Map((byKey(q.data, k)?.breakdown ?? []).map((p) => [p.label, p]));
  const [given, withdrawn, opened] = keys.map(split);
  const names = [...new Set([...given.keys(), ...opened.keys()])];
  const th = ctx.data.threshold;
  const rows = names.map((n) => {
    const g = given.get(n);
    const o = opened.get(n);
    const w = withdrawn.get(n);
    const rate =
      g && o && !g.suppressed && !o.suppressed && o.value
        ? Math.round(((g.value ?? 0) / o.value) * 100)
        : null;
    return {
      name: n,
      given: g ? shownValue(g.value, g.suppressed, "count", th) : "0",
      withdrawn: w ? shownValue(w.value, w.suppressed, "count", th) : "0",
      opened: o ? shownValue(o.value, o.suppressed, "count", th) : "0",
      rate,
    };
  });
  return (
    <ChartCard
      title="Your projects"
      subtitle="Consents, withdrawals and links opened, project by project"
      className="lg:col-span-2"
    >
      {q.isLoading ? (
        <Loading />
      ) : rows.length === 0 ? (
        <p className="py-4 text-sm text-text-subtle">
          Nothing on your projects in this period.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Your projects</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th scope="col" className="py-2 pr-3 font-semibold">
                  Project
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  Links opened
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  Consents
                </th>
                <th scope="col" className="px-2 py-2 text-right font-semibold">
                  Withdrawals
                </th>
                <th scope="col" className="w-48 py-2 pl-3 font-semibold">
                  Opened → consented
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-b border-border last:border-0">
                  <td className="py-2.5 pr-3 font-medium">{r.name}</td>
                  <td className="tabular px-2 py-2.5 text-right">{r.opened}</td>
                  <td className="tabular px-2 py-2.5 text-right">{r.given}</td>
                  <td className="tabular px-2 py-2.5 text-right">{r.withdrawn}</td>
                  <td className="py-2.5 pl-3">
                    {r.rate === null ? (
                      <span className="text-xs text-text-subtle">—</span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2 flex-1 rounded-full bg-[var(--viz-track)]"
                          aria-hidden="true"
                        >
                          <span
                            className="block h-full rounded-full bg-[var(--viz-2)]"
                            style={{ width: `${Math.min(100, r.rate)}%` }}
                          />
                        </span>
                        <span className="tabular w-10 text-right text-xs font-semibold">
                          {r.rate}%
                        </span>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}

function Loading() {
  return <div className="h-40 animate-pulse rounded-lg bg-bg-inset" aria-busy="true" />;
}

/** The charts that lead each group of a tab, in order. */
export function chartsFor(
  section: string,
  group: string,
): Array<React.ComponentType<{ ctx: ChartContext }>> {
  const k = `${section}/${group}`;
  switch (k) {
    case "management/Rights requests":
      return [RightsByMonth, RequestMix];
    case "management/Breaches":
      return [DutyMeters];
    case "management/Consent":
      return [ConsentFunnel, ConsentOutcomes];
    case "management/Projects":
      return [ProjectsByStatus];
    case "management/Third parties":
      return [HoldersOverdue];
    case "analytics/Notice delivery":
      return [DeliveryByChannel];
    case "analytics/HR track":
      return [HrByCategory];
    case "health/Sign-in and codes":
      return [SignInFailures, CodeSuccessByFlow];
    case "health/Pipelines":
      return [QueueDepth];
    case "mine/Your work":
      return [MyProjects];
    default:
      return [];
  }
}

function ProjectsByStatus({ ctx }: { ctx: ChartContext }) {
  return (
    <RankedSplit
      ctx={ctx}
      metric="projects.active"
      dim="status"
      title="Projects by status"
      subtitle="Every project, where it stands now"
    />
  );
}
function HoldersOverdue({ ctx }: { ctx: ChartContext }) {
  return (
    <RankedSplit
      ctx={ctx}
      metric="holders.overdue"
      dim="holder"
      title="Holder tickets overdue"
      subtitle="By the holder that has them, most first"
    />
  );
}
function DeliveryByChannel({ ctx }: { ctx: ChartContext }) {
  return (
    <RankedSplit
      ctx={ctx}
      metric="delivery.notice_rate"
      dim="channel"
      title="Breach notices delivered"
      subtitle="Share delivered, by channel"
    />
  );
}
function HrByCategory({ ctx }: { ctx: ChartContext }) {
  return (
    <RankedSplit
      ctx={ctx}
      metric="hr.consents"
      dim="category"
      title="HR consents by category"
      subtitle="Consents given, most first"
    />
  );
}
function QueueDepth({ ctx }: { ctx: ChartContext }) {
  return (
    <RankedSplit
      ctx={ctx}
      metric="health.queue_depth"
      dim="queue"
      title="Work waiting in each queue"
      subtitle="Now, as the workers see it"
    />
  );
}
