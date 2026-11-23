/**
 * The two marks the Analytics page draws, hand-rolled in SVG.
 *
 * Built by the dataviz method: the data's job picks the form. A figure over a
 * period is a stat tile; its course over the period is one line (change over
 * time, a single series, so no legend - the tile's title names it); a figure
 * split by one breakdown is a magnitude comparison across named things, so a
 * one-hue horizontal bar list with the value at each tip.
 *
 * Colour is the console's validated `--viz-2` blue (checked with the
 * validator for `charts.tsx`, both modes), with recessive `--viz-grid` and
 * `--viz-track`. Text wears text tokens, never the series colour. A withheld
 * point is a gap in the line and "< N" in the list - never a zero, which
 * would be a claim the record does not make. Each chart is named for a
 * screen reader, and every value is in the tile's table view as well.
 *
 * A library was not warranted: two forms, both small, and the console's
 * existing charts are hand-drawn SVG for the same reason.
 */
"use client";

import * as React from "react";

import { cn } from "@/lib/format";

/* =============================================================== trend line */

export interface TrendPoint {
  label: string;
  value: number | null;
  /** Shown for a point: "92.5%", "< 5". */
  text: string;
}

/**
 * A figure's line over its period. 2px line, round joins, a 10% wash under
 * it, an end-dot with a surface ring, and a crosshair with the point's value
 * on hover or on the arrow keys.
 */
export function TrendLine({
  points,
  label,
  className,
}: {
  points: TrendPoint[];
  /** What the line is, for a screen reader: "Requests answered on time, by day". */
  label: string;
  className?: string;
}) {
  const [at, setAt] = React.useState<number | null>(null);
  const w = 240;
  const h = 56;
  const pad = 5;
  const known = points.filter((p) => p.value !== null).map((p) => p.value as number);
  if (points.length < 2 || known.length === 0) return null;

  const max = Math.max(...known);
  const min = Math.min(0, ...known);
  const span = max - min || 1;
  const x = (i: number) => pad + (i * (w - pad * 2)) / (points.length - 1);
  const y = (v: number) => h - pad - ((v - min) / span) * (h - pad * 2);

  // A withheld or empty point breaks the line rather than dropping to nought.
  const runs: Array<Array<[number, number]>> = [];
  let run: Array<[number, number]> = [];
  points.forEach((p, i) => {
    if (p.value === null) {
      if (run.length) runs.push(run);
      run = [];
    } else run.push([x(i), y(p.value)]);
  });
  if (run.length) runs.push(run);
  const path = (r: Array<[number, number]>) =>
    r.map(([px, py], i) => `${i ? "L" : "M"}${px.toFixed(1)} ${py.toFixed(1)}`).join("");

  let last = points.length - 1;
  while (last > 0 && points[last].value === null) last -= 1;
  const hovered = at !== null ? points[at] : null;

  function pick(clientX: number, rect: DOMRect) {
    const rel = ((clientX - rect.left) / rect.width) * w;
    const i = Math.round(((rel - pad) / (w - pad * 2)) * (points.length - 1));
    setAt(Math.max(0, Math.min(points.length - 1, i)));
  }

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        className="block h-14 w-full touch-none overflow-visible rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
        role="img"
        aria-label={`${label}: ${points.map((p) => `${p.label} ${p.text}`).join(", ")}`}
        tabIndex={0}
        onPointerMove={(e) => pick(e.clientX, e.currentTarget.getBoundingClientRect())}
        onPointerLeave={() => setAt(null)}
        onBlur={() => setAt(null)}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const step = e.key === "ArrowRight" ? 1 : -1;
            setAt((cur) => Math.max(0, Math.min(points.length - 1, (cur ?? last) + step)));
          } else if (e.key === "Escape") setAt(null);
        }}
      >
        {/* One recessive baseline: the line's floor. */}
        <line
          x1={pad}
          x2={w - pad}
          y1={h - pad}
          y2={h - pad}
          stroke="var(--viz-grid)"
          strokeWidth="1"
          vectorEffect="non-scaling-stroke"
        />
        {runs.map((r, i) =>
          r.length > 1 ? (
            <path
              key={`a${i}`}
              d={`${path(r)}L${r[r.length - 1][0]} ${h - pad}L${r[0][0]} ${h - pad}Z`}
              fill="var(--viz-2)"
              fillOpacity="0.1"
            />
          ) : null,
        )}
        {runs.map((r, i) =>
          r.length > 1 ? (
            <path
              key={`l${i}`}
              d={path(r)}
              fill="none"
              stroke="var(--viz-2)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          ) : (
            // A lone point between gaps still shows.
            <circle key={`d${i}`} cx={r[0][0]} cy={r[0][1]} r="2" fill="var(--viz-2)" />
          ),
        )}
        {hovered && at !== null && (
          <line
            x1={x(at)}
            x2={x(at)}
            y1={pad}
            y2={h - pad}
            stroke="var(--viz-neutral)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>
      {/* Dots drawn in HTML so they stay round on a stretched line. */}
      {(() => {
        const i = at ?? last;
        const p = points[i];
        if (p.value === null) return null;
        return (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--viz-2)] ring-2 ring-[var(--surface)]"
            style={{ left: `${(x(i) / w) * 100}%`, top: `${(y(p.value) / h) * 100}%` }}
          />
        );
      })()}
      {hovered && at !== null && (
        <span
          role="status"
          className="pointer-events-none absolute -top-7 z-10 -translate-x-1/2 rounded-md bg-text px-2 py-0.5 text-2xs whitespace-nowrap text-text-inverse shadow-[var(--shadow-raised)]"
          style={{ left: `${Math.min(85, Math.max(15, (x(at) / w) * 100))}%` }}
        >
          {hovered.label}: <span className="tabular font-semibold">{hovered.text}</span>
        </span>
      )}
    </div>
  );
}

