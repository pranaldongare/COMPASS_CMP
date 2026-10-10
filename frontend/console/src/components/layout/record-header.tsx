/**
 * The head of a record's page (2026-10-10, "Summary card + underline tabs",
 * the user's pick for detail pages): one white card - a gradient icon, the
 * record's name and status line, its actions at the right - over a strip of
 * up to four key facts, each with a tinted icon tile. The page's h1 is here;
 * the breadcrumb above it is the page header's.
 */
import Link from "next/link";
import * as React from "react";

import { Card } from "@/components/ui/primitives";
import { cn } from "@/lib/format";

export interface RecordFact {
  label: string;
  value: React.ReactNode;
  icon: React.ComponentType<{ className?: string }>;
  /** The tile's tint: blue, violet, teal or amber (.nav-tint-0..3). */
  tint: 0 | 1 | 2 | 3;
  /** Where the rows behind the figure are, when there is somewhere. */
  href?: string;
}

export function RecordHeader({
  icon,
  title,
  meta,
  actions,
  facts = [],
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  /** The status badge and the record's reference line. */
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  facts?: RecordFact[];
}) {
  return (
    <Card className="mb-5 overflow-hidden rounded-[14px]">
      <div className="flex flex-wrap items-start gap-4 px-5 py-4">
        <span
          aria-hidden="true"
          className="tile-blue grid size-13 shrink-0 place-items-center rounded-[14px] text-white shadow-[var(--shadow-xs)]"
        >
          {React.createElement(icon, { className: "size-6" })}
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="text-[1.375rem] leading-tight font-semibold tracking-tight">
            {title}
          </h1>
          {meta && (
            <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-text-muted">
              {meta}
            </div>
          )}
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2" data-testid="page-actions">
            {actions}
          </div>
        )}
      </div>
      {facts.length > 0 && (
        <div className="grid grid-cols-2 border-t border-border lg:grid-cols-4">
          {facts.map((fact, i) => {
            const body = (
              <>
                <span
                  aria-hidden="true"
                  className={cn("nav-tile size-8", `nav-tint-${fact.tint}`)}
                >
                  {React.createElement(fact.icon, { className: "size-4" })}
                </span>
                <div className="min-w-0">
                  <p className="text-xs text-text-subtle">{fact.label}</p>
                  <p className="tabular truncate text-sm font-semibold text-text">
                    {fact.value}
                  </p>
                </div>
              </>
            );
            const cell = cn(
              "flex items-center gap-3 px-5 py-3.5",
              // Rules between the facts, as in the reference: a column rule on
              // a desk; on a phone, two by two.
              i % 2 === 0 && "border-r border-border",
              i < facts.length - 2 && "border-b border-border lg:border-b-0",
              i % 4 !== 3 && "lg:border-r",
              i === facts.length - 1 && "lg:border-r-0",
            );
            const linkClass = cn(cell, "transition-colors hover:bg-[var(--row-hover)]");
            // A place on this page ("#notices") is a plain anchor, so the
            // page's tabs follow the address as they do for any fragment.
            return fact.href?.startsWith("#") ? (
              <a key={fact.label} href={fact.href} className={linkClass}>
                {body}
              </a>
            ) : fact.href ? (
              <Link key={fact.label} href={fact.href} className={linkClass}>
                {body}
              </Link>
            ) : (
              <div key={fact.label} className={cell}>
                {body}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
