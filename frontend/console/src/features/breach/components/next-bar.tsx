/**
 * The next move on an incident or a breach, on every tab (the product owner,
 * 2026-11-13: "we have this in Rights, good to have it in Breach as well").
 *
 * The page said where a breach stood - what blocks closing, each duty and its
 * clock - and left the reader to work out which of them to pick up. This bar
 * names one: the step that stands between the record and its close and should
 * be taken first, with its clock, the button that takes it or the tab it is
 * taken on, and what else is running beside it. It is the bar a rights
 * request has (`NextStepBar`).
 *
 * Nothing here decides anything. Every fact is the server's own - the
 * validation, each duty's state and clock, where each report, the notice and
 * each ticket stands, and whether the breach may close - read from the same
 * answers the cards below draw. What this adds is only the order:
 *
 * 1. the validation, on an incident not yet recorded as a breach: a yes is
 *    what starts the duties. (A recorded breach being validated again keeps
 *    its duties running, so those are taken first and the validation after.)
 * 2. a duty the office can act on now, in the order the work runs: the
 *    organisation's board and CERT-In, whichever clock runs out sooner; the
 *    first intimation to the DPDP Board; the people affected; then the
 *    72-hour report, which accounts for all of them (`STAGE`);
 * 3. a ticket's answer to review;
 * 4. what is only waited for - a mail on its way, a notice going out, a
 *    ticket with its holder;
 * 5. closing, once nothing stands in the way.
 *
 * The assessment is not a step: nothing waits on it.
 *
 * The cards are read a moment apart, so two of them can disagree for one
 * round trip - the breach says a duty stands that the reports have not heard
 * of yet. Where that shows, the step is said plainly and leads to its tab;
 * it is never said from the answer that is behind.
 */
"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import * as React from "react";

import { NextStepBar } from "@/components/layout/next-step";
import { Button } from "@/components/ui/primitives";
import { getNotices } from "@/features/breach/api";
import { CloseBreachButton } from "@/features/breach/components/cards";
import { clockText } from "@/features/breach/components/copy";
import {
  NotifyBoardButton,
  mayTryAgain,
  onItsWay,
  useBreachDocuments,
} from "@/features/breach/components/reports-card";
import { formatDateTime } from "@/lib/format";
import { keys } from "@/lib/query";
import type {
  Breach,
  BreachDocumentKindView,
  BreachDocuments,
  BreachDuty,
  BreachDutyKind,
  BreachNotices,
  BreachTicket,
} from "@/types";

/** The tabs a next move can be made on. */
export type BreachNextTab = "duties" | "validation" | "reports" | "people" | "tickets";

export interface BreachNextStep {
  title: string;
  /** Its clock, or what it waits on. */
  why?: string | null;
  /** What else is due beside it, or what follows. */
  then?: string | null;
  /** The tab it is made on. */
  go?: BreachNextTab;
  /** Made from the bar itself: the board's report, or closing. */
  act?: "notify_board" | "close";
  /** Nothing for the office to do now: a mail, a delivery or a holder is waited for. */
  waiting?: boolean;
}

/** What the cards below have read, as far as they have: a step is said in
 *  less detail until its card's answer is in. */
export interface BreachNextFacts {
  documents?: BreachDocuments;
  notices?: BreachNotices;
  tickets?: BreachTicket[];
  /** The breach has been read again since the notices said every delivery had
   *  its outcome. If the people's duty still stands after that, no delivery
   *  will complete it: only a send does. */
  peopleDutyReread?: boolean;
  /** The moment the step is said at: the clock's, unless a test says. */
  now?: number;
}

const TAB_LABEL: Record<BreachNextTab, string> = {
  duties: "Duties",
  validation: "Validation",
  reports: "Reports",
  people: "People & notices",
  tickets: "Tickets",
};

/**
 * The order the work runs in. The organisation's board and CERT-In have the
 * short clocks - minutes and hours - so between those two the one that runs
 * out sooner is taken first. Then the first intimation, which is due without
 * delay and comes before the report that follows it up; the people affected;
 * and last the 72-hour report, which accounts for all of them. A clock that
 * has run out does not jump this order - a late 72-hour report is not written
 * before the intimation it follows - it is said, beside its duty.
 */
