/**
 * The next move on an incident or a breach (2026-11-13): which step the bar
 * names, in what order, in which words, and what its button does. Every fact
 * is one the server serves - the validation, each duty's state and clock,
 * where a report, the notice and a ticket stand, whether it may close - and
 * the bar only chooses among them.
 */
import { QueryClient } from "@tanstack/react-query";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BreachNextBar, breachNextStep } from "@/features/breach/components/next-bar";
import { keys } from "@/lib/query";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type {
  Breach,
  BreachDocument,
  BreachDocumentKind,
  BreachDocumentKindView,
  BreachDocumentMail,
  BreachDocuments,
  BreachDuty,
  BreachDutyKind,
  BreachNotice,
  BreachNotices,
  BreachTicket,
} from "@/types";

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const UUID = "66666666-6666-4666-8666-666666666666";

/* ------------------------------------------------------------------ fixtures */

const LABEL: Record<BreachDutyKind, string> = {
  org_board: "Organisation's board",
  cert_in: "Report to CERT-In",
  board_intimation: "Board - initial intimation",
  board_report: "Board - detailed report",
  principals: "Principals notified",
};

/** A dated duty with `left` seconds to run (negative: overdue by that much). */
function dated(
  kind: BreachDutyKind,
  left: number,
  due_at = "2026-11-13T10:30:00Z",
): BreachDuty {
  return {
    obligation_uuid: `duty-${kind}`,
    duty: kind,
    label: LABEL[kind],
    basis: "",
    created_at: "2026-11-13T10:00:00Z",
    state: "outstanding",
    due_at,
    anchored_at: "2026-11-13T10:00:00Z",
    completed_at: null,
    reference: null,
    reported_to: null,
    extended_until: null,
    extension_requested_at: null,
    clock: {
      without_delay: false,
      seconds_remaining: Math.abs(left),
      overdue: left < 0,
      seconds_elapsed: 600,
      target_at: null,
      past_target: false,
    },
    events: [],
  };
}

/** A duty due without delay; `pastTarget` once the internal target has gone. */
function withoutDelay(
  kind: BreachDutyKind,
  pastTarget = false,
  target_at: string | null = null,
): BreachDuty {
  return {
    ...dated(kind, 0),
    due_at: null,
    clock: {
      without_delay: true,
      seconds_remaining: null,
      overdue: false,
      seconds_elapsed: 3 * 3600,
      target_at,
      past_target: pastTarget,
    },
  };
}

const breach = (over: Partial<Breach> = {}): Breach =>
  ({
    breach_uuid: UUID,
    reference: "BR-2026-0042",
    incident_reference: "INC-2026-0042",
    breach_reference: "BR-2026-0042",
    title: "A laptop left on a train",
    status: "open",
    determination: "yes",
    obligations: [],
    determinations: [],
    attachments: [],
    status_history: [],
    transitions: [
      {
        to: "closed",
        allowed: false,
        blocked_by: "x",
        blockers: ["x"],
        reason_required: false,
      },
    ],
    without_delay_target_hours: null,
    ...over,
  }) as Breach;

const CLOSABLE = [
  {
    to: "closed" as const,
    allowed: true,
    blocked_by: null,
    blockers: [],
    reason_required: false,
  },
];

const mail = (over: Partial<BreachDocumentMail> = {}): BreachDocumentMail => ({
  delivered: 0,
  queued: 0,
  failed: 0,
  unsent: 0,
  held: 0,
  stale: 0,
  retryable: 0,
  withheld_because: null,
  recipients: [],
  ...over,
});

const queuedTo = (n: number): BreachDocumentMail =>
  mail({
    queued: n,
    recipients: Array.from({ length: n }, (_, i) => ({
      recipient_uuid: `r${i}`,
      full_name: null,
      email: `board${i}@example.org`,
      status: "queued" as const,
      attempt: 1,
      error: null,
      recorded_at: "2026-11-13T10:01:00Z",
      removed: false,
      mandatory: false,
      added_for_this_send: false,
    })),
  });

const doc = (
  kind: BreachDocumentKind,
  state: BreachDocument["state"],
  over: Partial<BreachDocument> = {},
) =>
  ({
    report_uuid: `${kind}-${state}-${over.version ?? 1}`,
    kind,
    title: "",
    version: 1,
    state,
    superseded: false,
    sections: [],
    evidence: [],
    mail: mail(),
    ...over,
  }) as BreachDocument;

