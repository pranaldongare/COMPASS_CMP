/**
 * The breadcrumb above a page's title (2026-10-10, "Pill steps", chosen from
 * three): each step a small white pill with its icon, chevrons between, the
 * page you are on a blue pill. The shells build the steps from the menu, so
 * no page has to; a page's own back link, when it has one, sits at the row's
 * right end.
 */
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/format";

export interface Crumb {
  label: string;
  /** Absent on the last step: that is where you are. */
  href?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

const pill =
  "inline-flex h-7 max-w-64 items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium whitespace-nowrap";

export function PillTrail({ crumbs, extra }: { crumbs: Crumb[]; extra?: React.ReactNode }) {
  if (crumbs.length === 0 && !extra) return null;
  return (
    <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-2">
      {crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="flex flex-wrap items-center gap-1.5">
            {crumbs.map((crumb, i) => {
              const last = i === crumbs.length - 1;
              const body = (
                <>
                  {crumb.icon &&
                    React.createElement(crumb.icon, {
                      className: "size-3.5 shrink-0",
                      "aria-hidden": true,
                    } as { className: string })}
                  <span className="truncate">{crumb.label}</span>
                </>
              );
              return (
                <React.Fragment key={`${i}:${crumb.label}`}>
                  {i > 0 && (
                    <li aria-hidden="true" className="text-text-subtle">
                      <ChevronRight className="size-3.5" />
                    </li>
                  )}
                  <li className="min-w-0">
                    {last || !crumb.href ? (
                      <span
                        aria-current={last ? "page" : undefined}
                        className={cn(
                          pill,
                          last
                            ? "border-accent-border bg-accent-subtle font-semibold text-accent-text"
                            : "border-border bg-surface text-text-muted",
                        )}
                      >
                        {body}
                      </span>
                    ) : (
                      <Link
                        href={crumb.href}
                        className={cn(
                          pill,
                          "border-border bg-surface text-text-muted shadow-[var(--shadow-xs)] transition-colors",
                          "outline-none hover:border-border-strong hover:text-text focus-visible:ring-2 focus-visible:ring-[var(--accent-border)]",
                        )}
                      >
                        {body}
                      </Link>
                    )}
                  </li>
                </React.Fragment>
              );
            })}
          </ol>
        </nav>
      )}
      {extra && <div className="ml-auto text-sm text-text-muted">{extra}</div>}
    </div>
  );
}
