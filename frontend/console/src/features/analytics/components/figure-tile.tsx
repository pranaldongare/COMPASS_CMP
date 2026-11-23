/**
 * One figure, as a tile: its title, its value in its unit, the previous
 * period and the change, its target and status, a line over the period, its
 * breakdown when one is chosen, and exactly what it counts.
 *
 * The stat-tile contract from the dataviz method: label, value, a delta
 * coloured by direction times whether up is good (with an arrow and words,
 * never colour alone), and a small trend. The status badge carries an icon
 * and its label, so On target / Watch / Off target read without colour.
 */
"use client";

import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CircleAlert,
  CircleCheck,
  CircleX,
  Info,
} from "lucide-react";
import * as React from "react";

import { Tooltip } from "@/components/ui/overlay";
import { Badge } from "@/components/ui/primitives";
import { BreakdownBars, TrendLine } from "@/features/analytics/components/charts";
import {
  RAG,
  bucketLabel,
  changeTone,
  formatChange,
  shownValue,
  targetText,
  withheldText,
} from "@/features/analytics/format";
import { cn } from "@/lib/format";
import type { Figure } from "@/types";

const RAG_ICON = { green: CircleCheck, amber: CircleAlert, red: CircleX } as const;

export function RagBadge({ status }: { status: string | null }) {
  if (!status || !RAG[status]) return null;
  const Icon = RAG_ICON[status as keyof typeof RAG_ICON];
  return (
    <Badge tone={RAG[status].tone} className="shrink-0">
      <Icon className="size-3.5" aria-hidden="true" />
      {RAG[status].label}
    </Badge>
  );
}

export function FigureTile({
  figure,
  threshold,
  previousLabel,
  grain,
  dimLabel,
  compare,
}: {
  figure: Figure;
  threshold: number;
  /** The previous period's name: "October 2026". */
  previousLabel: string | null;
  grain: string | null;
  /** The chosen breakdown's name, when one is chosen and this figure has it. */
  dimLabel: string | null;
  compare: boolean;
}) {
  const id = React.useId();
  const f = figure;
  const value = shownValue(f.value, f.suppressed, f.unit, threshold);
  const tone = changeTone(f.change, f.higher_is_better);
  const Arrow =
    f.change === null || f.change === 0
      ? ArrowRight
      : f.change > 0
        ? ArrowUpRight
        : ArrowDownRight;
  const comparable = compare && f.kind !== "snapshot" && f.kind !== "live";
  const withheld = withheldText(threshold);
  const points = f.series.map((p) => ({
    label: bucketLabel(p.bucket, grain),
    value: p.suppressed ? null : p.value,
    text: shownValue(p.value, p.suppressed, f.unit, threshold),
  }));
  const parts = f.breakdown.map((p) => ({
    key: p.key ?? p.label,
    label: p.label,
    value: p.value,
    text: shownValue(p.value, p.suppressed, f.unit, threshold),
    withheld: p.suppressed,
  }));

  return (
    <article
      aria-labelledby={`${id}-t`}
      className="flex h-full flex-col rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-xs)]"
    >
      <div className="flex items-start justify-between gap-3">
        <h3
          id={`${id}-t`}
          className="text-[0.8125rem] leading-snug font-medium text-text-muted"
        >
          {f.title}
        </h3>
        <RagBadge status={f.status} />
      </div>

      <p className="mt-2 flex items-baseline gap-1.5 text-[1.75rem] leading-none font-semibold tracking-tight text-text">
        {f.suppressed ? (
          <Tooltip content={withheld}>
            <span
              tabIndex={0}
              className="cursor-help rounded-sm underline decoration-dotted decoration-1 underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]"
            >
              {value}
            </span>
          </Tooltip>
        ) : (
          value
        )}
      </p>
      {f.suppressed && <p className="mt-1 text-xs text-text-subtle">{withheld}</p>}
      {!f.suppressed && f.value === null && (
        <p className="mt-1 text-xs text-text-subtle">Nothing to count in this period.</p>
      )}

      <dl className="mt-3 space-y-1 text-xs">
        {comparable && (
          <div className="flex flex-wrap items-center gap-x-1.5">
            <dt className="text-text-subtle">
              {previousLabel ? `${previousLabel}:` : "Previous period:"}
            </dt>
            <dd className="tabular text-text-muted">
              {shownValue(f.previous, f.previous_suppressed, f.unit, threshold)}
            </dd>
            {f.change !== null && (
              <dd
                className={cn(
                  "inline-flex items-center gap-0.5 font-semibold",
                  tone === "good" && "text-success-text",
                  tone === "bad" && "text-danger-text",
                  tone === "flat" && "text-text-muted",
                )}
              >
                <Arrow className="size-3.5" aria-hidden="true" />
                <span className="tabular">{formatChange(f.change, f.unit)}</span>
                <span className="sr-only">
                  {tone === "good"
                    ? " (better)"
                    : tone === "bad"
                      ? " (worse)"
                      : " (no change)"}
                </span>
              </dd>
            )}
          </div>
        )}
        {f.target !== null && (
          <div className="flex flex-wrap gap-x-1.5">
            <dt className="text-text-subtle">Target:</dt>
            <dd className="text-text-muted">
              {targetText(f.target, f.unit, f.higher_is_better)}
              {f.amber !== null && f.amber !== f.target && (
                <span className="text-text-subtle">
                  {" "}
                  (watch to {shownValue(f.amber, false, f.unit, threshold)})
                </span>
              )}
            </dd>
          </div>
        )}
      </dl>

      {points.length > 1 && (
        <TrendLine
          points={points}
          label={`${f.title}, by ${grain ?? "period"}`}
          className="mt-4"
        />
      )}

      {dimLabel && (
        <div className="mt-4 border-t border-border pt-3">
          <p className="mb-2 text-2xs font-semibold tracking-wide text-text-subtle uppercase">
            By {dimLabel.toLowerCase()}
          </p>
          <BreakdownBars
            items={parts}
            max={f.unit === "percent" ? 100 : undefined}
            label={`${f.title} by ${dimLabel.toLowerCase()}`}
            withheldNote={withheld}
          />
        </div>
      )}

      <details className="group mt-auto pt-3 text-xs">
        <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded-sm text-accent-text outline-none hover:underline focus-visible:ring-2 focus-visible:ring-[var(--accent-border)] [&::-webkit-details-marker]:hidden">
          <Info className="size-3.5" aria-hidden="true" />
          What this counts
        </summary>
        <p className="mt-2 leading-relaxed text-text-muted">{f.definition}</p>
        {/* The table view: every point of the line, for anyone who would
            rather read the numbers than the shape. */}
        {points.length > 1 && (
          <table className="mt-2 w-full text-left">
            <caption className="sr-only">
              {f.title}, by {grain ?? "period"}
            </caption>
            <thead>
              <tr className="text-text-subtle">
                <th scope="col" className="py-0.5 font-medium">
                  {grain === "month" ? "Month" : grain === "week" ? "Week of" : "Day"}
                </th>
                <th scope="col" className="py-0.5 text-right font-medium">
                  Value
                </th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={i} className="border-t border-border">
                  <td className="py-0.5 text-text-muted">{p.label}</td>
                  <td className="tabular py-0.5 text-right text-text">{p.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </article>
  );
}
