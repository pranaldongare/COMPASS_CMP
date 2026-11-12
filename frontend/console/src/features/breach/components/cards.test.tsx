/**
 * The Duties card: what each duty offers, as the server's answer allows it.
 *
 * A CERT-In mark that was a mistake can be set aside whatever validation says,
 * with a reason and a mail to nobody, and marked again later. The board's duty
 * row keeps an open editor through a change of duty. A yes after a no names
 * the duties it found already done.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DeterminationCard, DutiesCard } from "@/features/breach/components/cards";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachDocuments, BreachDuty, BreachDutyEvent } from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const BREACH = "66666666-6666-4666-8666-666666666666";
const ACTION = "Not reportable to CERT-In";

const duty = (over: Partial<BreachDuty> = {}): BreachDuty => ({
  obligation_uuid: "77777777-7777-4777-8777-777777777777",
  duty: "cert_in",
  label: "Report to CERT-In",
  basis: "CERT-In Directions 2022",
  created_at: "2026-11-06T09:00:00Z",
  state: "outstanding",
  due_at: "2026-11-06T15:00:00Z",
  anchored_at: "2026-11-06T09:00:00Z",
  completed_at: null,
  reference: null,
  reported_to: null,
  extended_until: null,
  extension_requested_at: null,
  clock: {
    without_delay: false,
    seconds_remaining: 600,
    overdue: false,
    seconds_elapsed: 1200,
    target_at: null,
    past_target: false,
  },
  events: [],
  ...over,
});

const breach = (over: Partial<Breach> = {}) =>
  ({
    breach_uuid: BREACH,
    status: "open",
    reference: "INC-2026-0042",
    breach_reference: null,
    determination: "no",
    without_delay_target_hours: null,
    obligations: [duty()],
    ...over,
  }) as Breach;

const setAside = (note: string | null): BreachDutyEvent => ({
  event_uuid: crypto.randomUUID(),
  kind: "not_applicable",
  occurred_at: null,
  reference: null,
  note,
  reported_to: null,
  due_at: null,
  requested_at: null,
  determination_uuid: "88888888-8888-4888-8888-888888888888",
  recorded_at: "2026-11-06T12:00:00Z",
  recorded_by_name: "Priya Menon",
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("setting CERT-In aside", () => {
  // "pending" is what the breach says before any validation, too.
  it.each(["no", "yes", "pending"] as const)(
    "is offered whenever the duty stands, whatever validation says (%s)",
    (determination) => {
      render(<DutiesCard breach={breach({ determination })} />);

      const row = screen.getByRole("row", { name: /Report to CERT-In/ });
      expect(within(row).getByRole("button", { name: ACTION })).toBeInTheDocument();
    },
  );

  it("is not offered in any state the server would refuse", () => {
    const cases: Partial<Breach>[] = [
      { status: "closed" },
      { obligations: [duty({ state: "done" })] },
      { obligations: [duty({ state: "not_applicable" })] },
      { obligations: [duty({ duty: "board_intimation", label: "Initial intimation" })] },
    ];
    for (const over of cases) {
      const { unmount } = render(<DutiesCard breach={breach(over)} />);
      expect(screen.queryByRole("button", { name: ACTION })).not.toBeInTheDocument();
      unmount();
    }
  });

  it("says what it does and that it mails nobody, and needs a reason", async () => {
    let sent: unknown = null;
    server.use(
      http.post(`${API}/breaches/${BREACH}/cert-in/not-applicable`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(breach({ obligations: [duty({ state: "not_applicable" })] }));
      }),
    );
    const { user } = render(<DutiesCard breach={breach()} />);

    await user.click(screen.getByRole("button", { name: ACTION }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/no longer holds up closing/)).toBeInTheDocument();
    expect(within(dialog).getByText(/It mails nobody/)).toBeInTheDocument();
    expect(within(dialog).getByText(/whatever validation says/)).toBeInTheDocument();
    expect(within(dialog).queryByText(/validated as No/)).not.toBeInTheDocument();

    const go = within(dialog).getByRole("button", { name: "Mark as not reportable" });
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/reason it is not reportable/i), "   ");
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/reason it is not reportable/i), "A false alarm from the scanner  ");
    await user.click(go);

    await vi.waitFor(() => expect(sent).toEqual({ reason: "A false alarm from the scanner" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.success).toHaveBeenCalledWith("CERT-In set aside", expect.stringContaining("Nobody was mailed"));
  });

  it("warns that a report to CERT-In waiting for a yes is not mailed while it stays set aside", async () => {
    const { user } = render(<DutiesCard breach={breach({ determination: "pending" })} />);

    await user.click(screen.getByRole("button", { name: ACTION }));
    const dialog = await screen.findByRole("dialog");

    expect(
      within(dialog).getByText(
        /A report to CERT-In still waiting for a yes to be mailed to the board is not mailed while it stays set aside\./,
      ),
    ).toBeInTheDocument();
  });

  it("shows the server's sentence and keeps the reason when it is refused", async () => {
    const sentence = "A report to CERT-In has been filed, so it stands";
    server.use(
      http.post(`${API}/breaches/${BREACH}/cert-in/not-applicable`, () =>
        HttpResponse.json({ error: { code: "report_filed", message: sentence } }, { status: 409 }),
      ),
    );
    const { user } = render(<DutiesCard breach={breach()} />);

    await user.click(screen.getByRole("button", { name: ACTION }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/reason it is not reportable/i), "A false alarm");
    await user.click(within(dialog).getByRole("button", { name: "Mark as not reportable" }));

    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith("Not set aside", sentence));
    expect(within(dialog).getByLabelText(/reason it is not reportable/i)).toHaveValue("A false alarm");
  });

  it("shows why it was set aside on the row", () => {
    render(
      <DutiesCard
        breach={breach({
          obligations: [
            duty({ state: "not_applicable", events: [setAside("An earlier reason"), setAside("A false alarm")] }),
          ],
        })}
      />,
    );

    const row = screen.getByRole("row", { name: /Report to CERT-In/ });
    expect(within(row).getByText("A false alarm")).toBeInTheDocument();
    expect(within(row).queryByText("An earlier reason")).not.toBeInTheDocument();
  });

  it("offers Mark again once it is set aside, and says the duty is back", async () => {
    let marked = false;
    server.use(
      http.post(`${API}/breaches/${BREACH}/cert-in`, () => {
        marked = true;
        return HttpResponse.json(breach());
      }),
    );
    const { user } = render(<DutiesCard breach={breach({ obligations: [duty({ state: "not_applicable" })] })} />);

    await user.click(screen.getByRole("button", { name: "Mark reportable to CERT-In" }));

    await vi.waitFor(() => expect(marked).toBe(true));
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("CERT-In duty reinstated", expect.any(String)));
  });

  it("offers no Mark while the duty stands or is done", () => {
    for (const state of ["outstanding", "done"] as const) {
      const { unmount } = render(<DutiesCard breach={breach({ obligations: [duty({ state })] })} />);
      expect(screen.queryByRole("button", { name: "Mark reportable to CERT-In" })).not.toBeInTheDocument();
      unmount();
    }
  });

  it("says a first mark creates the duty", async () => {
    server.use(http.post(`${API}/breaches/${BREACH}/cert-in`, () => HttpResponse.json(breach())));
    const { user } = render(<DutiesCard breach={breach({ obligations: [] })} />);

    await user.click(screen.getByRole("button", { name: "Mark reportable to CERT-In" }));

    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("CERT-In duty created", expect.any(String)));
  });
});

describe("the board's duty", () => {
  const SECTION = { key: "what_happened", label: "What happened", required: true, body: "A list" };
  const documents = {
    kinds: [
      {
        kind: "org_board",
        title: "Report to the organisation's board",
        basis: "Internal policy",
        duty: "org_board",
        duty_state: "outstanding",
        blocked_by: null,
        goes_to_regulator: false,
        holds_mail: false,
        versions: [
          {
            report_uuid: "99999999-9999-4999-8999-999999999999",
            kind: "org_board",
            title: "Report to the organisation's board",
            version: 1,
            state: "draft",
            superseded: false,
            sections: [SECTION],
            evidence: [],
            mail: { delivered: 0, queued: 0, failed: 0, unsent: 0, held: 0, stale: 0, retryable: 0, recipients: [] },
          },
        ],
      },
    ],
    board_recipients: 2,
    proofs: [],
  } as unknown as BreachDocuments;
  const board = (state: BreachDuty["state"]) =>
    breach({
      determination: "yes",
      breach_reference: "BR-2026-0042",
      obligations: [duty({ duty: "org_board", label: "Report to the organisation's board", state })],
    });

  it("keeps an open editor through a colleague's No", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () => HttpResponse.json(documents)),
      http.get(`${API}/breaches/${BREACH}/reports/recipients`, () => HttpResponse.json({ recipients: [] })),
    );
    const { user, rerender } = render(<DutiesCard breach={board("outstanding")} />);

    await user.click(await screen.findByRole("button", { name: "Notify Organization Board" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/what happened/i), ", typed");

    rerender(<DutiesCard breach={board("not_applicable")} />);

    expect(within(screen.getByRole("dialog")).getByLabelText(/what happened/i)).toHaveValue("A list, typed");
    expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
  });
});

describe("validation", () => {
  const recorded = (obligations: BreachDuty[]) =>
    breach({ determination: "no", breach_reference: "BR-2026-0042", determinations: [], obligations });
  const board = (state: BreachDuty["state"]) =>
    duty({ duty: "org_board", label: "Report to the organisation's board", state });
  const intimation = (state: BreachDuty["state"]) =>
    duty({ duty: "board_intimation", label: "Board - initial intimation", state });

  async function validateYes(before: Breach, after: Breach) {
    server.use(http.post(`${API}/breaches/${BREACH}/determinations`, () => HttpResponse.json(after)));
    const { user } = render(<DeterminationCard breach={before} />);
    await user.type(screen.getByLabelText(/^Became aware at/), "2026-11-06T09:30");
    await user.type(screen.getByLabelText(/^Reasoning/), "Names were exposed after all");
    await user.click(screen.getByRole("button", { name: "Record the validation" }));
  }

  it("names the duties a later yes found already done, and says nothing was sent again", async () => {
    await validateYes(
      recorded([board("not_applicable"), intimation("not_applicable"), duty()]),
      recorded([board("done"), intimation("done"), duty()]),
    );

    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Validation recorded",
        "A personal data breach. Done while it was set aside, so done now: Report to the organisation's board; Board - initial intimation. Nobody was mailed.",
      ),
    );
  });

  it("names only those that went from set aside to done", async () => {
    await validateYes(
      recorded([board("not_applicable"), intimation("not_applicable"), duty({ state: "done" })]),
      recorded([board("outstanding"), intimation("done"), duty({ state: "done" })]),
    );

    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Validation recorded",
        "A personal data breach. Done while it was set aside, so done now: Board - initial intimation. Nobody was mailed.",
      ),
    );
  });

  it("claims for a yes after a no only what the server completes", () => {
    render(<DeterminationCard breach={recorded([board("not_applicable")])} />);

    expect(screen.queryByText(/done already where the work was done meanwhile/)).not.toBeInTheDocument();
    expect(screen.getByText(/That yes finds done only the duty to tell the organisation's board/)).toBeInTheDocument();
    // From a report that has run its course: one still sending is passed over.
    expect(
      screen.getByText(/if a report to it has run its course and reached somebody meanwhile \(one still sending is passed over\)/),
    ).toBeInTheDocument();
    expect(screen.getByText(/The notice to the people affected is not done by it/)).toBeInTheDocument();
    expect(screen.getByText(/A no leaves the CERT-In duty as it is/)).toBeInTheDocument();
  });

  it("says no more than the outcome when a yes found nothing done", async () => {
    await validateYes(recorded([board("not_applicable")]), recorded([board("outstanding")]));

    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Validation recorded", "A personal data breach"));
  });
});