const TITLE: Record<BreachDocumentKind, string> = {
  org_board: "Report to the organisation's board",
  board_intimation: "Initial intimation to the DPDP Board",
  cert_in: "Report to CERT-In",
  board_report: "72-hour report to the DPDP Board",
  closure: "Closure report",
};

const kind = (
  k: BreachDocumentKind,
  versions: BreachDocument[] = [],
  over: Partial<BreachDocumentKindView> = {},
): BreachDocumentKindView => ({
  kind: k,
  title: TITLE[k],
  basis: "",
  duty: k === "closure" ? null : k,
  duty_state: k === "closure" ? null : "outstanding",
  blocked_by: null,
  goes_to_regulator: k !== "org_board",
  holds_mail: false,
  versions,
  ...over,
});

const documents = (...kinds: BreachDocumentKindView[]): BreachDocuments =>
  ({ kinds, board_recipients: 2, proofs: [] }) as unknown as BreachDocuments;

const notice = (state: BreachNotice["state"], version = 1) =>
  ({ notice_uuid: `n${version}`, version, state }) as BreachNotice;

const notices = (over: Partial<BreachNotices> = {}): BreachNotices => ({
  versions: [],
  account: [],
  failures: [],
  listed: 3,
  contacts: 0,
  unnotified: 3,
  contents: [],
  duty: "Principals notified",
  send_blocked_by: null,
  ...over,
});

const ticket = (state: BreachTicket["state"], overdue = false) =>
  ({ ticket_uuid: `t-${state}-${overdue}`, state, overdue }) as BreachTicket;

/* ------------------------------------------------------------ which step */

describe("breachNextStep: when there is one", () => {
  it("has none for a closed breach, or for someone the close is not offered to", () => {
    expect(breachNextStep(breach({ status: "closed" }))).toBeNull();
    expect(breachNextStep(breach({ transitions: [] }))).toBeNull();
    expect(
      breachNextStep(
        breach({
          transitions: [
            {
              to: "open",
              allowed: true,
              blocked_by: null,
              blockers: [],
              reason_required: true,
            },
          ],
        }),
      ),
    ).toBeNull();
  });

  it("starts with the validation, which is what starts the duties", () => {
    const step = breachNextStep(
      breach({ determination: "pending", breach_reference: null }),
    );
    expect(step).toMatchObject({
      title: "Record the validation",
      why: "Is it a personal data breach under s.2(u)?",
      go: "validation",
    });
    expect(step?.then).toMatch(
      /A yes records it, starts the DPDP duties and gives 30 minutes/,
    );
  });

  it("names CERT-In beside a pending validation when its clock is already running", () => {
    const step = breachNextStep(
      breach({
        determination: "pending",
        breach_reference: null,
        obligations: [dated("cert_in", 5 * 3600 + 720)],
      }),
    );
    expect(step).toMatchObject({ title: "Record the validation", go: "validation" });
    expect(step?.then).toBe("Also due: Report to CERT-In (5 h 12 min left)");
  });
});

describe("breachNextStep: validated again, on a recorded breach", () => {
  // A pending validation changes no duty: the clocks a yes started keep running.
  const again = (over: Partial<Breach> = {}, facts = {}) =>
    breachNextStep(breach({ determination: "pending", ...over }), facts);

  it("takes a running duty first, and says the validation comes after it, not the close", () => {
    const step = again(
      { obligations: [dated("org_board", 20 * 60)] },
      { documents: documents(kind("org_board")) },
    );
    expect(step).toMatchObject({
      title: "Notify the organisation's board",
      act: "notify_board",
      then: "Then: the validation, which is still open.",
    });
    // With a ticket open too, the validation is still what comes next.
    expect(
      again(
        { obligations: [dated("org_board", 20 * 60)] },
        { documents: documents(kind("org_board")), tickets: [ticket("issued")] },
      )?.then,
    ).toBe("Then: the validation, which is still open.");
  });

  it("asks for the validation before a ticket, a wait or the close", () => {
    const sending = documents(
      kind("org_board", [doc("org_board", "finalised", { mail: queuedTo(1) })]),
    );
    const step = again(
      { obligations: [dated("org_board", 20 * 60)] },
      { documents: sending, tickets: [ticket("returned")] },
    );
    expect(step).toMatchObject({
      title: "Record the validation",
      why: "It is being validated again, and cannot close until that is settled.",
      go: "validation",
      then: "Also due: Organisation's board (20 min left)",
    });
    expect(again({}, { tickets: [ticket("issued")] })?.then).toBe(
      "Then: the tickets still open, then closing.",
    );
    expect(again()).toMatchObject({
      title: "Record the validation",
      then: "Then: closing.",
    });
  });
});

