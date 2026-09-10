/**
 * The path: the flow diagram, rendered live against one request.
 *
 * Each diagram in the Privacy Engineering deck has three columns - the clock,
 * the path, and where it can end early. This is the middle and right columns.
 * The steps are the diagram's steps in the diagram's words; what changes is
 * their state, which is read off the request the server returned: done,
 * current, still ahead, or the early exit that was actually taken.
 *
 * Nothing here decides. A step is "done" because a timestamp the server set
 * is present, never because this component worked out that it should be.
 */
"use client";

import { ArrowRight, Check, CircleDot, XCircle } from "lucide-react";

import { cn } from "@/lib/format";
import type { MyRequest, RightsRequest, RightsRequestDetail } from "@/types";

type AnyRequest = RightsRequest | RightsRequestDetail | MyRequest;

export type StepState = "done" | "current" | "pending" | "exited";

export interface Step {
  n: number;
  title: string;
  detail: string;
  /** A step drawn as a question on the diagram. */
  decision?: boolean;
  state: StepState;
  /** The early exit attached to this step, and whether it was taken. */
  exit?: { title: string; detail: string; taken: boolean };
}

function has(value: unknown): boolean {
  return value !== null && value !== undefined;
}

function staff(r: AnyRequest): r is RightsRequest {
  return "holder_count" in r;
}

