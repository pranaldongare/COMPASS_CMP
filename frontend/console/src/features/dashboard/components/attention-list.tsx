/**
 * What needs this person today.
 *
 * The first thing on the page, and the only thing sized by urgency. Each
 * row is one count that calls for an action, with a mark that says how
 * pressing, and a link that opens the list already filtered - or jumps to
 * the queue further down this page. Rows with nothing to count are not sent
 * by the server, so a quiet day reads as one line.
 *
 * Drawn as the role-dashboard design has it (2026-10-10): a dot with a soft
 * ring, the count in the same colour, the label, a Late / Due soon / To do
 * tag, and a chevron - one height, one column grid, so the rows line up.
 */
"use client";

import { AlertTriangle, ChevronRight } from "lucide-react";
import Link from "next/link";

import { PanelHeader } from "@/components/ui/panel";
import { Card } from "@/components/ui/primitives";
import { cn } from "@/lib/format";
import type { AttentionRow } from "@/types";

const MARK: Record<
  AttentionRow["severity"],
  { dot: string; text: string; tag: string; tagClass: string; word: string }
> = {
  critical: {
    dot: "bg-danger ring-4 ring-danger-subtle",
    text: "text-danger-text",
    tag: "Late",
    tagClass: "bg-danger-subtle text-danger-text",
    word: "overdue",
  },
  warning: {
    dot: "bg-warning ring-4 ring-warning-subtle",
    text: "text-warning-text",
    tag: "Due soon",
    tagClass: "bg-warning-subtle text-warning-text",
    word: "waiting",
  },
  info: {
    dot: "bg-text-subtle ring-4 ring-bg-inset",
    text: "text-text",
    tag: "To do",
    tagClass: "bg-bg-inset text-text-muted",
    word: "",
  },
};

export function AttentionList({ rows }: { rows: AttentionRow[] }) {
  return (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl">
      {/* Not "Needs you today - 5 things": the rows are kinds of work, each
          with its own count, and not every one is due today (UX review). */}
      <PanelHeader
        icon={AlertTriangle}
        tint="danger"
        title="Needs attention"
        count={rows.length}
      />
      {rows.length === 0 ? (
        <p className="px-[18px] py-4 text-sm text-text-muted">
          Nothing needs your attention. The queues below are clear or waiting on somebody
          else.
        </p>
      ) : (
        <ul data-testid="attention">
          {rows.map((row) => {
            const mark = MARK[row.severity];
            return (
              <li key={row.key} className="border-b border-border/60 last:border-b-0">
                <Link
                  href={row.href}
                  className="group grid h-[2.875rem] grid-cols-[1.375rem_3.5rem_minmax(0,1fr)_auto_1.125rem] items-center px-[18px] text-[0.8125rem] transition-colors hover:bg-[var(--row-hover)]"
                >
                  <span
                    className={cn("size-[9px] rounded-full", mark.dot)}
                    aria-hidden="true"
                  />
                  <span
                    className={cn(
                      "tabular pr-3.5 text-right text-base font-bold",
                      mark.text,
                    )}
                  >
                    {row.count}
                  </span>
                  <span className="truncate">
                    {row.label}
                    {mark.word && <span className="sr-only"> ({mark.word})</span>}
                  </span>
                  <span
                    aria-hidden="true"
                    className={cn(
                      "mr-2.5 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-semibold",
                      mark.tagClass,
                    )}
                  >
                    {mark.tag}
                  </span>
                  <ChevronRight
                    className="size-4 text-text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
