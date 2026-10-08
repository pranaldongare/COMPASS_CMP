/**
 * Where one request stands, in four lines, before anything else on its page.
 *
 * The request page used to open on the requester's details and then the full
 * clock and path, which put the deadline, the current step and what to do
 * about it some 4,000 pixels down a phone (UX review 2026-10-05). These four
 * are what somebody opening a request needs first: when it is due, where it
 * is on the path, who has it, and the next move - or what is stopping it.
 *
 * Everything here is read off the server's answer: the clock it computed, the
 * path's current step, the transitions it offers. Nothing is decided here.
 */
"use client";

import { AlertTriangle, ArrowDown } from "lucide-react";

import { Card, CardBody } from "@/components/ui/primitives";
import { OUTCOME_COPY, STATUS_COPY } from "@/features/rights/components/copy";
import { stepsFor } from "@/features/rights/components/path";
import { cn, formatDate, formatDateTime } from "@/lib/format";
import type { RightsRequestDetail } from "@/types";

/** What the office does next on the holders card, if anything. */
function holdersMove(r: RightsRequestDetail): string | null {
  if (!["in_progress", "awaiting_holders", "collating"].includes(r.status)) return null;
  const n = (state: string) => r.holders.filter((h) => h.state === state).length;
  // Holders are confirmed and sent tickets only before collating.
  const sending = r.status !== "collating";
  const steps: [number, string, string][] = [
    [sending ? n("not_confirmed") : 0, "Confirm who answers", "Confirm who answers for {n} holders"],
    [sending ? n("not_sent") : 0, "Send the ticket", "Send {n} tickets"],
    [n("review"), "Review an answer", "Review {n} answers"],
    [n("overdue"), "Chase an overdue holder", "Chase {n} overdue holders"],
  ];
  const step = steps.find(([k]) => k > 0);
  if (!step) return null;
  const [k, one, many] = step;
  return k === 1 ? one : many.replace("{n}", String(k));
}

/** Moves the server makes by itself, so never offered as a button. */
export const AUTOMATIC: readonly string[] = ["awaiting_holders"];

/**
 * The next move: a holder needing the office first, then the move the server
 * offers, or the first thing blocking one.
 */
export function nextMove(r: RightsRequestDetail): {
  label: string;
  blocked?: string;
  href?: string;
} | null {
  if (r.status === "closed") return null;
  const holders = holdersMove(r);
  if (holders) return { label: holders, href: "#holders" };
  // Never a way back (one that asks why): the next move is forward.
  const open = r.transitions.find(
    (t) => t.allowed && !AUTOMATIC.includes(t.to) && !t.reason_required,
  );
  if (open) {
    return {
      label:
        open.via === "respond"
          ? "Respond and close"
          : `Move to ${STATUS_COPY[open.to].label.toLowerCase()}`,
    };
  }
  const blocked = r.transitions.find(
    (t) => t.blocked_by && !AUTOMATIC.includes(t.to) && !t.reason_required,
  );
  if (blocked?.blocked_by) {
    return {
      label:
        blocked.via === "respond"
          ? "Respond and close"
          : `Move to ${STATUS_COPY[blocked.to].label.toLowerCase()}`,
      blocked: blocked.blocked_by,
    };
  }
  return null;
}

export function RequestSummary({
  request: r,
  actionsHref,
}: {
  request: RightsRequestDetail;
  /** Where the controls that make the next move are on this page. */
  actionsHref: string;
}) {
  const closed = r.status === "closed";
  const clock = r.clock;
  const current = stepsFor(r).find((s) => s.state === "current");
  const checkpoint = clock.checkpoints.find((c) => c.key === clock.next_checkpoint);
  const move = nextMove(r);
  const days = Math.abs(clock.days_remaining);

  return (
    <Card>
      <CardBody>
        <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">{closed ? "Closed" : "Due"}</dt>
            <dd className="mt-0.5">
              {closed ? (
                <>
                  <span className="text-sm font-semibold">
                    {r.closed_at ? formatDate(r.closed_at) : "Closed"}
                  </span>
                  {r.outcome && (
                    <span className="block text-xs text-text-muted">
                      {OUTCOME_COPY[r.outcome].label}
                    </span>
                  )}
                </>
              ) : (
                <>
                  <span className="text-sm font-semibold">{formatDate(clock.due_at)}</span>
                  <span
                    className={cn(
                      "block text-xs",
                      clock.overdue
                        ? "font-medium text-danger-text"
                        : clock.at_risk
                          ? "font-medium text-warning-text"
                          : "text-text-muted",
                    )}
                  >
                    {clock.overdue
                      ? `Overdue by ${days} ${days === 1 ? "day" : "days"}`
                      : `${days} ${days === 1 ? "day" : "days"} left`}
                    {checkpoint &&
                      !clock.overdue &&
                      ` · next: ${checkpoint.label.toLowerCase()} by ${formatDateTime(checkpoint.at)}`}
                  </span>
                </>
              )}
            </dd>
          </div>

          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">Current step</dt>
            <dd className="mt-0.5">
              <span className="text-sm font-semibold">
                {closed ? "Closed" : (current?.title ?? STATUS_COPY[r.status].label)}
              </span>
              {!closed && current?.detail && (
                <span className="block text-xs text-text-muted">{current.detail}</span>
              )}
            </dd>
          </div>

          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">With</dt>
            <dd className="mt-0.5">
              {/* A complaint about the DPO is not theirs to answer; an
                  administrator names somebody else, and until then nobody has
                  it - which is worth saying rather than implying the DPO. */}
              <span className="text-sm font-semibold">
                {r.about_dpo
                  ? (r.reviewer_name ?? "Nobody yet")
                  : "Data Protection Officer"}
              </span>
              {r.about_dpo && (
                <span className="block text-xs text-text-muted">
                  {r.reviewer_name
                    ? "Reviewing a complaint about the DPO"
                    : "An administrator names a reviewer"}
                </span>
              )}
            </dd>
          </div>

          <div className="min-w-0">
            <dt className="text-xs text-text-subtle">Next</dt>
            <dd className="mt-0.5">
              {move ? (
                <>
                  <a
                    href={move.href ?? actionsHref}
                    className="inline-flex items-center gap-1 text-sm font-semibold text-accent-text hover:underline"
                  >
                    {move.label}
                    <ArrowDown className="size-3.5" aria-hidden="true" />
                  </a>
                  {move.blocked && (
                    <span className="mt-0.5 flex items-start gap-1 text-xs text-warning-text">
                      <AlertTriangle
                        className="mt-0.5 size-3 shrink-0"
                        aria-hidden="true"
                      />
                      {move.blocked}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-sm text-text-muted">
                  {closed
                    ? "Nothing - a disagreement is a new, linked request"
                    : "Work the step above; the next move opens when it is done"}
                </span>
              )}
            </dd>
          </div>
        </dl>
      </CardBody>
    </Card>
  );
}