const STAGE: Record<BreachDutyKind, number> = {
  org_board: 0,
  cert_in: 0,
  board_intimation: 1,
  principals: 2,
  board_report: 3,
};

/** A regulator's report, named before its card has answered. */
const REPORT: Partial<Record<BreachDutyKind, string>> = {
  cert_in: "report to CERT-In",
  board_intimation: "initial intimation to the DPDP Board",
  board_report: "72-hour report to the DPDP Board",
};

const REGULATOR: Partial<Record<BreachDutyKind, string>> = {
  cert_in: "CERT-In",
  board_intimation: "the DPDP Board",
  board_report: "the DPDP Board",
};

/** How long a delivery may sit queued before only a send moves it: the
 *  server's `STALE_AFTER` (`domain/breach/notices.py`). The worker is done
 *  with a message in a few minutes; one queued longer was lost on its way. */
const QUEUE_LOST_AFTER_MS = 15 * 60_000;

function inOrder(duties: BreachDuty[]): BreachDuty[] {
  const stage = (d: BreachDuty) => STAGE[d.duty] ?? Object.keys(STAGE).length;
  const due = (d: BreachDuty) =>
    d.due_at ? Date.parse(d.due_at) : Number.POSITIVE_INFINITY;
  return [...duties].sort((a, b) => {
    if (stage(a) !== stage(b)) return stage(a) - stage(b);
    if (due(a) !== due(b)) return due(a) < due(b) ? -1 : 1;
    // The board before CERT-In where neither says when.
    return a.duty === b.duty ? 0 : a.duty === "org_board" ? -1 : 1;
  });
}

/** A duty's clock, as the reason it is next. */
function clockSaid(d: BreachDuty): string {
  const said = clockText(d.state, d.clock);
  if (d.due_at) {
    return d.clock.overdue
      ? `${said}: it was due ${formatDateTime(d.due_at)}`
      : `${said}, due ${formatDateTime(d.due_at)}`;
  }
  if (said === "Without delay") return "Due without delay";
  // That no internal target is set is the Duties tab's to say, not the step's.
  return `Due without delay: ${said.replace(" (no internal target set)", "")}`;
}

/** The other duties still running, with the clock of each that has one. */
function alsoDue(others: BreachDuty[]): string {
  const named = others.map((d) =>
    d.due_at ? `${d.label} (${clockText(d.state, d.clock).toLowerCase()})` : d.label,
  );
  return `Also due: ${named.join(" · ")}`;
}

/** What follows a step: the duties beside it, else what still stands before
 *  the close - a validation left open, a ticket - else the close. */
function after(others: BreachDuty[], openTickets: number, validating: boolean): string {
  if (others.length > 0) return alsoDue(others);
  if (validating) return "Then: the validation, which is still open.";
  return openTickets > 0 ? "Then: the tickets still open, then closing." : "Then: closing.";
}

const lower = (title: string) => title.charAt(0).toLowerCase() + title.slice(1);

/* ---------------------------------------------------------- one duty's step */

function boardStep(
  d: BreachDuty,
  view: BreachDocumentKindView | undefined,
): BreachNextStep {
  // Not read yet, or read before the duty was there: its tab says the rest.
  if (!view || view.duty_state !== "outstanding") {
    return { title: "Notify the organisation's board", why: clockSaid(d), go: "reports" };
  }
  const [latest] = view.versions;
  const sent = latest?.state === "finalised" ? latest : null;
  if (sent && onItsWay(sent.mail) > 0) {
    return {
      title: "The organisation's board report is on its way",
      why: "Its duty completes when the mail lands.",
      go: "reports",
      waiting: true,
    };
  }
  if (sent && mayTryAgain(view, sent)) {
    return sent.mail.delivered > 0
      ? {
          title: "Finish the organisation's board report",
          why: "Its mail was delivered and the duty is still open: press Try again on the Reports tab.",
          go: "reports",
        }
      : {
          title: "The organisation's board report reached nobody",
          why: `Press Try again on the Reports tab. ${clockSaid(d)}`,
          go: "reports",
        };
  }
  return {
    title:
      latest?.state === "draft"
        ? "Finish the report to the organisation's board"
        : "Notify the organisation's board",
    why: clockSaid(d),
    act: "notify_board",
  };
}

