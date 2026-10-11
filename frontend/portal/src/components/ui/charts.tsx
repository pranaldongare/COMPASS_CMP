/**
 * The chart vocabulary.
 *
 * Built by the method rather than by taste: the data's job picks the form, and
 * colour comes last. Two of these are deliberately *not* charts — a single
 * current value is a stat tile, and a ratio against a limit is a meter. A
 * one-bar bar chart says nothing a number does not.
 *
 * The three-hue palette in `globals.css` was checked with the dataviz
 * validator: all six checks pass in both modes, worst adjacent normal-vision
 * ΔE 24.0 light / 20.9 dark against a ≥15 floor. Two hues sit below 3:1 against
 * the surface, which obligates visible labels — so every segment here is
 * direct-labelled and every series is named in text. Identity never rests on
 * colour alone.
 */
"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/format";

/* ========================================================== stat tile / KPI */

/**
 * A single current value. The right form for one number, per the form
 * heuristic — a one-bar chart would carry the same information and less of it.
 */
export function StatTile({
  label,
  value,
  hint,
  hintTone = "neutral",
  trend,
  tone = "neutral",
  icon,
  tint,
  href,
  className,
}: {
  label: string;
  value: number | string;
  hint?: string;
  /** The hint's chip colour on a tinted tile (2026-10-10): green for good
   *  news, red for late, amber for due soon, grey otherwise. */
  hintTone?: "good" | "bad" | "warn" | "neutral";
  /** New records per day, oldest first (2026-10-11): drawn as a small line
   *  at the tile's lower right. */
  trend?: number[];
  /** `attention` is for a count that is a problem when non-zero. */
  tone?: "neutral" | "accent" | "attention";
  icon?: React.ReactNode;
  /** A coloured tile for the icon (2026-10-10), one per figure in a row. */
  tint?: "blue" | "amber" | "teal" | "violet";
  /** Where the rows behind this figure live. A number somebody wants to act on
   *  and cannot click is a dead end — the tile becomes a link when given one. */
  href?: string;
  className?: string;
}) {
  const shown = typeof value === "number" ? value.toLocaleString("en-IN") : value;

  // Branched rather than a polymorphic `Wrapper`: next/link's href is required,
  // so a component variable typed as `Link | "div"` cannot accept an optional
  // one without casting the type away.
  const classes = cn(
    "lift group relative block overflow-hidden rounded-lg border bg-surface p-4",
    "shadow-[var(--shadow-card)]",
    tone === "attention" ? "border-warning-border" : "border-border",
    href &&
      "cursor-pointer hover:border-accent-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]",
    className,
  );

  // The dashboard's figure (2026-10-10, the role-dashboard design): the icon
  // tile beside the label, a large figure, the hint as a coloured chip, and a
  // blue - or, when it needs action, amber - edge along the top.
  if (tint) {
    const tinted = (
      <>
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            className={cn(
              "grid size-9 shrink-0 place-items-center rounded-[11px] text-white [&_svg]:size-[1.125rem]",
              `tile-${tint}`,
            )}
          >
            {icon}
          </span>
          <p className="text-[0.8125rem] leading-tight font-medium text-text-muted">
            {label}
          </p>
        </div>
        <p className="tabular mt-3 text-[1.875rem] leading-none font-bold tracking-tight text-text">
          {shown}
        </p>
        {/* Clear of the trend line at the lower right. */}
        <p className={cn("mt-2 min-h-5", trend && trend.length > 1 && "pr-24")}>
          {hint && (
            <span
              className={cn(
                "inline-flex max-w-full truncate rounded-full px-2 py-0.5 text-[0.6875rem] font-bold",
                hintTone === "good" && "bg-success-subtle text-success-text",
                hintTone === "bad" && "bg-danger-subtle text-danger-text",
                hintTone === "warn" && "bg-warning-subtle text-warning-text",
                hintTone === "neutral" && "bg-bg-inset text-text-muted",
              )}
            >
              {hint}
            </span>
          )}
        </p>
        {trend && trend.length > 1 && (
          <Sparkline
            values={trend}
            color={TINT_COLOR[tint]}
            className="absolute right-3.5 bottom-4 h-9 w-24"
            label={`${label}: new each day, last ${trend.length} days`}
          />
        )}
      </>
    );
    const tintedClasses = cn(
      "lift group relative block h-full overflow-hidden rounded-2xl border border-border bg-surface px-[18px] pt-4 pb-3.5",
      tone === "attention"
        ? "shadow-[inset_0_3px_0_var(--warning),var(--shadow-xs)]"
        : "shadow-[inset_0_3px_0_var(--accent),var(--shadow-xs)]",
      href &&
        "cursor-pointer hover:border-accent-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]",
      className,
    );
    return href ? (
      <Link href={href} className={tintedClasses}>
        {tinted}
      </Link>
    ) : (
      <div className={tintedClasses}>{tinted}</div>
    );
  }

  const body = (
    <>
      {/* A hairline of colour along the top edge. Enough to group the tile with
          its meaning, not enough to compete with the figure. */}
      <span
        aria-hidden="true"
        className={cn(
          "absolute inset-x-0 top-0 h-0.5",
          tone === "attention"
            ? "bg-warning"
            : tone === "accent"
              ? "brand-gradient"
              : "bg-border",
        )}
      />

      {icon && tint && (
        <span
          aria-hidden="true"
          className={cn(
            "mb-3 grid size-9 place-items-center rounded-xl text-white shadow-[var(--shadow-xs)] [&_svg]:size-[1.125rem]",
            `tile-${tint}`,
          )}
        >
          {icon}
        </span>
      )}
      <div className="flex items-start justify-between gap-3">
        <p className="text-[0.8125rem] font-medium text-text-muted">{label}</p>
        {icon && !tint && (
          <span
            aria-hidden="true"
            className={cn(
              "grid size-7 shrink-0 place-items-center rounded-lg [&_svg]:size-3.5",
              tone === "attention"
                ? "bg-warning-subtle text-warning-text"
                : "bg-bg-inset text-text-subtle group-hover:bg-accent-subtle group-hover:text-accent-text",
              "transition-colors",
            )}
          >
            {icon}
          </span>
        )}
      </div>

      <p
        className={cn(
          "tabular mt-1.5 text-2xl font-semibold tracking-tight",
          tone === "attention" ? "text-warning-text" : "text-text",
        )}
      >
        {shown}
      </p>

      {hint && <p className="mt-0.5 text-xs text-text-muted">{hint}</p>}

      {href && (
        <span
          aria-hidden="true"
          className="absolute right-3 bottom-3 text-text-subtle opacity-0 transition-opacity group-hover:opacity-100"
        >
          <ArrowRight className="size-4" />
        </span>
      )}
    </>
  );

  return href ? (
    <Link href={href} className={classes}>
      {body}
    </Link>
  ) : (
    <div className={classes}>{body}</div>
  );
}

