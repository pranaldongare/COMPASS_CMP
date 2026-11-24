/**
 * The Analytics page's charts (2026-11-24 redesign), hand-drawn in SVG and
 * HTML like the console's others.
 *
 * Each form is the one the data's job asks for (the dataviz method):
 *  - change over time in two or three parts - **stacked columns**;
 *  - one figure's course against its target - a **line** with the target and
 *    the amber band behind it;
 *  - a whole in up to five parts, read at a glance - a **donut** with the
 *    total in its middle and every part listed beside it, or a **segmented
 *    bar** where the parts sit beside their figures;
 *  - several rates, each against its own target - a **meter list**;
 *  - a sequence that narrows - **funnel steps**, each as a share of the one
 *    before.
 *
 * Colour follows the entity (`--cat-1…5`, fixed order, never cycled), text
 * wears text tokens, and every chart sits in a `ChartCard` whose Table view
 * holds the same numbers. A withheld value is a gap and "< N", never nought.
 */
"use client";

import * as React from "react";

import { cn } from "@/lib/format";

/** The categorical series, in order. */
export const CAT = [
  "var(--cat-1)",
  "var(--cat-2)",
  "var(--cat-3)",
  "var(--cat-4)",
  "var(--cat-5)",
] as const;

/* =============================================================== chart card */

/**
 * A chart's frame: its title and one line on what it shows, a Chart / Table
 * switch, the chart, and the same numbers as a table for anyone who would
 * rather read them - or cannot see the shape.
 */