/** A report that goes to a regulator: the platform never sends it, so the
 *  step after finalising is the office's own mail, then the record of it. */
function regulatorStep(
  d: BreachDuty,
  view: BreachDocumentKindView | undefined,
): BreachNextStep {
  const report = view ? lower(view.title) : (REPORT[d.duty] ?? lower(d.label));
  const why = clockSaid(d);
  // Not read yet - or read before the duty was there, which is the only time
  // the server says such a report is blocked while its duty stands.
  if (!view || view.blocked_by) return { title: `Open the ${report}`, why, go: "reports" };
  const [latest] = view.versions;
  if (!latest) return { title: `Draft the ${report}`, why, go: "reports" };
  if (latest.state === "draft")
    return { title: `Finalise the ${report}`, why, go: "reports" };
  if (view.versions.some((v) => v.state === "finalised")) {
    return {
      title: `Send the ${report} yourself, then record it as sent`,
      why: `The platform does not send to ${REGULATOR[d.duty] ?? "a regulator"}: record it with the proof of approval, the mail you sent and the reference returned. ${why}`,
      go: "reports",
    };
  }
  return { title: `Open the ${report}`, why, go: "reports" };
}

/**
 * Telling the people affected. Its duty completes by delivery: when every
 * listed person has a version whose every channel has an outcome - delivered,
 * or failed after the worker's retries - which is what `unnotified` counts
 * down to. So "told" below means tried on every channel, never "reached".
 */
function peopleStep(d: BreachDuty, facts: BreachNextFacts): BreachNextStep {
  const why = clockSaid(d);
  const notices = facts.notices;
  if (!notices) return { title: "Tell the people affected", why, go: "people" };
  if (notices.listed === 0) {
    return {
      title: "List the people affected",
      why: `A notice goes to the people listed under Affected people. ${why}`,
      go: "people",
    };
  }
  const approved = [...notices.versions].reverse().find((v) => v.state === "approved");
  if (!approved) {
    return notices.versions.some((v) => v.state === "draft")
      ? {
          title: "Approve the notice to the people affected",
          why: `It says all five things Rule 7(1) asks for, then it is approved. ${why}`,
          go: "people",
        }
      : { title: "Draft the notice to the people affected", why, go: "people" };
  }
  if (notices.send_blocked_by) {
    return {
      title: "Send the notice to the people affected",
      why: notices.send_blocked_by,
      go: "people",
    };
  }

  if (notices.unnotified === 0) {
    // The worker completes the duty in the same write as the last outcome, so
    // a duty that still stands once the breach has been read again was not
    // completed by one: it came back - a yes after a no - after everybody had
    // been told, and only a send settles it. It tells nobody twice.
    return facts.peopleDutyReread
      ? {
          title: "Send the notice again to complete this duty",
          why: "Everyone listed has been told already, and the duty is still open - as after a yes that brings it back. Send completes it, and tells nobody twice.",
          go: "people",
        }
      : {
          title: "The notice to the people affected has gone out",
          why: "Checking that its duty has completed.",
          go: "people",
          waiting: true,
        };
  }

  const queued = notices.account.filter(
    (a) => a.version === approved.version && a.status === "queued" && a.people > 0,
  );
  const now = facts.now ?? Date.now();
  if (queued.some((a) => now - Date.parse(a.last_at) < QUEUE_LOST_AFTER_MS)) {
    const told = notices.listed - notices.unnotified;
    const failed = notices.failures.some((f) => f.version === approved.version);
    return {
      title: "The notice to the people affected is going out",
      why:
        `Every delivery to ${told} of the ${notices.listed} listed has been tried so far.` +
        (failed ? " Some failed: see People & notices." : ""),
      go: "people",
      waiting: true,
    };
  }
  if (queued.length > 0) {
    // Queued and never sent: lost before the worker saw them, which nothing
    // but a send queues again.
    return {
      title: "Send the notice again",
      why: `Deliveries queued more than 15 minutes ago did not go: sending again queues them once more. ${why}`,
      go: "people",
    };
  }
  const waiting = notices.unnotified;
  return {
    title: "Send the notice to the people affected",
    why: `${waiting} of the ${notices.listed} listed ${waiting === 1 ? "has" : "have"} not been told. ${why}`,
    go: "people",
  };
}

