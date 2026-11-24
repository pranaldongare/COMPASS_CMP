/**
 * A figure as a clickable tile (2026-11-24 redesign): its name, its value, the
 * change since the period before, a small trend, its status and its target -
 * and the whole tile opens the figure's own page, with its line, breakdown,
 * definition and numbers.
 *
 * The stat-tile contract: a delta coloured by whether it is good news (with
 * an arrow and words, never colour alone), the status as an icon and a word.
 * One link per tile, named for what it opens, so a screen reader hears the
 * figure and where it goes once.
 */
"use client";

import { ArrowDownRight, ArrowRight, ArrowUpRight, ChevronRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { TrendLine } from "@/features/analytics/components/charts";
import { RagBadge } from "@/features/analytics/components/figure-tile";
import {
  RAG,
  bucketLabel,
  changeTone,
  formatChange,
  shownValue,
  targetText,
} from "@/features/analytics/format";
import { cn } from "@/lib/format";
import type { Figure } from "@/types";

export function FigureCard({
  figure: f,
  threshold,
  previousLabel,
  grain,
  compare,
  href,
}: {
  figure: Figure;
  threshold: number;
  previousLabel: string | null;
  grain: string | null;
  compare: boolean;
  href: string;
}) {
  const value = shownValue(f.value, f.suppressed, f.unit, threshold);
  const tone = changeTone(f.change, f.higher_is_better);
  const Arrow =
    f.change === null || f.change === 0
      ? ArrowRight
      : f.change > 0
        ? ArrowUpRight
        : ArrowDownRight;
  const comparable =
    compare && f.kind !== "snapshot" && f.kind !== "live" && f.change !== null;
  const points = f.series.map((p) => ({
    label: bucketLabel(p.bucket, grain),
    value: p.suppressed ? null : p.value,
    text: shownValue(p.value, p.suppressed, f.unit, threshold),
  }));
  const spoken = [
    f.title,
    value,
    f.status && RAG[f.status] ? RAG[f.status].label : null,
    comparable
      ? `${formatChange(f.change!, f.unit)} ${tone === "good" ? "better" : tone === "bad" ? "worse" : ""} than ${previousLabel ?? "the period before"}`
      : null,
    "Open details",
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <Link
      href={href}
      aria-label={spoken}
      className={cn(
        "group flex h-full flex-col gap-3 rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-xs)] transition-[border-color,box-shadow]",
        "hover:border-accent-border hover:shadow-[var(--shadow-raised)]",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-[0.8125rem] leading-snug font-medium text-text-muted">
          {f.title}
        </h3>
        <ChevronRight
          className="size-4 flex-none text-text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent-text"
          aria-hidden="true"
        />
      </div>

      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="tabular text-[1.625rem] leading-none font-semibold tracking-tight text-text">
            {value}
          </p>
          {comparable ? (
            <p
              className={cn(
                "mt-1.5 inline-flex items-center gap-0.5 text-xs font-medium",
                tone === "good" && "text-success-text",
                tone === "bad" && "text-danger-text",
                tone === "flat" && "text-text-muted",
              )}
            >
              <Arrow className="size-3.5" aria-hidden="true" />
              <span className="tabular">{formatChange(f.change!, f.unit)}</span>
              <span className="text-text-muted">
                &nbsp;vs {previousLabel ?? "previous"}
              </span>
            </p>
          ) : f.suppressed ? (
            <p className="mt-1.5 text-xs text-text-subtle">Too few to show</p>
          ) : f.value === null ? (
            <p className="mt-1.5 text-xs text-text-subtle">Nothing to count yet</p>
          ) : null}
        </div>
        {points.length > 1 && (
          <TrendLine
            points={points}
            label={`${f.title} over the period`}
            className="w-28 flex-none"
            interactive={false}
          />
        )}
      </div>

      {(f.status || f.target !== null) && (
        <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-2.5">
          <RagBadge status={f.status} />
          {f.target !== null && (
            <span className="text-xs text-text-muted">
              Target {targetText(f.target, f.unit, f.higher_is_better)}
            </span>
          )}
        </div>
      )}
    </Link>
  );
}

/**
 * The figures off target or worth watching, worst first, each a link to its
 * page - the first thing on the page, because it is the first question.
 */
export function AttentionStrip({
  figures,
  threshold,
  hrefOf,
}: {
  figures: Figure[];
  threshold: number;
  hrefOf: (key: string) => string;
}) {
  const flagged = figures
    .filter((f) => f.status === "red" || f.status === "amber")
    .sort((a, b) => (a.status === b.status ? 0 : a.status === "red" ? -1 : 1));
  if (flagged.length === 0) {
    const judged = figures.filter((f) => f.status).length;
    if (judged === 0) return null;
    return (
      <p className="rounded-xl border border-success-border bg-success-subtle px-4 py-3 text-sm text-success-text">
        Every figure with a target is on target for this period ({judged} in all).
      </p>
    );
  }
  return (
    <section aria-labelledby="attention-title" className="space-y-2.5">
      <h2 id="attention-title" className="text-sm font-semibold text-text">
        Needs attention{" "}
        <span className="font-normal text-text-muted">
          · {flagged.length} {flagged.length === 1 ? "figure" : "figures"} off target or
          close to it
        </span>
      </h2>
      <ul className="grid [grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))] gap-3">
        {flagged.slice(0, 6).map((f) => {
          const red = f.status === "red";
          return (
            <li key={f.key}>
              <Link
                href={hrefOf(f.key)}
                className={cn(
                  "flex h-full items-start gap-3 rounded-xl border px-4 py-3 transition-shadow hover:shadow-[var(--shadow-raised)]",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                  red
                    ? "border-danger-border bg-danger-subtle"
                    : "border-warning-border bg-warning-subtle",
                )}
              >
                <RagBadge status={f.status} />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-text">
                    {f.title}: {shownValue(f.value, f.suppressed, f.unit, threshold)}
                  </span>
                  {f.target !== null && (
                    <span className="block text-xs text-text-muted">
                      Target {targetText(f.target, f.unit, f.higher_is_better)}
                      {f.change !== null && f.change !== 0 && (
                        <> · {formatChange(f.change, f.unit)} since the period before</>
                      )}
                    </span>
                  )}
                </span>
                <ChevronRight
                  className="mt-0.5 size-4 flex-none text-text-muted"
                  aria-hidden="true"
                />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
