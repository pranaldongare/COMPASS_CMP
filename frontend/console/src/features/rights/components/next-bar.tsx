/**
 * The one move open on a request, on every tab (2026-10-30, mock-up C).
 *
 * Once identity and classification were done the page said nothing about
 * what came next: the claim sat in a card on the overview, the start in
 * another, the holders on their own tab. This bar names the next move, makes
 * it when it is one button (claim, a forward move), or opens the tab where it
 * is made, and says what follows.
 *
 * What may happen is still the server's answer: the bar shows only to someone
 * the server offers moves to, and a blocked move is explained in the server's
 * own words. The order of the steps before work begins is the order the
 * server checks them in (verified, classified, claimed, then the erasure and
 * nominee questions).
 */
"use client";

import { ArrowRight } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { STATUS_COPY } from "@/features/rights/components/copy";
import {
  AUTOMATIC,
  holdersNotYetFound,
  nextMove,
} from "@/features/rights/components/request-summary";
import { useClaimRequest, useTransitionRequest } from "@/features/rights/mutations";
import { cn } from "@/lib/format";
import { useToast } from "@/providers";
import type { RightsRequestDetail } from "@/types";

/** The tabs a next move can be made on. */
export type NextTab = "overview" | "identity" | "holders" | "response";

export interface NextStep {
  title: string;
  /** Why it is the next move, or what stops the one after it. */
  why?: string | null;
  /** What follows it, so the path ahead is in view. */
  then?: string;
  /** Made from the bar itself. */
  claim?: boolean;
  move?: string;
  /** Otherwise the tab it is made on. */
  go?: NextTab;
}

const TAB_LABEL: Record<NextTab, string> = {
  overview: "Overview",
  identity: "Identity",
  holders: "Holders",
  response: "Response",
};

function statusLabel(to: string): string {
  return (STATUS_COPY[to as keyof typeof STATUS_COPY]?.label ?? to).toLowerCase();
}

export function nextStep(r: RightsRequestDetail): NextStep | null {
  if (r.status === "closed" || r.transitions.length === 0) return null;
  const grievance = r.request_type === "grievance";
  const afterStart = grievance
    ? "Then: move to in progress → respond"
    : "Then: move to in progress → Holders";

  if (r.status === "received") {
    const start = r.transitions.find((t) => t.to === "in_progress");
    if (!start) return null;
    if (start.allowed) {
      return {
        title: "Start the work",
        why: "Everything before work begins is settled.",
        move: "in_progress",
        then: grievance ? "Then: respond" : "Then: Holders - find who holds the data",
      };
    }
    const why = start.blocked_by ?? null;
    if (r.verification_status !== "verified") {
      return {
        title: "Verify who it is",
        why,
        go: "identity",
        then: "Then: confirm what kind of request it is",
      };
    }
    if (!r.classified_at) {
      return {
        title: "Confirm what kind of request it is",
        why,
        go: "identity",
        then: r.office
          ? afterStart
          : "Then: claim it for your office → move to in progress",
      };
    }
    if (!r.office) {
      return {
        title: "Claim it for your office",
        why: "It is in the shared intake: both offices see it until one claims it.",
        claim: true,
        then: afterStart,
      };
    }
    if (r.request_type === "erasure" && !r.intent_confirmed_at) {
      return {
        title: "Confirm withdrawal or erasure",
        why,
        go: "identity",
        then: afterStart,
      };
    }
    if (r.channel === "nominee" && !r.trigger_evidenced_at) {
      return {
        title: "Decide whether the event is evidenced",
        why,
        go: "identity",
        then: afterStart,
      };
    }
    return { title: "Start the work", why, go: "overview" };
  }

  // At work: the holders first, then the move forward the server offers.
  if (holdersNotYetFound(r)) {
    return {
      title: "Find who holds the data",
      go: "holders",
      then: "Then: confirm who answers → send the tickets. Nothing to ask anyone? Move it to collating from Overview instead.",
    };
  }
  const holders = nextMove(r);
  if (holders?.href === "#holders") return { title: holders.label, go: "holders" };
  const forward = r.transitions.filter(
    (t) => !AUTOMATIC.includes(t.to) && !t.reason_required,
  );
  const open = forward.find((t) => t.allowed);
  const next = open ?? forward.find((t) => t.blocked_by);
  if (!next) return null;
  if (next.via === "respond") {
    return {
      title: "Respond and close",
      why: open ? null : next.blocked_by,
      go: open || grievance ? "response" : "holders",
    };
  }
  return open
    ? { title: `Move it to ${statusLabel(next.to)}`, move: next.to }
    : {
        title: `Move it to ${statusLabel(next.to)}`,
        why: next.blocked_by,
        go: grievance ? "overview" : "holders",
      };
}

export function NextBar({
  request: r,
  tab,
  onGo,
}: {
  request: RightsRequestDetail;
  /** The tab open now: a step made here needs no button to reach it. */
  tab: string;
  onGo: (tab: NextTab) => void;
}) {
  const toast = useToast();
  const claim = useClaimRequest(r.request_uuid);
  const move = useTransitionRequest(r.request_uuid);
  const step = nextStep(r);
  if (!step) return null;

  async function act() {
    try {
      if (step?.claim) {
        await claim.mutateAsync();
        toast.success("Claimed for your office");
      } else if (step?.move) {
        await move.mutateAsync({ to: step.move });
        toast.success(`Moved to ${statusLabel(step.move)}`);
      }
    } catch (err) {
      const message =
        err && typeof err === "object" && "userMessage" in err
          ? (err as { userMessage: () => string }).userMessage()
          : "The server refused.";
      toast.error("Not done", message);
    }
  }

  let action: React.ReactNode = null;
  if (step.claim || step.move) {
    action = (
      <Button
        variant="primary"
        size="sm"
        loading={claim.isPending || move.isPending}
        onClick={act}
      >
        {step.claim ? "Claim for my office" : `Move to ${statusLabel(step.move ?? "")}`}
      </Button>
    );
  } else if (step.go && step.go !== tab) {
    const target = step.go;
    action = (
      <Button variant="primary" size="sm" onClick={() => onGo(target)}>
        Go to {TAB_LABEL[target]}
        <ArrowRight className="size-4" />
      </Button>
    );
  }

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
          <span className="font-semibold">{step.title}</span>
          {step.why && <span className="text-text-muted"> - {step.why}</span>}
        </p>
        {step.then && <p className="mt-0.5 text-xs text-text-muted">{step.then}</p>}
      </div>
      {action}
    </section>
  );
}