describe("breachNextStep: the order", () => {
  const all = [
    dated("board_report", 70 * 3600),
    withoutDelay("principals"),
    withoutDelay("board_intimation"),
    dated("cert_in", 5 * 3600),
    dated("org_board", 28 * 60),
  ];

  it("takes the duties in the order the work runs, whatever order they are served in", () => {
    const step = breachNextStep(breach({ obligations: all }));
    expect(step).toMatchObject({ title: "Notify the organisation's board", go: "reports" });
    expect(step?.then).toBe(
      "Also due: Report to CERT-In (5 h 0 min left) · Board - initial intimation · Principals notified · Board - detailed report (2 d 22 h left)",
    );
  });

  it("takes whichever of the board and CERT-In runs out sooner", () => {
    const certInSooner = [
      dated("org_board", 20 * 60, "2026-11-13T10:20:00Z"),
      dated("cert_in", 10 * 60, "2026-11-13T10:10:00Z"),
    ];
    expect(breachNextStep(breach({ obligations: certInSooner }))).toMatchObject({
      title: "Open the report to CERT-In",
      then: "Also due: Organisation's board (20 min left)",
    });
    // One already past its time is the one that ran out sooner.
    const certInLate = [
      dated("org_board", 20 * 60, "2026-11-13T10:20:00Z"),
      dated("cert_in", -7200, "2026-11-13T08:00:00Z"),
    ];
    const step = breachNextStep(breach({ obligations: certInLate }));
    expect(step?.title).toBe("Open the report to CERT-In");
    expect(step?.why).toMatch(/^Overdue by 2 h 0 min: it was due /);
    const boardSooner = [
      dated("cert_in", 5 * 3600, "2026-11-13T15:00:00Z"),
      dated("org_board", 20 * 60, "2026-11-13T10:20:00Z"),
    ];
    expect(breachNextStep(breach({ obligations: boardSooner }))?.title).toBe(
      "Notify the organisation's board",
    );
  });

  it("does not let a clock that has run out jump the order: the intimation comes before the report that follows it", () => {
    const step = breachNextStep(
      breach({
        obligations: [
          dated("board_report", -3600, "2026-11-13T09:00:00Z"),
          withoutDelay("principals", true, "2026-11-13T07:00:00Z"),
          withoutDelay("board_intimation"),
        ],
      }),
    );
    expect(step?.title).toBe("Open the initial intimation to the DPDP Board");
    // What has run out is said beside its duty.
    expect(step?.then).toBe(
      "Also due: Principals notified · Board - detailed report (overdue by 1 h 0 min)",
    );
  });

  it("says a duty due without delay has passed the internal target, where one is set", () => {
    const step = breachNextStep(
      breach({ obligations: [withoutDelay("principals", true, "2026-11-13T07:00:00Z")] }),
    );
    expect(step?.title).toBe("Tell the people affected");
    expect(step?.why).toBe(
      "Due without delay: 3 h 0 min since awareness - past the internal target",
    );
  });

  it("passes over a duty that only waits for one the office can act on", () => {
    const step = breachNextStep(
      breach({
        obligations: [dated("org_board", 20 * 60), withoutDelay("board_intimation")],
      }),
      {
        documents: documents(
          kind("org_board", [doc("org_board", "finalised", { mail: queuedTo(2) })]),
          kind("board_intimation"),
        ),
      },
    );
    expect(step).toMatchObject({
      title: "Draft the initial intimation to the DPDP Board",
      go: "reports",
    });
    expect(step?.waiting).toBeUndefined();
    expect(step?.then).toBe("Also due: Organisation's board (20 min left)");
  });

  it("puts a ticket's answer after what the office can do on a duty, and before what is only waited for", () => {
    const board = dated("org_board", 20 * 60);
    const sending = documents(
      kind("org_board", [doc("org_board", "finalised", { mail: queuedTo(1) })]),
    );
    const tickets = [ticket("returned"), ticket("issued")];

    expect(
      breachNextStep(breach({ obligations: [board] }), {
        documents: documents(kind("org_board")),
        tickets,
      })?.title,
    ).toBe("Notify the organisation's board");

    const review = breachNextStep(breach({ obligations: [board] }), {
      documents: sending,
      tickets,
    });
    expect(review).toMatchObject({
      title: "Review the answer on a ticket",
      why: "Close the ticket, or send it back with what is missing.",
      go: "tickets",
    });
    expect(review?.then).toBe("Also due: Organisation's board (20 min left)");

    const waited = breachNextStep(breach({ obligations: [board] }), {
      documents: sending,
      tickets: [ticket("issued")],
    });
    expect(waited).toMatchObject({
      title: "The organisation's board report is on its way",
      waiting: true,
    });
    expect(waited?.then).toBe("Then: the tickets still open, then closing.");
  });
});