/** The steps for one request, states already decided. */
export function stepsFor(r: AnyRequest): Step[] {
  const closed = r.status === "closed";
  const started = r.status !== "received";
  const collated = r.status === "collating" || closed;
  const verified = r.verification_status === "verified";
  const classified = staff(r) ? has(r.classified_at) : started;
  const holders = staff(r) ? r.holder_count : 0;
  const holdersConfirmed = staff(r) ? r.holders_confirmed : 0;
  const ticketsIssued = staff(r) ? r.tickets_issued : 0;
  const gap = staff(r) ? r.tickets_outstanding > 0 || r.outcome === "partial" : r.outcome === "partial";
  const items = staff(r) ? r.item_count : 0;
  const undecided = staff(r) ? r.items_undecided : 0;
  const intent = staff(r) ? has(r.intent_confirmed_at) : started;
  const evidenced = staff(r) ? has(r.trigger_evidenced_at) : started;
  const aboutDpo = staff(r) ? r.about_dpo : false;
  const responded = closed && has(r.responded_at);

  const raw: Array<Omit<Step, "n" | "state"> & { done: boolean }> = [];
  const push = (step: Omit<Step, "n" | "state"> & { done: boolean }) => raw.push(step);

  // Everything begins the same way.
  push({ title: "Request received", detail: "Dashboard · notice link · email to the DPO - all three make the same record", done: true });
  push({ title: "Acknowledge", detail: "Reference number, expected date, and what she will receive", done: has(r.acknowledged_at) });
  push({
    title: "Identity verified?",
    detail: "session · code to a stored channel · manual, with reason recorded",
    decision: true,
    done: verified,
    exit: {
      title: "No match, or verification not satisfied",
      detail: "Neutral message - nothing is confirmed either way. Request closed and audited. She may try again.",
      taken: r.outcome === "not_verified",
    },
  });

  if (r.channel === "nominee") {
    push({
      title: "Is the triggering event evidenced?",
      detail: "Death or incapacity. What we accept as proof is a Legal decision",
      decision: true,
      done: evidenced,
      exit: {
        title: "The event is not evidenced",
        detail: "Refused, with the reason. She is not contacted - she may be exactly as incapacitated as claimed.",
        taken: r.outcome === "refused" && !evidenced,
      },
    });
  }

  switch (r.request_type) {
    case "access":
    case "correction":
      push({
        title: r.request_type === "access" ? "A valid access request?" : "A valid correction request?",
        detail: "The DPO can reclassify anything that arrived as free text",
        decision: true,
        done: classified,
        exit: {
          title: "Not a rights request, or refused",
          detail: "Reason given in writing, plus the grievance route. A refusal is still a response.",
          taken: r.outcome === "refused" && (r.channel !== "nominee" || evidenced),
        },
      });
      push({ title: "The CMP answers its own records", detail: "Consents, notices as read, withdrawals and export_line - no ticket needed", done: started });
      push({
        title: "Holders derived, DPO confirms",
        detail: "export_line and asset_consent are exact - the DPO adds what they miss",
        done: holdersConfirmed > 0 || collated,
        exit: {
          title: "No records held anywhere",
          detail: "A complete and valid response. Short path, same audit trail, same clock.",
          taken: r.outcome === "no_records",
        },
      });
      push({ title: "Tickets issued to each holder", detail: "Structured return form, named responder, internal due date set early", done: ticketsIssued > 0 || (collated && holders === 0) });
      push({
        title: "All responses returned?",
        detail: "The DPO sees completeness at a glance",
        decision: true,
        done: collated,
        exit: {
          title: "A holder misses its date",
          detail: "Escalate once, then respond partial and on time. The clock does not pause because a system is busy - the gap is named in the response.",
          taken: gap,
        },
      });
      push({ title: "Collate, review, redact", detail: "Third-party data removed. The DPO signs off - nothing releases automatically", done: responded });
      push({
        title: "Release and close",
        detail: "Authenticated, time-limited download from her dashboard - not an email",
        done: responded,
        exit: {
          title: "She disputes the response",
          detail: "Grievance under s.13, then the Data Protection Board. The Board link is already in every notice.",
          taken: false,
        },
      });
      break;

    case "erasure":
      push({
        title: "Withdrawal, or erasure?",
        detail: "Different rights, different outcomes - the DPO confirms which she means",
        decision: true,
        done: intent,
        exit: {
          title: "She meant withdrawal",
          detail: "Processing stops going forward. Data already collected is not reached by it. Handled under s.6(4), not s.12(3).",
          taken: r.outcome === "reclassified_withdrawal",
        },
      });
      push({ title: "Scope determined", detail: "What can go, what must stay, and the legal basis for each", done: items > 0 || collated });
      push({
        title: "Inside the one-year floor?",
        detail: "Rule 6 and Rule 8(3) bind even against her own request",
        decision: true,
        done: items > 0 && undecided === 0,
        exit: {
          title: "Inside the statutory floor",
          detail: "Retained, with the legal basis stated plainly in the response, and erased when the floor passes.",
          taken: false,
        },
      });
      push({ title: "Holders derived, DPO confirms", detail: "export_line and asset_consent name them - the DPO adds what they miss", done: holdersConfirmed > 0 || collated });
      push({ title: "Erasure instructions issued", detail: "One per holder, with a structured confirmation to return", done: ticketsIssued > 0 || (collated && holders === 0) });
      push({
        title: "All confirmations returned?",
        detail: "The DPO sees completeness at a glance",
        decision: true,
        done: collated,
        exit: {
          title: "A holder misses its date",
          detail: "Escalate once, then respond partial and on time. The clock does not pause because a system is busy.",
          taken: gap,
        },
      });
      push({ title: "Respond and close", detail: "What was erased, what was retained, and why each was decided", done: responded });
      break;

    case "grievance":
      push({ title: "Linked to an existing request?", detail: has(r.linked_reference) ? `Linked to ${r.linked_reference} - what was asked, what was returned and its trail are on this page` : "If so, the original request, its response and its trail are shown here", decision: true, done: classified });
      push({
        title: "Is the complaint about the DPO?",
        detail: "The DPO owns grievances, including ones about her own decisions",
        decision: true,
        done: classified,
        exit: {
          title: "The complaint is about the DPO",
          detail: "Escalated to an independent reviewer. Accountability cannot review itself and be credible.",
          taken: aboutDpo,
        },
      });
      push({ title: "Investigate", detail: "The original request, what was returned, what was released, and the log", done: started && (r.status !== "in_progress" || closed) });
      push({
        title: "Is it upheld?",
        detail: "Was the original handling wrong, incomplete, or late?",
        decision: true,
        done: closed && has(r.grievance_upheld),
        exit: {
          title: "Not upheld",
          detail: "A reasoned explanation in writing, plus the Data Protection Board route. Disagreement is not refusal.",
          taken: r.outcome === "not_upheld",
        },
      });
      push({ title: "Remedy applied", detail: "The original request is re-run or corrected, at no cost to her", done: r.outcome === "upheld" });
      push({
        title: "Respond and close",
        detail: "What was found, what was done, and her route onward to the Board",
        done: closed && has(r.responded_at),
        exit: {
          title: "She remains unsatisfied",
          detail: "The Data Protection Board. The link is already in every notice she was ever served.",
          taken: false,
        },
      });
      break;
  }

  // States. Done is what the server says; current is the first thing not
  // done while the request is open; exited is the exit that closed it.
  const exitedAt = raw.findIndex((s) => s.exit?.taken && closed && s.exit && !s.done);
  let currentAssigned = false;
  return raw.map((step, index) => {
    let state: StepState = step.done ? "done" : "pending";
    if (!step.done && closed && step.exit?.taken) state = "exited";
    else if (!step.done && closed && exitedAt >= 0 && index > exitedAt) state = "pending";
    else if (!step.done && !closed && !currentAssigned) {
      state = "current";
      currentAssigned = true;
    }
    return { ...step, n: index + 1, state };
  });
}

