/**
 * What needs this person today.
 *
 * The first thing on the page, and the only thing sized by urgency. Each
 * row is one count that calls for an action, with a mark that says how
 * pressing, and a link that opens the list already filtered - or jumps to
 * the queue further down this page. Rows with nothing to count are not sent
 * by the server, so a quiet day reads as one line.
 */
"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/primitives";
import { cn } from "@/lib/format";
import type { AttentionRow } from "@/types";

const MARK: Record<AttentionRow["severity"], { dot: string; text: string; word: string }> = {
  critical: { dot: "bg-danger-text", text: "text-danger-text", word: "overdue" },
  warning: { dot: "bg-warning-text", text: "text-warning-text", word: "waiting" },
  info: { dot: "bg-text-subtle", text: "text-text-muted", word: "" },
};

export function AttentionList({ rows }: { rows: AttentionRow[] }) {
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Needs you today</CardTitle>
        {rows.length > 0 && (
          <span className="text-xs text-text-muted">
            {rows.length} {rows.length === 1 ? "thing" : "things"}
          </span>
        )}
      </CardHeader>
      {rows.length === 0 ? (
        <CardBody>
          <p className="text-sm text-text-muted">Nothing needs you today. The queues below are clear or waiting on somebody else.</p>
        </CardBody>
      ) : (
        <ul className="divide-y divide-border" data-testid="attention">
          {rows.map((row) => {
            const mark = MARK[row.severity];
            return (
              <li key={row.key}>
                <Link
                  href={row.href}
                  className="group flex items-center gap-4 px-5 py-3 transition-colors hover:bg-surface-hover"
                >
                  <span className={cn("size-2.5 shrink-0 rounded-full", mark.dot)} aria-hidden="true" />
                  <span className={cn("w-10 shrink-0 text-right text-lg font-semibold tabular", mark.text)}>
                    {row.count}
                  </span>
                  <span className="min-w-0 flex-1 text-sm">
                    {row.label}
                    {mark.word && <span className="sr-only"> ({mark.word})</span>}
                  </span>
                  <ArrowRight className="size-4 shrink-0 text-text-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent" aria-hidden="true" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