/* --------------------------------------------------------- each duty's path */

describe("breachNextStep: the organisation's board", () => {
  const board = dated("org_board", 28 * 60);
  const of = (versions: BreachDocument[], over: Partial<BreachDocumentKindView> = {}) =>
    breachNextStep(breach({ obligations: [board] }), {
      documents: documents(kind("org_board", versions, over)),
    });

  it("offers the report's pop-up from the bar, with the clock", () => {
    const step = of([]);
    expect(step).toMatchObject({
      title: "Notify the organisation's board",
      act: "notify_board",
    });
    expect(step?.why).toMatch(/^28 min left, due /);
    expect(step?.then).toBe("Then: closing.");
  });

  it("says a draft is still to finish", () => {
    expect(of([doc("org_board", "draft")])).toMatchObject({
      title: "Finish the report to the organisation's board",
      act: "notify_board",
    });
  });

  it("waits while the mail is on its way, and says what completes the duty", () => {
    expect(of([doc("org_board", "finalised", { mail: queuedTo(2) })])).toMatchObject({
      title: "The organisation's board report is on its way",
      why: "Its duty completes when the mail lands.",
      go: "reports",
      waiting: true,
    });
  });

  it("sends the reader to Try again when it reached nobody, or reached somebody and left the duty open", () => {
    const failed = of([
      doc("org_board", "finalised", { mail: mail({ failed: 2, retryable: 2 }) }),
    ]);
    expect(failed).toMatchObject({
      title: "The organisation's board report reached nobody",
      go: "reports",
    });
    expect(failed?.why).toMatch(/^Press Try again on the Reports tab\. 28 min left/);
    expect(failed?.act).toBeUndefined();

    const delivered = of([doc("org_board", "finalised", { mail: mail({ delivered: 1 }) })]);
    expect(delivered).toMatchObject({
      title: "Finish the organisation's board report",
      go: "reports",
    });
  });

  it("opens the Reports tab until the reports have been read, or have heard of the duty", () => {
    expect(breachNextStep(breach({ obligations: [board] }))).toMatchObject({
      title: "Notify the organisation's board",
      go: "reports",
    });
    // Read just before the yes: the reports do not know the duty yet, and the
    // board's own button would show nothing. The bar still leads somewhere.
    const behind = of([], { duty_state: null });
    expect(behind).toMatchObject({
      title: "Notify the organisation's board",
      go: "reports",
    });
    expect(behind?.act).toBeUndefined();
  });
});