export function Path({ request }: { request: AnyRequest }) {
  const steps = stepsFor(request);
  return (
    <ol className="space-y-2" aria-label="The path">
      {steps.map((step) => (
        <li key={step.n} className="grid gap-2 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <StepCard step={step} />
          {step.exit && <ExitCard step={step} />}
        </li>
      ))}
    </ol>
  );
}

function StepCard({ step }: { step: Step }) {
  const Icon = step.state === "done" ? Check : step.state === "exited" ? XCircle : CircleDot;
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-md border px-3 py-2.5",
        step.state === "done" && "border-border bg-bg-inset",
        step.state === "current" && "border-accent-border bg-accent-subtle",
        step.state === "exited" && "border-danger-border bg-danger-subtle",
        step.state === "pending" && "border-border opacity-80",
        step.decision && step.state !== "done" && step.state !== "exited" && "border-warning-border",
      )}
      aria-current={step.state === "current" ? "step" : undefined}
    >
      <span
        className={cn(
          "mt-0.5 grid size-6 shrink-0 place-items-center rounded-md text-xs font-semibold text-white",
          step.state === "done" && "bg-success",
          step.state === "current" && "bg-accent",
          step.state === "exited" && "bg-danger",
          step.state === "pending" && "bg-text-subtle",
        )}
        aria-hidden="true"
      >
        {step.state === "done" || step.state === "exited" ? <Icon className="size-3.5" /> : step.n}
      </span>
      <div className="min-w-0">
        <p
          className={cn(
            "text-sm font-medium",
            step.decision && step.state === "current" && "text-warning-text",
          )}
        >
          {step.title}
        </p>
        <p className="mt-0.5 text-xs text-text-muted">{step.detail}</p>
      </div>
    </div>
  );
}

function ExitCard({ step }: { step: Step }) {
  const exit = step.exit!;
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md border px-3 py-2.5",
        exit.taken
          ? "border-danger-border bg-danger-subtle"
          : "border-dashed border-border text-text-subtle",
      )}
    >
      <ArrowRight
        className={cn("mt-0.5 size-4 shrink-0", exit.taken ? "text-danger" : "text-text-subtle")}
        aria-hidden="true"
      />
      <div className="min-w-0">
        <p className={cn("text-sm font-medium", exit.taken ? "text-danger-text" : "text-text-muted")}>
          {exit.title}
          {exit.taken && <span className="ml-2 text-2xs font-semibold uppercase tracking-wide">taken</span>}
        </p>
        <p className="mt-0.5 text-xs">{exit.detail}</p>
      </div>
    </div>
  );
}