function dutyStep(d: BreachDuty, facts: BreachNextFacts): BreachNextStep {
  if (d.duty === "principals") return peopleStep(d, facts);
  const view = facts.documents?.kinds.find((k) => k.duty === d.duty);
  return d.duty === "org_board" ? boardStep(d, view) : regulatorStep(d, view);
}

/** An optional closure report left unfinished is worth a word before closing:
 *  nothing can be written or recorded on a closed breach. */
function closureSaid(b: Breach, documents: BreachDocuments | undefined): string | null {
  const view = documents?.kinds.find((k) => k.kind === "closure");
  if (!view || view.blocked_by) return null;
  const [latest] = view.versions;
  if (!latest) {
    return b.breach_reference
      ? "A closure report is optional: draft it under Reports first if one is wanted."
      : null;
  }
  if (latest.state === "draft") {
    return "The closure report is still a draft: finalise it first, or close without it.";
  }
  if (latest.state === "finalised") {
    return "The closure report is finalised and not yet recorded as sent: record it first, or close without that.";
  }
  return null;
}

/* ------------------------------------------------------------------ the step */

export function breachNextStep(
  b: Breach,
  facts: BreachNextFacts = {},
): BreachNextStep | null {
  if (b.status !== "open") return null;
  const [move] = b.transitions;
  // Shown only to someone the server offers the close to.
  if (!move || move.to !== "closed") return null;

  const outstanding = inOrder(b.obligations.filter((d) => d.state === "outstanding"));
  const open = (facts.tickets ?? []).filter(
    (t) => t.state === "issued" || t.state === "returned",
  );
  const toReview = open.filter((t) => t.state === "returned");
  const withHolders = open.filter((t) => t.state === "issued");
  const validating = b.determination === "pending";

  // Not yet a breach: the validation comes before everything, since a yes is
  // what starts the duties. CERT-In stands on its own test, and may be running.
  if (validating && b.breach_reference === null) {
    return {
      title: "Record the validation",
      why: "Is it a personal data breach under s.2(u)?",
      go: "validation",
      then:
        outstanding.length > 0
          ? alsoDue(outstanding)
          : "A yes records it, starts the DPDP duties and gives 30 minutes to tell the organisation's board.",
    };
  }

  const steps = outstanding.map((d) => ({ d, step: dutyStep(d, facts) }));
  const others = (than: BreachDuty) => outstanding.filter((d) => d !== than);

  const doable = steps.find(({ step }) => !step.waiting);
  if (doable)
    return { ...doable.step, then: after(others(doable.d), open.length, validating) };

  // Recorded as a breach and being validated again: a pending validation
  // changes no duty, so those keep their clocks and are taken first; the
  // question still has to be settled before the record can close.
  if (validating) {
    return {
      title: "Record the validation",
      why: "It is being validated again, and cannot close until that is settled.",
      go: "validation",
      then: after(outstanding, open.length, false),
    };
  }

  if (toReview.length > 0) {
    return {
      title:
        toReview.length === 1
          ? "Review the answer on a ticket"
          : `Review the answers on ${toReview.length} tickets`,
      why: "Close the ticket, or send it back with what is missing.",
      go: "tickets",
      then: after(outstanding, withHolders.length, false),
    };
  }

  const [waited] = steps;
  if (waited) return { ...waited.step, then: after(others(waited.d), open.length, false) };

  if (withHolders.length > 0) {
    const overdue = withHolders.filter((t) => t.overdue).length;
    return {
      title:
        withHolders.length === 1
          ? "Waiting for a ticket to be answered"
          : `Waiting for ${withHolders.length} tickets to be answered`,
      why:
        overdue > 0
          ? `${overdue} past ${overdue === 1 ? "its" : "their"} resolve-by date.`
          : null,
      go: "tickets",
      waiting: true,
      then: "Then: closing.",
    };
  }

  if (move.allowed) {
    return {
      title: "Ready to close",
      why:
        b.determination === "no"
          ? "It is not a personal data breach, and nothing is left open on it."
          : "Every duty is done or set aside, and no ticket is open.",
      act: "close",
      then: closureSaid(b, facts.documents),
    };
  }

  // The server still names something this page has not read yet (the tickets,
  // while they load): the Close card under the bar lists it.
  return {
    title: "Clear what still stands in the way of closing",
    why: "The list is under Close, below.",
  };
}