describe("breachNextStep: a report that goes to a regulator", () => {
  const certIn = dated("cert_in", 5 * 3600);
  const of = (versions: BreachDocument[]) =>
    breachNextStep(breach({ obligations: [certIn] }), {
      documents: documents(kind("cert_in", versions)),
    });

  it("is drafted, finalised, then sent by the office and recorded as sent", () => {
    expect(of([])).toMatchObject({ title: "Draft the report to CERT-In", go: "reports" });
    expect(of([doc("cert_in", "draft")])).toMatchObject({
      title: "Finalise the report to CERT-In",
      go: "reports",
    });
    const sent = of([doc("cert_in", "finalised")]);
    expect(sent?.title).toBe("Send the report to CERT-In yourself, then record it as sent");
    // The three things the record of it asks for.
    expect(sent?.why).toMatch(
      /^The platform does not send to CERT-In: record it with the proof of approval, the mail you sent and the reference returned\. 5 h 0 min left/,
    );
  });

  it("finishes a newer draft before an earlier version is recorded", () => {
    const step = of([
      doc("cert_in", "draft", { version: 2 }),
      doc("cert_in", "finalised", { version: 1 }),
    ]);
    expect(step?.title).toBe("Finalise the report to CERT-In");
  });

  it("names each of the DPDP Board's reports as its card does", () => {
    const step = (duty: BreachDuty, k: BreachDocumentKind, versions: BreachDocument[]) =>
      breachNextStep(breach({ obligations: [duty] }), {
        documents: documents(kind(k, versions)),
      })?.title;
    expect(step(withoutDelay("board_intimation"), "board_intimation", [])).toBe(
      "Draft the initial intimation to the DPDP Board",
    );
    expect(
      step(dated("board_report", 3600), "board_report", [doc("board_report", "finalised")]),
    ).toBe("Send the 72-hour report to the DPDP Board yourself, then record it as sent");
  });

  it("says less until the reports have been read, and never from an answer that is behind", () => {
    expect(
      breachNextStep(breach({ obligations: [withoutDelay("board_intimation")] })),
    ).toMatchObject({
      title: "Open the initial intimation to the DPDP Board",
      why: "Due without delay: 3 h 0 min since awareness",
      go: "reports",
    });
    // The reports were read before the mark: the server blocks no report
    // whose duty stands, so that reason is stale and is not repeated.
    const behind = breachNextStep(breach({ obligations: [certIn] }), {
      documents: documents(
        kind("cert_in", [], { blocked_by: "Mark it reportable to CERT-In first" }),
      ),
    });
    expect(behind?.title).toBe("Open the report to CERT-In");
    expect(behind?.why).toMatch(/^5 h 0 min left, due /);
  });
});