export function ChartCard({
  title,
  subtitle,
  actions,
  table,
  footnote,
  children,
  className,
}: {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  /** The chart's numbers; omitted, the switch is not offered. */
  table?: React.ReactNode;
  footnote?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  const id = React.useId();
  const [view, setView] = React.useState<"chart" | "table">("chart");
  return (
    <section
      aria-labelledby={`${id}-t`}
      className={cn(
        "flex min-w-0 flex-col gap-4 rounded-xl border border-border bg-surface p-5 shadow-[var(--shadow-xs)]",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 id={`${id}-t`} className="font-semibold text-text">
            {title}
          </h3>
          {subtitle && <p className="mt-0.5 text-sm text-text-muted">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions}
          {table && (
            <Segmented
              label={`${title}: show as`}
              value={view}
              onChange={(v) => setView(v as "chart" | "table")}
              options={[
                { value: "chart", label: "Chart" },
                { value: "table", label: "Table" },
              ]}
            />
          )}
        </div>
      </div>
      {view === "chart" || !table ? (
        children
      ) : (
        <div className="overflow-x-auto">{table}</div>
      )}
      {footnote && <p className="text-xs text-text-subtle">{footnote}</p>}
    </section>
  );
}

/** A small set of mutually exclusive choices, as pressed buttons. */
export function Segmented({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string; disabled?: boolean; title?: string }[];
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex rounded-lg bg-bg-inset p-0.5"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          disabled={o.disabled}
          title={o.title}
          onClick={() => onChange(o.value)}
          className={cn(
            "min-h-8 rounded-md px-2.5 text-xs font-medium transition-colors",
            "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
            "disabled:cursor-not-allowed disabled:opacity-40",
            value === o.value
              ? "bg-surface text-text shadow-[var(--shadow-xs)]"
              : "text-text-muted hover:text-text",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* =================================================================== legend */

export interface LegendItem {
  label: string;
  color: string;
  /** Shown after the name: "130", "41%". */
  text?: string;
}

export function Legend({ items, className }: { items: LegendItem[]; className?: string }) {
  return (
    <ul className={cn("flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-muted", className)}>
      {items.map((i) => (
        <li key={i.label} className="inline-flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-[3px]"
            style={{ background: i.color }}
            aria-hidden="true"
          />
          {i.label}
          {i.text && <span className="tabular font-semibold text-text">{i.text}</span>}
        </li>
      ))}
    </ul>
  );
}

/* ================================================================= helpers */

/** Round, readable gridlines from nought to past the top. */
export function niceTicks(max: number, count = 4): number[] {
  if (!(max > 0)) return [0, 1];
  const raw = max / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const top = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= top + step / 2; v += step) ticks.push(Number(v.toFixed(6)));
  return ticks;
}

const COMPACT = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

/* ========================================================= stacked columns */

export interface ColumnBucket {
  label: string;
  /** One value per series, in series order; null is withheld or unknown. */
  values: (number | null)[];
}

/**
 * Columns over time, each split into its parts and stacked from one
 * baseline. A 2px surface gap between parts; the total at each column's top;
 * a column's numbers on hover or with the arrow keys.
 */
export function StackedColumns({
  buckets,
  series,
  label,
  format = (n) => COMPACT.format(n),
}: {
  buckets: ColumnBucket[];
  series: { label: string; color: string }[];
  /** What the chart is, for a screen reader. */
  label: string;
  format?: (n: number) => string;
}) {
  const [at, setAt] = React.useState<number | null>(null);
  if (buckets.length === 0) return <Empty />;
  const totals = buckets.map((b) => b.values.reduce<number>((s, v) => s + (v ?? 0), 0));
  const ticks = niceTicks(Math.max(...totals));
  const top = ticks[ticks.length - 1] || 1;
  const W = 640;
  const H = 220;
  const L = 36;
  const B = 24;
  const T = 18;
  const plotH = H - B - T;
  const slot = (W - L) / buckets.length;
  const bw = Math.min(56, slot * 0.62);
  const y = (v: number) => T + plotH - (v / top) * plotH;
  const every = Math.ceil(buckets.length / 12);

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block h-auto w-full touch-none outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
        role="img"
        aria-label={`${label}. ${buckets
          .map(
            (b, i) =>
              `${b.label}: ${series.map((s, j) => `${s.label} ${b.values[j] ?? "withheld"}`).join(", ")}; ${totals[i]} in all`,
          )
          .join(". ")}`}
        tabIndex={0}
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const xv = ((e.clientX - r.left) / r.width) * W - L;
          setAt(Math.max(0, Math.min(buckets.length - 1, Math.floor(xv / slot))));
        }}
        onPointerLeave={() => setAt(null)}
        onBlur={() => setAt(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const d = e.key === "ArrowRight" ? 1 : -1;
            setAt((c) =>
              Math.max(0, Math.min(buckets.length - 1, (c ?? buckets.length - 1) + d)),
            );
          } else if (e.key === "Escape") setAt(null);
        }}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={L}
              x2={W}
              y1={y(t)}
              y2={y(t)}
              stroke={t === 0 ? "var(--border-strong)" : "var(--viz-grid)"}
              strokeWidth="1"
            />
            <text
              x={L - 6}
              y={y(t) + 3.5}
              textAnchor="end"
              className="fill-text-subtle text-[10px]"
            >
              {format(t)}
            </text>
          </g>
        ))}
        {at !== null && (
          <rect
            x={L + at * slot + 2}
            y={T - 6}
            width={slot - 4}
            height={plotH + 6}
            rx="6"
            fill="var(--accent)"
            fillOpacity="0.07"
          />
        )}
        {buckets.map((b, i) => {
          const cx = L + i * slot + slot / 2;
          let base = 0;
          return (
            <g key={b.label + i}>
              {b.values.map((v, j) => {
                if (!v || v <= 0) return null;
                const y0 = y(base);
                const y1 = y(base + v);
                base += v;
                const h = Math.max(1, y0 - y1 - (j > 0 ? 2 : 0));
                return (
                  <rect
                    key={j}
                    x={cx - bw / 2}
                    y={y1}
                    width={bw}
                    height={h}
                    rx="2"
                    fill={series[j].color}
                  />
                );
              })}
              {totals[i] > 0 && (
                <text
                  x={cx}
                  y={y(totals[i]) - 5}
                  textAnchor="middle"
                  className="fill-text text-[10px] font-semibold"
                >
                  {format(totals[i])}
                </text>
              )}
              {i % every === 0 && (
                <text
                  x={cx}
                  y={H - 6}
                  textAnchor="middle"
                  className="fill-text-subtle text-[10px]"
                >
                  {b.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {at !== null && (
        <div
          role="status"
          className="pointer-events-none absolute top-0 z-10 w-48 rounded-lg bg-text p-2.5 text-xs text-text-inverse shadow-[var(--shadow-raised)]"
          style={{
            left: `${Math.min(70, Math.max(0, ((L + at * slot + slot / 2) / W) * 100 - 25))}%`,
          }}
        >
          <p className="mb-1 font-semibold">
            {buckets[at].label} · {format(totals[at])} in all
          </p>
          {series.map((s, j) => (
            <p key={s.label} className="flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-1.5">
                <span
                  className="size-2 rounded-[2px]"
                  style={{ background: s.color }}
                  aria-hidden="true"
                />
                {s.label}
              </span>
              <span className="tabular">
                {buckets[at].values[j] === null
                  ? "withheld"
                  : format(buckets[at].values[j] ?? 0)}
              </span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/* ==================================================================== donut */

export interface Part {
  key: string;
  label: string;
  value: number | null;
  color: string;
  /** "130", or "< 5" when withheld. */
  text: string;
}

/**
 * A whole in up to five parts: the ring with the total in its middle, every
 * part named with its count and share beside it. Parts past five fold into
 * "Other" before they get here.
 */
export function Donut({
  parts,
  totalLabel,
  label,
  onPick,
}: {
  parts: Part[];
  /** Under the total: "requests". */
  totalLabel: string;
  label: string;
  /** A part chosen from the list beside the ring. */
  onPick?: (key: string) => void;
}) {
  const total = parts.reduce((s, p) => s + (p.value ?? 0), 0);
  if (total <= 0) return <Empty />;
  const R = 62;
  const C = 2 * Math.PI * R;
  const gap = parts.filter((p) => (p.value ?? 0) > 0).length > 1 ? 2 : 0;
  // Where each part starts along the ring, worked out before drawing.
  const starts = parts.reduce<number[]>(
    (acc, p, i) => [
      ...acc,
      i === 0 ? 0 : acc[i - 1] + ((parts[i - 1].value ?? 0) / total) * C,
    ],
    [],
  );
  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg
        viewBox="0 0 160 160"
        className="size-40 flex-none"
        role="img"
        aria-label={`${label}: ${parts.map((p) => `${p.label} ${p.text}`).join(", ")}; ${total} in all`}
      >
        <circle
          cx="80"
          cy="80"
          r={R}
          fill="none"
          stroke="var(--viz-track)"
          strokeWidth="20"
        />
        {parts.map((p, i) => {
          const v = p.value ?? 0;
          if (v <= 0) return null;
          const len = (v / total) * C;
          const dash = Math.max(0.5, len - gap);
          return (
            <circle
              key={p.key}
              cx="80"
              cy="80"
              r={R}
              fill="none"
              stroke={p.color}
              strokeWidth="20"
              strokeDasharray={`${dash} ${C - dash}`}
              strokeDashoffset={-starts[i]}
              transform="rotate(-90 80 80)"
            />
          );
        })}
        <text x="80" y="78" textAnchor="middle" className="fill-text text-[22px] font-bold">
          {COMPACT.format(total)}
        </text>
        <text x="80" y="96" textAnchor="middle" className="fill-text-muted text-[11px]">
          {totalLabel}
        </text>
      </svg>
      <ul className="min-w-48 flex-1 space-y-0.5 text-sm">
        {parts.map((p) => {
          const share =
            p.value !== null && total > 0 ? Math.round((p.value / total) * 100) : null;
          const body = (
            <>
              <span className="inline-flex min-w-0 items-center gap-2">
                <span
                  className="size-2.5 flex-none rounded-[3px]"
                  style={{ background: p.color }}
                  aria-hidden="true"
                />
                <span className="truncate">{p.label}</span>
              </span>
              <span className="tabular whitespace-nowrap">
                <span className="font-semibold text-text">{p.text}</span>
                {share !== null && <span className="ml-1.5 text-text-muted">{share}%</span>}
              </span>
            </>
          );
          return (
            <li key={p.key}>
              {onPick ? (
                <button
                  type="button"
                  onClick={() => onPick(p.key)}
                  className="flex min-h-9 w-full items-center justify-between gap-3 rounded-md px-2 text-left hover:bg-bg-subtle focus-visible:outline-2 focus-visible:outline-focus"
                >
                  {body}
                </button>
              ) : (
                <div className="flex min-h-9 items-center justify-between gap-3 px-2">
                  {body}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ============================================================ segmented bar */

/**
 * One whole as a bar of parts. Tall, the share is printed on each part that
 * has room and a legend names them; thin, it sits beside figures that already
 * say the numbers.
 */
export function SegmentBar({
  parts,
  label,
  tall = false,
}: {
  parts: Part[];
  label: string;
  tall?: boolean;
}) {
  const total = parts.reduce((s, p) => s + (p.value ?? 0), 0);
  if (total <= 0) return <Empty />;
  return (
    <div className="space-y-2">
      <div
        className={cn("flex gap-0.5 overflow-hidden rounded-md", tall ? "h-7" : "h-3")}
        role="img"
        aria-label={`${label}: ${parts.map((p) => `${p.label} ${p.text}`).join(", ")}`}
      >
        {parts.map((p) => {
          const v = p.value ?? 0;
          if (v <= 0) return null;
          const share = Math.round((v / total) * 100);
          return (
            <span
              key={p.key}
              className="flex items-center justify-center text-[11px] font-semibold text-white"
              style={{ flex: v, background: p.color }}
            >
              {tall && share >= 8 ? `${share}%` : null}
            </span>
          );
        })}
      </div>
      <Legend
        items={parts.map((p) => ({
          label: p.label,
          color: p.color,
          text: p.text,
        }))}
      />
    </div>
  );
}

/* =============================================================== meter list */

export interface MeterRow {
  key: string;
  label: string;
  /** 0-100; null withheld or nothing to divide by. */
  value: number | null;
  /** "92%", "< 5". */
  text: string;
  /** Beside the value: "10 of 12". */
  detail?: string;
  /** A status badge, already built. */
  badge?: React.ReactNode;
}

/**
 * Several rates, one per row, each against the target line. The bar runs
 * nought to 100 so every row reads on the same scale.
 */
export function MeterList({
  rows,
  target,
  label,
}: {
  rows: MeterRow[];
  /** The target line, on the same 0-100 scale. */
  target?: number | null;
  label: string;
}) {
  if (rows.length === 0) return <Empty />;
  return (
    <ul className="space-y-3.5" aria-label={label}>
      {rows.map((r) => (
        <li key={r.key} className="space-y-1.5">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
            <span className="font-medium text-text">{r.label}</span>
            <span className="inline-flex items-center gap-2">
              <span className="tabular font-semibold text-text">{r.text}</span>
              {r.detail && <span className="text-xs text-text-muted">{r.detail}</span>}
              {r.badge}
            </span>
          </div>
          <div
            className="relative h-2 rounded-full bg-[var(--viz-track)]"
            aria-hidden="true"
          >
            {r.value !== null && (
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-[var(--viz-2)]"
                style={{ width: `${Math.max(1, Math.min(100, r.value))}%` }}
              />
            )}
            {r.value === null && (
              <span className="absolute inset-0 rounded-full bg-[repeating-linear-gradient(135deg,var(--viz-track)_0_5px,var(--bg-subtle)_5px_10px)]" />
            )}
            {target !== null && target !== undefined && (
              <span
                className="absolute -inset-y-1 w-0.5 rounded bg-text"
                style={{ left: `${Math.min(100, target)}%` }}
              />
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

/* ==================================================================== funnel */

export interface FunnelStep {
  label: string;
  value: number | null;
  text: string;
  /** Said between this step and the one before: "91% saw the notice". */
  between?: string;
}

/** A sequence that narrows: each step a bar against the first, and the share
 *  carried from the step before said in words between them. */
export function Funnel({ steps, label }: { steps: FunnelStep[]; label: string }) {
  const first = steps[0]?.value ?? 0;
  if (!first) return <Empty />;
  return (
    <ol className="space-y-1" aria-label={label}>
      {steps.map((s, i) => (
        <li key={s.label}>
          {i > 0 && s.between && (
            <p className="py-1 pl-2 text-xs text-text-muted">
              <span aria-hidden="true">↓ </span>
              {s.between}
            </p>
          )}
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="font-medium text-text">{s.label}</span>
            <span className="tabular font-semibold text-text">{s.text}</span>
          </div>
          <div className="mt-1 h-5 rounded bg-[var(--viz-track)]" aria-hidden="true">
            {s.value !== null && s.value > 0 && (
              <div
                className="h-full rounded bg-[var(--viz-2)]"
                style={{
                  width: `${Math.max(0.8, Math.min(100, (s.value / first) * 100))}%`,
                }}
              />
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

/* ============================================================== line chart */

export interface LinePoint {
  label: string;
  value: number | null;
  text: string;
}

/**
 * One figure's course, full width, with axes: the target as a dashed line and
 * the band between the amber line and the target shaded, so "how far off"
 * reads at a glance. A withheld point breaks the line.
 */
export function LineChart({
  points,
  label,
  target,
  amber,
  unit,
  format,
}: {
  points: LinePoint[];
  label: string;
  target?: number | null;
  amber?: number | null;
  unit: string;
  format: (n: number) => string;
}) {
  const [at, setAt] = React.useState<number | null>(null);
  const known = points.filter((p) => p.value !== null).map((p) => p.value as number);
  if (points.length < 2 || known.length === 0)
    return <Empty text="Too few points to draw a line for this period." />;
  const marks = [
    ...known,
    ...(target != null ? [target] : []),
    ...(amber != null ? [amber] : []),
  ];
  let lo = Math.min(...marks);
  let hi = Math.max(...marks);
  if (unit === "percent") {
    lo = Math.max(0, Math.floor((lo - 5) / 5) * 5);
    hi = Math.min(100, Math.ceil((hi + 2) / 5) * 5);
  } else {
    lo = 0;
    hi = niceTicks(hi).at(-1) ?? hi;
  }
  if (hi <= lo) hi = lo + 1;
  const W = 760;
  const H = 240;
  const L = 44;
  const R = 16;
  const T = 14;
  const B = 28;
  const x = (i: number) => L + (i * (W - L - R)) / (points.length - 1);
  const y = (v: number) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);

  const runs: Array<Array<[number, number]>> = [];
  let run: Array<[number, number]> = [];
  points.forEach((p, i) => {
    if (p.value === null) {
      if (run.length) runs.push(run);
      run = [];
    } else run.push([x(i), y(p.value)]);
  });
  if (run.length) runs.push(run);
  const d = (r: Array<[number, number]>) =>
    r.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join("");
  let last = points.length - 1;
  while (last > 0 && points[last].value === null) last -= 1;
  const every = Math.ceil(points.length / 12);
  const band =
    target != null && amber != null && amber !== target
      ? [Math.min(y(target), y(amber)), Math.abs(y(target) - y(amber))]
      : null;

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block h-auto w-full touch-none outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
        role="img"
        aria-label={`${label}: ${points.map((p) => `${p.label} ${p.text}`).join(", ")}`}
        tabIndex={0}
        onPointerMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          const xv = ((e.clientX - r.left) / r.width) * W;
          const i = Math.round(((xv - L) / (W - L - R)) * (points.length - 1));
          setAt(Math.max(0, Math.min(points.length - 1, i)));
        }}
        onPointerLeave={() => setAt(null)}
        onBlur={() => setAt(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const s = e.key === "ArrowRight" ? 1 : -1;
            setAt((c) => Math.max(0, Math.min(points.length - 1, (c ?? last) + s)));
          } else if (e.key === "Escape") setAt(null);
        }}
      >
        {band && (
          <rect
            x={L}
            y={band[0]}
            width={W - L - R}
            height={band[1]}
            fill="var(--warning-subtle)"
          />
        )}
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={L}
              x2={W - R}
              y1={y(t)}
              y2={y(t)}
              stroke={t === lo ? "var(--border-strong)" : "var(--viz-grid)"}
            />
            <text
              x={L - 6}
              y={y(t) + 3.5}
              textAnchor="end"
              className="fill-text-subtle text-[10px]"
            >
              {format(Number(t.toFixed(1)))}
            </text>
          </g>
        ))}
        {target != null && (
          <line
            x1={L}
            x2={W - R}
            y1={y(target)}
            y2={y(target)}
            stroke="var(--text)"
            strokeWidth="1.5"
            strokeDasharray="5 4"
          />
        )}
        {runs.map((r, i) =>
          r.length > 1 ? (
            <path
              key={i}
              d={d(r)}
              fill="none"
              stroke="var(--viz-2)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : (
            <circle key={i} cx={r[0][0]} cy={r[0][1]} r="3" fill="var(--viz-2)" />
          ),
        )}
        {at !== null && (
          <line x1={x(at)} x2={x(at)} y1={T} y2={H - B} stroke="var(--viz-neutral)" />
        )}
        {(() => {
          const i = at ?? last;
          const p = points[i];
          return p.value === null ? null : (
            <circle
              cx={x(i)}
              cy={y(p.value)}
              r="4.5"
              fill="var(--viz-2)"
              stroke="var(--surface)"
              strokeWidth="2"
            />
          );
        })()}
        {points.map((p, i) =>
          i % every === 0 || i === points.length - 1 ? (
            <text
              key={i}
              x={x(i)}
              y={H - 8}
              textAnchor="middle"
              className="fill-text-subtle text-[10px]"
            >
              {p.label}
            </text>
          ) : null,
        )}
      </svg>
      {at !== null && (
        <div
          role="status"
          className="pointer-events-none absolute top-0 z-10 rounded-lg bg-text px-2.5 py-1.5 text-xs whitespace-nowrap text-text-inverse shadow-[var(--shadow-raised)]"
          style={{ left: `${Math.min(80, Math.max(2, (x(at) / W) * 100 - 8))}%` }}
        >
          {points[at].label}:{" "}
          <span className="tabular font-semibold">{points[at].text}</span>
        </div>
      )}
    </div>
  );
}

/* ==================================================================== empty */

function Empty({ text = "Nothing to show for this period." }: { text?: string }) {
  return <p className="py-6 text-center text-sm text-text-subtle">{text}</p>;
}