/* ==================================================================== meter */

/**
 * A single ratio against a limit. Same-ramp track, never a two-slice pie.
 *
 * Used for a consent link's use cap, where the question is "how much of the
 * allowance is gone" — one value against one limit.
 */
export function Meter({
  label,
  value,
  max,
  caption,
}: {
  label: string;
  value: number;
  max: number;
  caption?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  // Amber past 80%: the point at which somebody should be thinking about the
  // cap, not the point at which it is already too late.
  const tight = pct >= 80;

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-text-muted">{label}</span>
        <span className="tabular text-sm font-medium text-text">
          {value.toLocaleString("en-IN")}
          <span className="text-text-subtle"> / {max.toLocaleString("en-IN")}</span>
        </span>
      </div>

      <div
        className="mt-1.5 h-2 overflow-hidden rounded-full bg-[var(--viz-track)]"
        role="meter"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label}
      >
        <div
          className={cn(
            "grow-x h-full rounded-full",
            tight ? "bg-warning" : "bg-[var(--viz-2)]",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>

      {caption && <p className="mt-1 text-xs text-text-subtle">{caption}</p>}
    </div>
  );
}

/* ====================================================== stacked composition */

export interface Segment {
  key: string;
  label: string;
  value: number;
  /** A CSS colour, taken from the validated `--viz-*` slots. */
  color: string;
}

/**
 * Part-to-whole, horizontal.
 *
 * Horizontal because the category names are words ("Consented", "Withdrawn"),
 * and horizontal is what lets them be read without rotating anything.
 *
 * A 2px surface gap sits between segments so adjacent fills never touch — that
 * gap is what keeps two similar hues separable, and it is why the palette
 * validates on the *adjacent* pairlist rather than all pairs.
 */
export function StackedBar({
  segments,
  total,
  caption,
}: {
  segments: Segment[];
  total?: number;
  caption?: string;
}) {
  const sum = total ?? segments.reduce((acc, s) => acc + s.value, 0);
  const present = segments.filter((s) => s.value > 0);

  if (sum === 0) {
    return (
      <div>
        <div className="h-3 rounded-full bg-[var(--viz-track)]" aria-hidden="true" />
        <p className="mt-2 text-xs text-text-subtle">
          {caption ?? "Nothing recorded yet."}
        </p>
      </div>
    );
  }

  return (
    <div>
      <div
        className="flex h-3 gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={`${caption ?? "Composition"}: ${present
          .map((s) => `${s.label} ${s.value}`)
          .join(", ")}`}
      >
        {present.map((s) => (
          <div
            key={s.key}
            className="grow-x h-full first:rounded-l-full last:rounded-r-full"
            style={{ width: `${(s.value / sum) * 100}%`, background: s.color }}
          />
        ))}
      </div>

      {/* The legend is also the direct labelling. Every segment is named with
          its count, so the contrast WARN on two of the hues is covered and
          nobody has to match a colour to a key. */}
      <ul className="mt-3 grid [grid-template-columns:repeat(auto-fill,minmax(12rem,1fr))] gap-x-5 gap-y-1.5">
        {segments.map((s) => (
          <li key={s.key} className="flex items-center gap-2 text-sm">
            <span
              aria-hidden="true"
              className="size-2.5 shrink-0 rounded-[3px]"
              style={{ background: s.color }}
            />
            {/* Text wears text tokens, never the series colour. */}
            <span className="text-text-muted">{s.label}</span>
            <span className="tabular ml-auto font-medium text-text">
              {s.value.toLocaleString("en-IN")}
            </span>
            <span className="tabular w-10 text-right text-xs text-text-subtle">
              {sum > 0 ? `${Math.round((s.value / sum) * 100)}%` : "—"}
            </span>
          </li>
        ))}
      </ul>

      {caption && <p className="mt-3 text-xs text-text-subtle">{caption}</p>}
    </div>
  );
}

/* ================================================================ sparkline */

const TINT_COLOR = {
  blue: "#2f72bb",
  amber: "#e08a0b",
  teal: "#13a89e",
  violet: "#7c6cf0",
} as const;

/**
 * A small line of a figure's last few days (2026-10-11, the role-dashboard
 * design): the line and a soft fill under it, scaled to its own range. Named
 * for screen readers by `label`, with the values in its title.
 */
export function Sparkline({
  values,
  color,
  label,
  className,
}: {
  values: number[];
  color: string;
  label: string;
  className?: string;
}) {
  const id = React.useId().replace(/:/g, "");
  const w = 96;
  const h = 36;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const points = values.map((v, i) => [
    (i * w) / (values.length - 1),
    h - 4 - ((v - min) / span) * (h - 8),
  ]);
  const line = points
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join("");
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={className}
      role="img"
      aria-label={`${label}: ${values.join(", ")}`}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`${id}-f`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.22" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${line}L${w} ${h}L0 ${h}Z`} fill={`url(#${id}-f)`} />
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* ==================================================================== donut */

/**
 * A whole in its parts, as a ring (2026-10-10, the role-dashboard design):
 * the total in the middle and a legend beside it with each part's count and
 * share. A part too small to see keeps a sliver so it is still on the ring.
 */
export function Donut({
  segments,
  centreLabel = "records",
}: {
  segments: Array<{
    key: string;
    label: string;
    value: number;
    color: string;
    href?: string;
  }>;
  centreLabel?: string;
}) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const r = 60;
  const circumference = 2 * Math.PI * r;
  const shown = segments.filter((s) => s.value > 0);
  // Each arc starts where the ones before it end.
  const arcs = shown.map((s, i) => {
    const before = shown.slice(0, i).reduce((sum, p) => sum + p.value, 0);
    return {
      key: s.key,
      color: s.color,
      length: Math.max((s.value / Math.max(total, 1)) * circumference - 2, 1.2),
      offset: (before / Math.max(total, 1)) * circumference,
    };
  });
  return (
    <div className="grid items-center gap-6 sm:grid-cols-[9.5rem_minmax(0,1fr)]">
      <div className="relative mx-auto size-[9.5rem]">
        <svg viewBox="0 0 150 150" className="size-full" aria-hidden="true">
          <circle
            cx="75"
            cy="75"
            r={r}
            fill="none"
            stroke="var(--viz-track)"
            strokeWidth="16"
          />
          {arcs.map((a) => (
            <circle
              key={a.key}
              cx="75"
              cy="75"
              r={r}
              fill="none"
              stroke={a.color}
              strokeWidth="16"
              strokeDasharray={`${a.length} ${circumference - a.length}`}
              strokeDashoffset={-a.offset}
              transform="rotate(-90 75 75)"
            />
          ))}
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="tabular text-2xl font-bold">{total.toLocaleString("en-IN")}</p>
            <p className="text-xs text-text-subtle">{centreLabel}</p>
          </div>
        </div>
      </div>
      <ul className="grid gap-2.5 text-[0.8125rem]">
        {segments.map((s) => {
          const share = total ? Math.round((s.value / total) * 100) : 0;
          const row = (
            <>
              <span
                aria-hidden="true"
                className="size-2.5 rounded-[3px]"
                style={{ background: s.color }}
              />
              <span className="truncate">{s.label}</span>
              <span className="tabular text-right font-semibold">
                {s.value.toLocaleString("en-IN")}
              </span>
              <span className="tabular text-right text-xs text-text-subtle">{share}%</span>
            </>
          );
          const grid =
            "grid grid-cols-[0.75rem_minmax(0,1fr)_auto_2.75rem] items-center gap-2";
          return (
            <li key={s.key}>
              {s.href ? (
                <Link
                  href={s.href}
                  className={cn(
                    grid,
                    "-mx-1.5 rounded-md px-1.5 py-0.5 hover:bg-surface-hover",
                  )}
                >
                  {row}
                </Link>
              ) : (
                <div className={grid}>{row}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ==================================================== ranked magnitude bars */

/**
 * Compare magnitude across a handful of named things.
 *
 * One hue, more-is-longer — sequential is the safe default when the job is
 * magnitude rather than identity, and it cannot be misread the way eight
 * categorical hues can.
 */
export function BarList({
  items,
  emptyLabel = "Nothing to show",
}: {
  items: Array<{ key: string; label: string; value: number; href?: string }>;
  emptyLabel?: string;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));

  if (items.length === 0) {
    return <p className="py-4 text-sm text-text-subtle">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-2.5">
      {items.map((item) => {
        // Label, track and figure on one line (2026-10-10), so a column of
        // bars reads as a table.
        const row = (
          <div className="grid grid-cols-[7.5rem_minmax(0,1fr)_2.5rem] items-center gap-3 text-[0.8125rem]">
            <span className="truncate text-text-muted group-hover:text-text">
              {item.label}
            </span>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--viz-track)]">
              <div
                className="grow-x h-full rounded-full bg-linear-to-r from-accent to-[#4a90d9]"
                style={{ width: `${Math.max(4, (item.value / max) * 100)}%` }}
              />
            </div>
            <span className="tabular text-right font-semibold text-text">
              {item.value.toLocaleString("en-IN")}
            </span>
          </div>
        );

        return (
          <li key={item.key}>
            {/* A bar the reader wants to interrogate should take them to the
                rows behind it, not just sit there being a length. */}
            {item.href ? (
              <Link
                href={item.href}
                className="group -mx-2 block rounded-lg px-2 py-1 transition-colors hover:bg-surface-hover focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)] focus-visible:outline-none"
              >
                {row}
              </Link>
            ) : (
              row
            )}
          </li>
        );
      })}
    </ul>
  );
}

/* ============================================================ progress ring */

/* ================================================================= pipeline */

/**
 * An ordered process, drawn.
 *
 * Not a chart — a diagram of a state machine. The current step is marked with
 * text as well as colour (`aria-current` plus a visually-hidden "current
 * step"), so the position survives greyscale and screen readers alike.
 */
export function Pipeline({
  steps,
  currentIndex,
  terminal,
}: {
  steps: Array<{ key: string; label: string }>;
  currentIndex: number;
  /** Set when the machine has left the happy path (e.g. closed). */
  terminal?: { label: string; note?: string };
}) {
  if (terminal) {
    return (
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-bg-subtle px-3 py-2">
        <span className="rounded-full bg-bg-inset px-2.5 py-1 text-xs font-medium text-text-muted">
          {terminal.label}
        </span>
        {terminal.note && <span className="text-xs text-text-subtle">{terminal.note}</span>}
      </div>
    );
  }

  return (
    <ol className="flex flex-wrap items-center gap-1.5" aria-label="Progress">
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const current = index === currentIndex;

        return (
          <li key={step.key} className="flex items-center gap-1.5">
            <span
              aria-current={current ? "step" : undefined}
              className={cn(
                "relative rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                current &&
                  "brand-gradient border-transparent text-white shadow-[var(--shadow-sm)]",
                done && "border-success-border bg-success-subtle text-success-text",
                !current && !done && "border-border bg-bg-inset text-text-subtle",
              )}
            >
              {step.label}
              {current && <span className="sr-only"> (current step)</span>}
              {done && <span className="sr-only"> (completed)</span>}
            </span>

            {index < steps.length - 1 && (
              <span
                aria-hidden="true"
                className={cn(
                  "h-px w-4 rounded-full",
                  done ? "bg-success-border" : "bg-border",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