/* ------------------------------------------------------------------- the bar */

export function BreachNextBar({
  breach,
  tickets,
  tab,
  onGo,
}: {
  breach: Breach;
  /** The breach's tickets as the page has read them; undefined while it has not. */
  tickets?: BreachTicket[];
  /** The tab open now: a step made here needs no button to reach it. */
  tab: string;
  onGo: (tab: BreachNextTab) => void;
}) {
  // The same answers the Reports and People & notices cards draw, by the same
  // keys: one read between them, and a write on either card moves this too.
  const documents = useBreachDocuments(breach.breach_uuid);
  const notices = useQuery<BreachNotices>({
    queryKey: keys.breach.notices(breach.breach_uuid),
    queryFn: () => getNotices(breach.breach_uuid),
  });

  // The worker completes the people's duty in the same write as the last
  // delivery's outcome, and tells nobody. So once the notices say everyone
  // listed has been told, read the breach again: either the duty is done and
  // the step moves on without waiting for the minute's refresh, or it still
  // stands and will not complete by itself (`peopleDutyReread`).
  const qc = useQueryClient();
  const told =
    breach.obligations.some((d) => d.duty === "principals" && d.state === "outstanding") &&
    notices.data !== undefined &&
    notices.data.listed > 0 &&
    notices.data.unnotified === 0;
  const [was, setWas] = React.useState(told);
  const [reread, setReread] = React.useState(false);
  // A new time of "everyone told" starts unread.
  if (was !== told) {
    setWas(told);
    setReread(false);
  }
  React.useEffect(() => {
    if (!told) return;
    let live = true;
    void qc
      .invalidateQueries({ queryKey: keys.breach.detail(breach.breach_uuid), exact: true })
      .then(() => {
        if (live) setReread(true);
      });
    return () => {
      live = false;
    };
  }, [told, qc, breach.breach_uuid]);

  const step = breachNextStep(breach, {
    documents: documents.data,
    notices: notices.data,
    tickets,
    peopleDutyReread: reread,
  });

  // Nothing to say of a closed breach, and nothing can be written on one.
  if (!step) return null;
  // One board button for as long as there is a step: it owns the report being
  // written from it, so it stays mounted - showing nothing - when the step is
  // another, and the report's window is not lost as the step moves on.
  const board = <NotifyBoardButton breach={breach} quiet={step.act !== "notify_board"} />;

  let action: React.ReactNode = null;
  if (step.act === "close") {
    action = (
      <CloseBreachButton breach={breach} label={`Close ${breach.reference}`} size="sm" />
    );
  } else if (step.go && step.go !== tab) {
    const target = step.go;
    action = (
      <Button
        variant={step.waiting ? "secondary" : "primary"}
        size="sm"
        onClick={() => onGo(target)}
      >
        Go to {TAB_LABEL[target]}
        <ArrowRight className="size-4" />
      </Button>
    );
  }

  return (
    <NextStepBar
      title={step.title}
      why={step.why}
      then={step.then}
      action={
        <>
          {action}
          {board}
        </>
      }
    />
  );
}
