/**
 * The bar that names the next move on a record, above its tabs.
 *
 * One look, shared by every record that has one: a rights request since
 * 2026-10-30 (mock-up C), an incident or breach since 2026-11-13. What the
 * step is, and whether a button makes it, is each record's own business; this
 * is only how it is said - the step in bold, why it is next (or what it waits
 * on) beside it, what follows underneath, and one action on the right.
 */
import * as React from "react";

import { cn } from "@/lib/format";

export function NextStepBar({
  title,
  why,
  then,
  action,
}: {
  title: string;
  /** Why it is the next move, or what stops the one after it. */
  why?: string | null;
  /** What follows it, so the path ahead is in view. */
  then?: string | null;
  /** The button that makes the move, or opens where it is made. */
  action?: React.ReactNode;
}) {
  return (
    <section
      aria-label="Next step"
      className={cn(
        "mb-5 flex flex-wrap items-center justify-between gap-3 rounded-[14px] border border-accent-border",
        "bg-surface px-4 py-3 shadow-[inset_4px_0_0_var(--accent),var(--shadow-xs)]",
      )}
    >
      <div className="min-w-0 pl-1">
        <p className="text-2xs font-semibold tracking-wider text-accent-text uppercase">
          Next
        </p>
        <p className="text-sm">
          <span className="font-semibold">{title}</span>
          {why && <span className="text-text-muted"> - {why}</span>}
        </p>
        {then && <p className="mt-0.5 text-xs text-text-muted">{then}</p>}
      </div>
      {action}
    </section>
  );
}