/* ================================================================ bar list */

export interface BarItem {
  key: string;
  label: string;
  value: number | null;
  /** The value as shown at the bar's tip: "1,204", "92%", "< 5". */
  text: string;
  /** Withheld: no bar, and the reason said beside it. */
  withheld?: boolean;
}

/**
 * A figure split by one breakdown: label, a one-hue bar, the value at its
 * tip. Bars grow from one baseline; a percentage is drawn against 100 so two
 * offices' shares read as shares, not as a race.
 */
export function BreakdownBars({
  items,
  max,
  label,
  withheldNote,
}: {
  items: BarItem[];
  /** The scale's end; the largest value when not given. */
  max?: number;
  label: string;
  withheldNote?: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs text-text-subtle">Nothing to split for this period.</p>;
  }
  const top = max ?? Math.max(1, ...items.map((i) => i.value ?? 0));
  return (
    <ul className="space-y-1.5" aria-label={label}>
      {items.map((item) => (
        <li
          key={item.key}
          className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)_auto] items-center gap-2 text-xs"
        >
          <span className="truncate text-text-muted" title={item.label}>
            {item.label}
          </span>
          <span
            className="h-2 overflow-hidden rounded-full bg-[var(--viz-track)]"
            aria-hidden="true"
          >
            {!item.withheld && item.value !== null && item.value > 0 && (
              <span
                className="grow-x block h-full rounded-full bg-[var(--viz-2)]"
                style={{
                  width: `${Math.max(3, Math.min(100, (item.value / top) * 100))}%`,
                }}
              />
            )}
          </span>
          <span
            className={cn(
              "tabular text-right font-semibold",
              item.withheld ? "text-text-muted" : "text-text",
            )}
            title={item.withheld ? withheldNote : undefined}
          >
            {item.text}
            {item.withheld && withheldNote && (
              <span className="sr-only"> ({withheldNote})</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