describe("breachNextStep: telling the people affected", () => {
  const people = withoutDelay("principals");
  const NOW = Date.parse("2026-11-13T10:10:00Z");
  const of = (n?: BreachNotices, reread = false) =>
    breachNextStep(breach({ obligations: [people] }), {
      notices: n,
      now: NOW,
      peopleDutyReread: reread,
    });
  const queuedAt = (version: number, last_at: string, n = 2) => ({
    notice_uuid: `n${version}`,
    version,
    channel: "email" as const,
    status: "queued" as const,
    people: n,
    last_at,
  });

  it("lists them, drafts the notice, approves it, then sends it", () => {
    expect(of()).toMatchObject({ title: "Tell the people affected", go: "people" });
    expect(of(notices({ listed: 0, unnotified: 0 }))).toMatchObject({
      title: "List the people affected",
      go: "people",
    });
    expect(of(notices())).toMatchObject({
      title: "Draft the notice to the people affected",
      go: "people",
    });
    expect(of(notices({ versions: [notice("draft")] }))).toMatchObject({
      title: "Approve the notice to the people affected",
      go: "people",
    });
    const send = of(notices({ versions: [notice("approved")] }));
    expect(send).toMatchObject({
      title: "Send the notice to the people affected",
      go: "people",
    });
    expect(send?.why).toMatch(/^3 of the 3 listed have not been told\. Due without delay/);
    expect(send?.waiting).toBeUndefined();
  });

  it("says how many are still to be told, not how many the send will mail", () => {
    // A send mails a new version to everyone listed, so the step names who is
    // waiting and leaves the count on the button to the card.
    const step = of(
      notices({
        versions: [notice("approved", 1), notice("approved", 2)],
        listed: 5,
        unnotified: 1,
      }),
    );
    expect(step?.title).toBe("Send the notice to the people affected");
    expect(step?.why).toMatch(/^1 of the 5 listed has not been told\./);
  });

  it("sends the approved version while an update to it is still a draft", () => {
    expect(
      of(notices({ versions: [notice("approved", 1), notice("draft", 2)] }))?.title,
    ).toBe("Send the notice to the people affected");
  });

  it("waits while deliveries are going out, and says tried, not reached", () => {
    // A delivery that failed after its retries has its outcome too.
    const going = of(
      notices({
        versions: [notice("approved")],
        unnotified: 2,
        account: [queuedAt(1, "2026-11-13T10:08:00Z")],
      }),
    );
    expect(going).toMatchObject({
      title: "The notice to the people affected is going out",
      why: "Every delivery to 1 of the 3 listed has been tried so far.",
      go: "people",
      waiting: true,
    });
    const failing = of(
      notices({
        versions: [notice("approved")],
        unnotified: 2,
        account: [queuedAt(1, "2026-11-13T10:08:00Z")],
        failures: [{ version: 1 } as BreachNotices["failures"][number]],
      }),
    );
    expect(failing?.why).toBe(
      "Every delivery to 1 of the 3 listed has been tried so far. Some failed: see People & notices.",
    );
  });

  it("asks for a send when a queue has not moved for a quarter of an hour", () => {
    // Lost before the worker saw them: nothing but a send queues them again.
    const lost = of(
      notices({
        versions: [notice("approved")],
        unnotified: 2,
        account: [queuedAt(1, "2026-11-13T09:50:00Z")],
      }),
    );
    expect(lost?.title).toBe("Send the notice again");
    expect(lost?.why).toMatch(
      /^Deliveries queued more than 15 minutes ago did not go: sending again queues them once more\./,
    );
    expect(lost?.waiting).toBeUndefined();
    // One still moving is waited for.
    const moving = of(
      notices({
        versions: [notice("approved")],
        unnotified: 2,
        account: [
          queuedAt(1, "2026-11-13T09:50:00Z"),
          { ...queuedAt(1, "2026-11-13T10:09:00Z"), channel: "sms" as const },
        ],
      }),
    );
    expect(moving?.waiting).toBe(true);
  });

  it("does not take an older version's queue for this one's", () => {
    const step = of(
      notices({
        versions: [notice("approved", 1), notice("approved", 2)],
        account: [queuedAt(1, "2026-11-13T10:09:00Z", 1)],
      }),
    );
    expect(step?.title).toBe("Send the notice to the people affected");
  });

  it("once everyone has been told, waits only until the breach has been read again", () => {
    const everyone = notices({ versions: [notice("approved")], unnotified: 0 });
    expect(of(everyone)).toMatchObject({
      title: "The notice to the people affected has gone out",
      why: "Checking that its duty has completed.",
      waiting: true,
    });
    // Read again and the duty still stands: no delivery completes it now - a
    // yes brought it back after everybody had been told - and a send does.
    const back = of(everyone, true);
    expect(back).toMatchObject({
      title: "Send the notice again to complete this duty",
      go: "people",
    });
    expect(back?.why).toMatch(/Send completes it, and tells nobody twice\.$/);
    expect(back?.waiting).toBeUndefined();
  });
});

/* ------------------------------------------------------- tickets and closing */

describe("breachNextStep: tickets, then closing", () => {
  it("reviews answers, and otherwise waits for the holders", () => {
    expect(
      breachNextStep(breach(), { tickets: [ticket("returned"), ticket("returned", true)] }),
    ).toMatchObject({
      title: "Review the answers on 2 tickets",
      go: "tickets",
      then: "Then: closing.",
    });
    expect(
      breachNextStep(breach(), {
        tickets: [ticket("issued"), ticket("issued", true), ticket("closed")],
      }),
    ).toMatchObject({
      title: "Waiting for 2 tickets to be answered",
      why: "1 past its resolve-by date.",
      go: "tickets",
      waiting: true,
    });
    expect(breachNextStep(breach(), { tickets: [ticket("issued")] })).toMatchObject({
      title: "Waiting for a ticket to be answered",
      why: null,
    });
  });

  it("offers the close once the server allows it", () => {
    expect(
      breachNextStep(breach({ transitions: CLOSABLE }), {
        tickets: [ticket("closed"), ticket("withdrawn")],
      }),
    ).toMatchObject({
      title: "Ready to close",
      why: "Every duty is done or set aside, and no ticket is open.",
      act: "close",
    });
    expect(
      breachNextStep(
        breach({
          transitions: CLOSABLE,
          determination: "no",
          breach_reference: null,
          reference: "INC-2026-0042",
        }),
      ),
    ).toMatchObject({
      title: "Ready to close",
      why: "It is not a personal data breach, and nothing is left open on it.",
      then: null,
    });
  });

  it("says a word about the optional closure report before closing", () => {
    const closing = (versions: BreachDocument[], b: Partial<Breach> = {}) =>
      breachNextStep(breach({ transitions: CLOSABLE, ...b }), {
        documents: documents(kind("closure", versions)),
      })?.then;
    expect(closing([])).toBe(
      "A closure report is optional: draft it under Reports first if one is wanted.",
    );
    expect(closing([doc("closure", "draft")])).toBe(
      "The closure report is still a draft: finalise it first, or close without it.",
    );
    expect(closing([doc("closure", "finalised")])).toMatch(
      /finalised and not yet recorded as sent/,
    );
    expect(closing([doc("closure", "filed")])).toBeNull();
    // An incident that was never a breach has no closure report to write.
    expect(closing([], { breach_reference: null, determination: "no" })).toBeNull();
  });

  it("points at the Close card when the server names something this page has not read", () => {
    expect(breachNextStep(breach())).toMatchObject({
      title: "Clear what still stands in the way of closing",
      why: "The list is under Close, below.",
    });
  });
});

