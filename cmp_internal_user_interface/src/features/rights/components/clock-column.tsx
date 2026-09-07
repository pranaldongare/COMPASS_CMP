/**
 * The clock column of the flow diagrams.
 *
 * Every date on a rights request is expressed relative to two fixed points -
 * D0, when it was received, and D, when the response is due - and the
 * checkpoints between them are the ones the diagrams name. The server computes
 * all of them, so this renders and never re-derives: a console that worked
 * out "halfway" on its own would eventually disagree with the acknowledgement
 * email that quoted the server's.
 *
 * The clock starts on receipt, not on verification. If that ever looks wrong
 * on this screen, the screen is right.
 */
"use client";

import { AlertTriangle, CheckCircle2, Circle, Clock3 } from "lucide-react";

import { cn, formatDate } from "@/lib/format";
import type { Clock } from "@/types";

const DETAIL: Record<Clock["checkpoints"][number]["key"], string> = {
  received: "D0. The clock starts here, whatever happens next.",
  acknowledge: "D0 + 2. Reference number and the date she will hear by.",
  tickets: "D0 + 5. Every holder has a ticket with a named responder.",
  halfway: "Halfway. Tickets fall due; anything missing is escalated once.",
  collate: "D − 5. Stop collecting, start collating.",
  due: "D. Release and close, on time - partial if it has to be.",
};

export function ClockColumn({
  clock,
  closed,
  compact = false,
}: {
  clock: Clock;
  closed: boolean;
  compact?: boolean;
}) {
  return (
    <div className="space-y-3">
      <Headline clock={clock} closed={closed} />

      <ol className="space-y-2" aria-label="Checkpoints">
        {clock.checkpoints.map((point) => {
          const isNext = clock.next_checkpoint === point.key && !closed;
          const Icon = point.passed ? CheckCircle2 : isNext ? Clock3 : Circle;
          return (
            <li
              key={point.key}
              className={cn(
                "flex items-start gap-2.5 rounded-md border px-3 py-2",
                point.passed && "border-border bg-bg-inset text-text-muted",
                isNext && "border-accent-border bg-accent-subtle",
                !point.passed && !isNext && "border-border",
              )}
            >
              <Icon
                className={cn(
                  "mt-0.5 size-4 shrink-0",
                  point.passed && "text-success",
                  isNext && "text-accent",
                  !point.passed && !isNext && "text-text-subtle",
                )}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
                  <span className="font-medium">{point.label}</span>
                  <span className="tabular text-xs text-text-subtle">{formatDate(point.at)}</span>
                </p>
                {!compact && <p className="mt-0.5 text-xs text-text-muted">{DETAIL[point.key]}</p>}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Headline({ clock, closed }: { clock: Clock; closed: boolean }) {
  if (closed) {
    return (
      <p className="text-sm text-text-muted">
        Closed. The response was due by {formatDate(clock.due_at)}.
      </p>
    );
  }
  if (clock.overdue) {
    return (
      <p className="flex items-center gap-2 rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-sm font-medium text-danger-text">
        <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
        Overdue by {Math.abs(clock.days_remaining)} day{Math.abs(clock.days_remaining) === 1 ? "" : "s"}.
        The clock did not pause.
      </p>
    );
  }
  return (
    <div>
      <p
        className={cn(
          "text-sm font-medium",
          clock.at_risk ? "text-warning-text" : "text-text",
        )}
      >
        {clock.days_remaining} day{clock.days_remaining === 1 ? "" : "s"} to respond
        {clock.at_risk && " - past the collation checkpoint"}
      </p>
      <div
        className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-bg-inset"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clock.progress * 100)}
        aria-label="Response period elapsed"
      >
        <div
          className={cn("h-full rounded-full", clock.at_risk ? "bg-warning" : "bg-accent")}
          style={{ width: `${Math.round(clock.progress * 100)}%` }}
        />
      </div>
    </div>
  );
}