/* -------------------------------------------------------------------- the bar */

function serve(over: { reports?: BreachDocuments; notices?: BreachNotices } = {}) {
  server.use(
    http.get(`${API}/breaches/${UUID}/reports`, () =>
      HttpResponse.json(over.reports ?? documents()),
    ),
    http.get(`${API}/breaches/${UUID}/notices`, () =>
      HttpResponse.json(over.notices ?? notices()),
    ),
  );
}

beforeEach(() => vi.clearAllMocks());

describe("BreachNextBar", () => {
  it("names the step from what the cards have read, and opens the tab it is made on", async () => {
    serve({ reports: documents(kind("cert_in", [doc("cert_in", "draft")])) });
    const onGo = vi.fn();
    const { user } = render(
      <BreachNextBar
        breach={breach({ obligations: [dated("cert_in", 5 * 3600)] })}
        tickets={[]}
        tab="duties"
        onGo={onGo}
      />,
    );
    const bar = screen.getByRole("region", { name: "Next step" });
    // Said in less detail until the reports are in.
    expect(bar).toHaveTextContent("Open the report to CERT-In");
    expect(
      await within(bar).findByText("Finalise the report to CERT-In"),
    ).toBeInTheDocument();
    expect(bar).toHaveTextContent("5 h 0 min left, due");
    expect(bar).toHaveTextContent("Then: closing.");

    await user.click(within(bar).getByRole("button", { name: "Go to Reports" }));
    expect(onGo).toHaveBeenCalledWith("reports");
  });

  it("has no button to a tab that is already open", async () => {
    serve({ reports: documents(kind("cert_in")) });
    render(
      <BreachNextBar
        breach={breach({ obligations: [dated("cert_in", 3600)] })}
        tickets={[]}
        tab="reports"
        onGo={vi.fn()}
      />,
    );
    const bar = screen.getByRole("region", { name: "Next step" });
    expect(await within(bar).findByText("Draft the report to CERT-In")).toBeInTheDocument();
    expect(within(bar).queryByRole("button")).not.toBeInTheDocument();
  });

  it("offers the board's own button while that duty is the step", async () => {
    serve({ reports: documents(kind("org_board")) });
    render(
      <BreachNextBar
        breach={breach({ obligations: [dated("org_board", 28 * 60)] })}
        tickets={[]}
        tab="duties"
        onGo={vi.fn()}
      />,
    );
    const bar = screen.getByRole("region", { name: "Next step" });
    expect(
      await within(bar).findByRole("button", { name: "Notify Organization Board" }),
    ).toBeInTheDocument();
    expect(bar).toHaveTextContent("Notify the organisation's board - 28 min left, due");
    expect(within(bar).queryByRole("button", { name: /Go to/ })).not.toBeInTheDocument();
  });

  it("closes from the bar only after the same question the Close card asks", async () => {
    serve();
    const sent: unknown[] = [];
    server.use(
      http.post(`${API}/breaches/${UUID}/transition`, async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json(breach({ status: "closed" }));
      }),
    );
    const { user } = render(
      <BreachNextBar
        breach={breach({ transitions: CLOSABLE })}
        tickets={[]}
        tab="duties"
        onGo={vi.fn()}
      />,
    );
    const bar = screen.getByRole("region", { name: "Next step" });
    expect(bar).toHaveTextContent(
      "Ready to close - Every duty is done or set aside, and no ticket is open.",
    );

    await user.click(within(bar).getByRole("button", { name: "Close BR-2026-0042" }));
    const question = await screen.findByRole("dialog", { name: "Close BR-2026-0042?" });
    expect(sent).toEqual([]);
    await user.click(within(question).getByRole("button", { name: "Close the breach" }));
    await vi.waitFor(() => expect(sent).toEqual([{ to: "closed", reason: null }]));
    expect(toast.success).toHaveBeenCalledWith("Breach closed");
  });

  it("is not there for a closed breach", () => {
    serve();
    render(
      <BreachNextBar
        breach={breach({ status: "closed" })}
        tickets={[]}
        tab="duties"
        onGo={vi.fn()}
      />,
    );
    expect(screen.queryByRole("region", { name: "Next step" })).not.toBeInTheDocument();
  });

  it("reads the breach again once the notices say everyone listed has been told", async () => {
    // The worker completes that duty and tells nobody.
    serve({ notices: notices({ versions: [notice("approved")], unnotified: 0 }) });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const people = breach({ obligations: [withoutDelay("principals")] });
    queryClient.setQueryData(keys.breach.detail(UUID), people);
    render(<BreachNextBar breach={people} tickets={[]} tab="duties" onGo={vi.fn()} />, {
      queryClient,
    });
    expect(queryClient.getQueryState(keys.breach.detail(UUID))?.isInvalidated).toBe(false);
    await vi.waitFor(() =>
      expect(queryClient.getQueryState(keys.breach.detail(UUID))?.isInvalidated).toBe(true),
    );
    // Read again, and the duty this bar was given still stands: a send is
    // what completes it now.
    expect(
      await screen.findByText("Send the notice again to complete this duty"),
    ).toBeInTheDocument();
  });

  it("keeps a report being written from the bar when the step moves on", async () => {
    const draft = doc("org_board", "draft", {
      report_uuid: "rep-1",
      title: "Report to the organisation's board",
      sections: [
        {
          key: "what_happened",
          label: "What happened",
          required: true,
          body: "A list was exposed",
        },
      ],
    });
    serve({ reports: documents(kind("org_board", [draft]), kind("cert_in")) });
    server.use(
      http.get(`${API}/breaches/${UUID}/reports/recipients`, () =>
        HttpResponse.json({ recipients: [] }),
      ),
    );
    const board = dated("org_board", 20 * 60, "2026-11-13T10:20:00Z");
    const certIn = dated("cert_in", 5 * 3600, "2026-11-13T15:00:00Z");
    const { user, rerender } = render(
      <BreachNextBar
        breach={breach({ obligations: [board, certIn] })}
        tickets={[]}
        tab="duties"
        onGo={vi.fn()}
      />,
    );
    const bar = screen.getByRole("region", { name: "Next step" });
    expect(
      await within(bar).findByText("Finish the report to the organisation's board"),
    ).toBeInTheDocument();
    await user.click(
      within(bar).getByRole("button", { name: "Notify Organization Board" }),
    );
    const editor = await screen.findByRole("dialog");
    await user.type(within(editor).getByLabelText(/What happened/), " to a vendor");

    // Another officer's write: the board's duty is done, and CERT-In is next.
    rerender(
      <BreachNextBar
        breach={breach({ obligations: [{ ...board, state: "done" }, certIn] })}
        tickets={[]}
        tab="duties"
        onGo={vi.fn()}
      />,
    );
    expect(await within(bar).findByText("Draft the report to CERT-In")).toBeInTheDocument();
    expect(
      within(bar).queryByRole("button", { name: "Notify Organization Board" }),
    ).not.toBeInTheDocument();
    // The window, and what was typed into it, are still there.
    expect(within(screen.getByRole("dialog")).getByLabelText(/What happened/)).toHaveValue(
      "A list was exposed to a vendor",
    );
  });
});
