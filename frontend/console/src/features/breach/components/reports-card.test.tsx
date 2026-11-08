/**
 * The reports on a breach (0059, ADR 0037): a draft from the register, finalised
 * once every required section says something, to whoever the sender chose from
 * the board's list and anyone added for that report alone (0064); then, for a
 * regulator's report, recorded as sent with both proofs, on whichever finalised
 * version was the one sent. The platform sends nothing to a regulator, and
 * nothing here pretends otherwise. The board's own report is done when its mail
 * lands: the button says what the mail is doing until then. A report to
 * CERT-In finalised before the incident is recorded is held for the first yes,
 * and its line says so, or why it never went. Try again is offered where the
 * server says sending again would do something, reaches only the addresses a
 * version went to, and a press says what it did.
 */
import { QueryClient } from "@tanstack/react-query";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NotifyBoardButton, ReportsCard } from "@/features/breach/components/reports-card";
import { keys } from "@/lib/query";
import { makeMe } from "@/test/fixtures";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type {
  Breach,
  BreachBoardEntry,
  BreachDocument,
  BreachDocumentKindView,
  BreachDocumentMail,
  BreachDocumentMailRecipient,
  BreachDocumentProof,
  BreachDocuments,
  BreachDuty,
  Me,
} from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }));
const auth = vi.hoisted(() => ({ me: null as Me | null }));
vi.mock("@/providers", () => ({ useToast: () => toast }));
vi.mock("@/providers/auth-provider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/providers/auth-provider")>()),
  useOptionalAuth: () => ({ me: auth.me }),
}));

const BREACH = "66666666-6666-4666-8666-666666666666";
const REPORT = "77777777-7777-4777-8777-777777777777";
const NEWER = "88888888-8888-4888-8888-888888888888";
const CHAIR = "11111111-1111-4111-8111-111111111111";
const DEPUTY = "22222222-2222-4222-8222-222222222222";

const breach = (over: Partial<Breach> = {}) =>
  ({ breach_uuid: BREACH, status: "open", reference: "BR-2026-0007", obligations: [], ...over }) as Breach;

const mail = (over: Partial<BreachDocumentMail> = {}): BreachDocumentMail => ({
  delivered: 0,
  queued: 0,
  failed: 0,
  unsent: 0,
  held: 0,
  stale: 0,
  retryable: 0,
  recipients: [],
  ...over,
});

const address = (over: Partial<BreachDocumentMailRecipient> = {}): BreachDocumentMailRecipient => ({
  recipient_uuid: crypto.randomUUID(),
  full_name: "Meera Iyer",
  email: "meera@cmp.local",
  status: "delivered",
  attempt: 1,
  error: null,
  recorded_at: "2026-11-06T10:01:00Z",
  removed: false,
  mandatory: false,
  added_for_this_send: false,
  ...over,
});

/** An entry on the board's list, as the finalise window reads it. */
const entry = (over: Partial<BreachBoardEntry> = {}): BreachBoardEntry => ({
  recipient_uuid: CHAIR,
  full_name: "Asha Rao",
  email: "chair@cmp.local",
  mandatory: false,
  ...over,
});

const BOARD = [entry(), entry({ recipient_uuid: DEPUTY, full_name: null, email: "deputy@cmp.local" })];

const proofOf = (kind: "approval" | "sent_mail", over: Partial<BreachDocumentProof> = {}): BreachDocumentProof => ({
  attachment_uuid: crypto.randomUUID(),
  kind,
  note: null,
  file_name: `${kind}.pdf`,
  sha256: "a".repeat(64),
  size_bytes: 8,
  added_at: "2026-11-06T11:00:00Z",
  added_by_name: "Priya Menon",
  ...over,
});

const document = (over: Partial<BreachDocument> = {}): BreachDocument => ({
  report_uuid: REPORT,
  kind: "board_intimation",
  title: "Initial intimation to the DPDP Board",
  version: 1,
  state: "draft",
  superseded: false,
  sections: [
    { key: "nature_extent", label: "The nature and extent of the breach", required: true, body: "A list was exposed" },
    { key: "likely_impact", label: "Its likely impact", required: true, body: null },
  ],
  created_at: "2026-11-06T09:00:00Z",
  created_by_name: "Priya Menon",
  updated_at: "2026-11-06T09:00:00Z",
  finalised_at: null,
  finalised_by_name: null,
  filed_at: null,
  filed_reference: null,
  filed_by_name: null,
  evidence: [],
  mail: mail(),
  ...over,
});

const pdf = (name: string) => new File(["%PDF-1.4"], name, { type: "application/pdf" });

const FINALISED = {
  state: "finalised",
  finalised_at: "2026-11-06T10:00:00Z",
  finalised_by_name: "Priya Menon",
  mail: mail({ delivered: 2 }),
} as const;

const FULL = [{ key: "nature_extent", label: "Nature", required: true, body: "Written" }];

const view = (over: Partial<BreachDocumentKindView> = {}): BreachDocumentKindView => ({
  kind: "board_intimation",
  title: "Initial intimation to the DPDP Board",
  basis: "Rule 7(2)(a)",
  duty: "board_intimation",
  duty_state: "outstanding",
  blocked_by: null,
  goes_to_regulator: true,
  holds_mail: false,
  versions: [],
  ...over,
});

const boardView = (over: Partial<BreachDocumentKindView> = {}) =>
  view({
    kind: "org_board",
    title: "Report to the organisation's board",
    basis: "Internal policy",
    duty: "org_board",
    goes_to_regulator: false,
    ...over,
  });

const documents = (kinds: BreachDocumentKindView[], recipients = 2): BreachDocuments => ({
  kinds,
  board_recipients: recipients,
  proofs: [
    { kind: "approval", label: "Proof of internal approval" },
    { kind: "sent_mail", label: "The mail sent to the regulator" },
  ],
});

const dutyOf = (over: Partial<BreachDuty>) => ({ duty: "org_board", state: "outstanding", ...over }) as BreachDuty;

/** The reports as they stand, for the reads that follow a write, and the
 *  board's list the finalise window reads beside them. */
function serve(initial: BreachDocuments, board: BreachBoardEntry[] = BOARD) {
  const world = { now: initial, board, boardReads: 0 };
  server.use(
    http.get(`${API}/breaches/${BREACH}/reports`, () => HttpResponse.json(world.now)),
    http.get(`${API}/breaches/${BREACH}/reports/recipients`, () => {
      world.boardReads += 1;
      return HttpResponse.json({ recipients: world.board });
    }),
  );
  return world;
}

const multipart = (body: string, name: string) =>
  new RegExp(`name="${name}"\r\n\r\n([^\r]*)`).exec(body)?.[1] ?? null;

/** A poll that has just come back. */
async function polled(queryClient: QueryClient) {
  await act(async () => {
    await queryClient.refetchQueries({ queryKey: keys.breach.reports(BREACH) });
    // The query tells the screen on the next turn of the loop.
    await new Promise((resolve) => setTimeout(resolve, 10));
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.me = null;
});

describe("ReportsCard", () => {
  it("starts a draft from the register and opens it", async () => {
    const world = serve(documents([view()]));
    let kind: unknown = null;
    server.use(
      http.post(`${API}/breaches/${BREACH}/reports`, async ({ request }) => {
        kind = await request.json();
        world.now = documents([view({ versions: [document()] })]);
        return HttpResponse.json(world.now, { status: 201 });
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Draft it" }));

    const dialog = await screen.findByRole("dialog");
    expect(kind).toEqual({ kind: "board_intimation" });
    expect(within(dialog).getByLabelText(/nature and extent/i)).toHaveValue("A list was exposed");
    expect(within(dialog).getByText(/it does not go to the regulator/i)).toBeInTheDocument();
  });

  it("says why a report must wait, in the server's words", async () => {
    serve(
      documents([
        view({ kind: "cert_in", blocked_by: "Mark it reportable to CERT-In first", duty_state: null }),
      ]),
    );
    render(<ReportsCard breach={breach()} />);

    expect(await screen.findByText("Mark it reportable to CERT-In first.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Draft it" })).toBeDisabled();
  });

  describe("once CERT-In has been set aside", () => {
    const SET_ASIDE = "CERT-In was set aside as not reportable. Mark it reportable again first";
    // As the server serves it: the CERT-In duty, which a person set aside.
    const certIn = (versions: BreachDocument[]) =>
      documents([
        view({
          kind: "cert_in",
          title: "Report to CERT-In",
          duty: "cert_in",
          duty_state: "not_applicable",
          blocked_by: SET_ASIDE,
          versions,
        }),
      ]);

    it("will not finalise a draft left open, and says why on the row and in the window", async () => {
      serve(certIn([document({ kind: "cert_in", sections: FULL })]));
      const { user } = render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(`${SET_ASIDE}.`)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Continue the draft" }));

      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByText(`${SET_ASIDE}.`)).toBeInTheDocument();
      expect(within(dialog).getByRole("button", { name: "Finalise and tell the board" })).toBeDisabled();
      expect(within(dialog).getByLabelText(/Nature/)).toBeEnabled();
    });

    it("offers no Record as sent, which the server would refuse, and says what comes first", async () => {
      serve(certIn([document({ ...FINALISED, kind: "cert_in" })]));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(`${SET_ASIDE}.`)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Record as sent" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "New version" })).toBeDisabled();
    });

    it.each([
      ["a report", [document({ ...FINALISED, kind: "cert_in" })]],
      ["no report", []],
    ])("says nothing of it on a closed breach with %s, where nothing can be done", async (_, versions) => {
      serve(certIn(versions));
      render(<ReportsCard breach={breach({ status: "closed" })} />);

      await screen.findByTestId("report-cert_in");
      expect(screen.queryByText(`${SET_ASIDE}.`)).not.toBeInTheDocument();
    });

    it("keeps an open Record as sent and what was typed in it, and picks up when the mark is made again", async () => {
      const finalised = [document({ ...FINALISED, kind: "cert_in", evidence: [proofOf("sent_mail")] })];
      const free = () =>
        documents([view({ kind: "cert_in", title: "Report to CERT-In", duty: "cert_in", versions: finalised })]);
      const world = serve(free());
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      const { user } = render(<ReportsCard breach={breach()} />, { queryClient });

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      const record = within(dialog).getByRole("button", { name: "Record as sent" });
      const later = within(dialog).getByRole("button", { name: "Attach and finish later" });
      await user.upload(within(dialog).getByLabelText(/^proof of internal approval/i), pdf("approval.pdf"));
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T10:30");
      await user.type(within(dialog).getByLabelText(/Reference returned/), "CERT/7");
      expect(record).toBeEnabled();
      expect(later).toBeEnabled();

      world.now = certIn(finalised);
      await polled(queryClient);

      expect(screen.getByRole("dialog")).toBe(dialog);
      expect(within(dialog).getByLabelText(/Reference returned/)).toHaveValue("CERT/7");
      expect(within(dialog).getByText(`${SET_ASIDE}.`)).toBeInTheDocument();
      // Set aside by a person, not a No, and no Yes brings it back.
      expect(within(dialog).queryByText("This duty is set aside while the No stands")).not.toBeInTheDocument();
      expect(within(dialog).queryByText(/completes the duty at the next Yes/)).not.toBeInTheDocument();
      expect(record).toBeDisabled();
      expect(later).toBeDisabled();

      world.now = free();
      await polled(queryClient);

      expect(screen.getByRole("dialog")).toBe(dialog);
      expect(within(dialog).queryByText(`${SET_ASIDE}.`)).not.toBeInTheDocument();
      expect(within(dialog).getByLabelText(/Reference returned/)).toHaveValue("CERT/7");
      expect(record).toBeEnabled();
      expect(later).toBeEnabled();
    });

    it("does not open Record as sent by itself when the mark is made again", async () => {
      const finalised = [document({ ...FINALISED, kind: "cert_in" })];
      const world = serve(certIn(finalised));
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      render(<ReportsCard breach={breach()} />, { queryClient });
      await screen.findByText(`${SET_ASIDE}.`);

      world.now = documents([view({ kind: "cert_in", title: "Report to CERT-In", duty: "cert_in", versions: finalised })]);
      await polled(queryClient);

      expect(await screen.findByRole("button", { name: "Record as sent" })).toBeInTheDocument();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("takes each section up to the API's limit, and says when it stops there", async () => {
    const full = document({
      sections: [
        { key: "nature_extent", label: "Nature", required: true, body: "x".repeat(20_000) },
        { key: "likely_impact", label: "Impact", required: true, body: "Short" },
      ],
    });
    serve(documents([view({ versions: [full] })]));
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");

    expect(within(dialog).getByLabelText(/Nature/)).toHaveAttribute("maxlength", "20000");
    expect(within(dialog).getByLabelText(/Impact/)).toHaveAttribute("maxlength", "20000");
    expect(within(dialog).getAllByText("At the limit of 20,000 characters")).toHaveLength(1);
    expect(within(dialog).getByLabelText(/Nature/)).toHaveAccessibleDescription("At the limit of 20,000 characters");
  });

  it("will not finalise with a required section empty, and saves what was typed first", async () => {
    const world = serve(documents([view({ versions: [document()] })]));
    const order: string[] = [];
    let written: unknown = null;
    let to: unknown = null;
    server.use(
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, async ({ request }) => {
        written = await request.json();
        order.push("saved");
        return HttpResponse.json(world.now);
      }),
      http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async ({ request }) => {
        to = await request.json();
        order.push("finalised");
        world.now = documents([view({ versions: [document(FINALISED)] })]);
        return HttpResponse.json(world.now);
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");
    const finalise = within(dialog).getByRole("button", { name: "Finalise and tell the board" });
    expect(finalise).toBeDisabled();
    expect(within(dialog).getByText("Still to write: Its likely impact.")).toBeInTheDocument();

    await user.type(within(dialog).getByLabelText(/likely impact/i), "Contact details of 40 people");
    expect(finalise).toBeEnabled();
    await user.click(finalise);

    await vi.waitFor(() => expect(order).toEqual(["saved", "finalised"]));
    expect(written).toEqual({
      sections: { nature_extent: "A list was exposed", likely_impact: "Contact details of 40 people" },
    });
    // Nobody left out and nobody added: everyone on the list.
    expect(to).toEqual({ recipients: [CHAIR, DEPUTY], extra: [] });
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Finalised",
        "The organisation's board has been mailed. Nothing has gone to the regulator.",
      ),
    );
    expect(await screen.findByRole("button", { name: "Record as sent" })).toBeInTheDocument();
  });

  it("saves the words on the screen before finalising, even with nothing newly typed", async () => {
    const world = serve(documents([view({ versions: [document({ sections: FULL })] })]));
    const order: string[] = [];
    server.use(
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => {
        order.push("saved");
        return HttpResponse.json(world.now);
      }),
      http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, () => {
        order.push("finalised");
        return HttpResponse.json(world.now);
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Finalise and tell the board" }));

    await vi.waitFor(() => expect(order).toEqual(["saved", "finalised"]));
  });

  it("holds the words still while they are saved, so nothing typed is marked saved unsent", async () => {
    const world = serve(documents([view({ versions: [document()] })]));
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, async () => {
        await held;
        return HttpResponse.json(world.now);
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");
    const box = within(dialog).getByLabelText(/likely impact/i);
    await user.type(box, "Some");
    await user.click(within(dialog).getByRole("button", { name: "Save draft" }));

    await vi.waitFor(() => expect(box).toBeDisabled());
    // Who it goes to stands still with the words.
    expect(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" })).toBeDisabled();
    expect(within(dialog).getByRole("button", { name: "Add for this report" })).toBeDisabled();
    release();
    await vi.waitFor(() => expect(box).toBeEnabled());
    expect(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" })).toBeEnabled();
  });

  it("keeps an open draft through a failed poll, and shows the error only when there is nothing to show", async () => {
    serve(documents([view({ versions: [document()] })]));
    const { user, queryClient } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/likely impact/i), "Typed, not saved");

    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () =>
        HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment" } }, { status: 503 }),
      ),
    );
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: keys.breach.reports(BREACH) });
      // The query tells the screen on the next turn of the loop.
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(queryClient.getQueryState(keys.breach.reports(BREACH))?.status).toBe("error");
    expect(screen.queryByText("Down for a moment")).not.toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).getByLabelText(/likely impact/i)).toHaveValue("Typed, not saved");
  });

  it("closes a draft somebody else finalised, says so, and does not open the next one by itself", async () => {
    const world = serve(documents([view({ versions: [document()] })]));
    const { user, queryClient } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    await screen.findByRole("dialog");

    world.now = documents([view({ versions: [document(FINALISED)] })]);
    await polled(queryClient);

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.warning).toHaveBeenCalledTimes(1);
    expect(toast.warning).toHaveBeenCalledWith("That draft has been finalised", expect.any(String));

    world.now = documents([
      view({ versions: [document({ report_uuid: NEWER, version: 2 }), document(FINALISED)] }),
    ]);
    await polled(queryClient);

    expect(await screen.findByRole("button", { name: "Continue the draft" })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not take its own finalising for somebody else's, whichever comes back first", async () => {
    const world = serve(documents([view({ versions: [document({ sections: FULL })] })]));
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
      http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async () => {
        world.now = documents([view({ versions: [document(FINALISED)] })]);
        await held;
        return HttpResponse.json(world.now);
      }),
    );
    const { user, queryClient } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));
    await vi.waitFor(() => expect(world.now.kinds[0].versions[0].state).toBe("finalised"));

    await polled(queryClient);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    release();
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Finalised", expect.any(String)));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("says so when the reports cannot be read at all", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () =>
        HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment" } }, { status: 503 }),
      ),
    );
    render(<ReportsCard breach={breach()} />);

    expect(await screen.findByText("Down for a moment")).toBeInTheDocument();
  });

  it("reads who is on the board's list afresh on arrival, inside the staleness window", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () => {
        reads += 1;
        return HttpResponse.json(documents([view()]));
      }),
    );
    // As the application's client does: thirty seconds before a read goes stale.
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30_000 } } });
    const { unmount } = render(<ReportsCard breach={breach()} />, { queryClient });
    await screen.findByTestId("report-board_intimation");
    expect(reads).toBe(1);
    unmount();

    render(<ReportsCard breach={breach()} />, { queryClient });
    await vi.waitFor(() => expect(reads).toBe(2));
  });

  it("warns when nobody is on the board's list, and finalises only once an address is added for this report", async () => {
    const world = serve(documents([view({ versions: [document({ sections: FULL })] })], 0), []);
    let to: unknown = null;
    server.use(
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
      http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async ({ request }) => {
        to = await request.json();
        return HttpResponse.json(world.now);
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");

    expect(await within(dialog).findByText("Nobody is on the organisation's board list")).toBeInTheDocument();
    expect(within(dialog).getByText(/Add an address for this report below/)).toBeInTheDocument();
    const settings = within(dialog).getByRole("link", { name: "Breach settings" });
    expect(settings).toHaveAttribute("href", "/breach-settings");
    // In a tab of its own: following it must not drop what is typed here.
    expect(settings).toHaveAttribute("target", "_blank");
    const go = within(dialog).getByRole("button", { name: "Finalise and tell the board" });
    expect(go).toBeDisabled();
    expect(within(dialog).getByText("Choose at least one address.")).toBeInTheDocument();

    await user.type(within(dialog).getByLabelText(/^Mail ID/), "secretary@cmp.local");
    await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));
    expect(go).toBeEnabled();
    await user.click(go);

    await vi.waitFor(() => expect(to).toEqual({ recipients: [], extra: [{ full_name: null, email: "secretary@cmp.local" }] }));
  });

  it("does not ask about a draft that was saved when the window closes", async () => {
    const world = serve(documents([view({ versions: [document()] })]));
    server.use(http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)));
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/likely impact/i), "Some");
    await user.click(within(dialog).getByRole("button", { name: "Save draft" }));
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Draft saved"));

    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  describe("Record as sent", () => {
    it("needs both proofs, when it was sent, and the reference", async () => {
      const finalised = document(FINALISED);
      const world = serve(documents([view({ versions: [finalised] })]));
      const proofs: (string | null)[] = [];
      let filed: { filed_at: string; reference: string } | null = null;
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/evidence`, async ({ request }) => {
          proofs.push(multipart(await request.text(), "kind"));
          return HttpResponse.json(world.now, { status: 201 });
        }),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, async ({ request }) => {
          filed = (await request.json()) as { filed_at: string; reference: string };
          world.now = documents([
            view({
              duty_state: "done",
              versions: [
                document({
                  ...FINALISED,
                  state: "filed",
                  filed_at: "2026-11-06T11:00:00Z",
                  filed_reference: "DPB-1234",
                }),
              ],
            }),
          ]);
          return HttpResponse.json(world.now);
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByText(/the platform does not send this/i)).toBeInTheDocument();
      const go = within(dialog).getByRole("button", { name: "Record as sent" });
      expect(go).toBeDisabled();

      await user.upload(within(dialog).getByLabelText(/proof of internal approval/i), pdf("approval.pdf"));
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T11:00");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      expect(go).toBeDisabled();
      await user.upload(within(dialog).getByLabelText(/the mail sent to the regulator/i), pdf("sent.pdf"));
      expect(go).toBeEnabled();
      await user.click(go);

      await vi.waitFor(() => expect(filed).not.toBeNull());
      expect(proofs).toEqual(["approval", "sent_mail"]);
      expect(filed).toMatchObject({ reference: "DPB-1234" });
      await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
      expect(await screen.findByText(/reference DPB-1234/)).toBeInTheDocument();
    });

    it("does not keep a proof twice when the second try follows a refusal", async () => {
      const world = serve(documents([view({ versions: [document(FINALISED)] })]));
      const proofs: (string | null)[] = [];
      let tries = 0;
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/evidence`, async ({ request }) => {
          const kind = multipart(await request.text(), "kind") as "approval" | "sent_mail";
          proofs.push(kind);
          const evidence = [...world.now.kinds[0].versions[0].evidence, proofOf(kind)];
          world.now = documents([view({ versions: [document({ ...FINALISED, evidence })] })]);
          return HttpResponse.json(world.now, { status: 201 });
        }),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, () => {
          tries += 1;
          return tries === 1
            ? HttpResponse.json(
                { error: { code: "validation_failed", message: "It cannot have been sent before it was finalised" } },
                { status: 422 },
              )
            : HttpResponse.json(world.now);
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      await user.upload(within(dialog).getByLabelText(/proof of internal approval/i), pdf("approval.pdf"));
      await user.upload(within(dialog).getByLabelText(/the mail sent to the regulator/i), pdf("sent.pdf"));
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T09:00");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));

      await vi.waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith(
          "Not recorded",
          "It cannot have been sent before it was finalised",
        ),
      );
      expect(await within(dialog).findByRole("link", { name: "approval.pdf" })).toBeInTheDocument();
      expect(within(dialog).getByRole("link", { name: "sent_mail.pdf" })).toBeInTheDocument();
      // Nothing left in the box to suggest it would go again.
      const another = within(dialog).getByLabelText(/add another proof of internal approval/i) as HTMLInputElement;
      expect(another.files).toHaveLength(0);

      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));
      await vi.waitFor(() => expect(tries).toBe(2));
      expect(proofs).toEqual(["approval", "sent_mail"]);
    });

    it("needs no reference on a closure report, which completes no duty", async () => {
      const closure = view({
        kind: "closure",
        title: "Closure report",
        basis: "When the matter is concluded",
        duty: null,
        duty_state: null,
        versions: [document({ ...FINALISED, kind: "closure", title: "Closure report" })],
      });
      serve(documents([closure]));
      const { user } = render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/· optional$/)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      await user.upload(within(dialog).getByLabelText(/proof of internal approval/i), pdf("approval.pdf"));
      await user.upload(within(dialog).getByLabelText(/the mail sent to the regulator/i), pdf("sent.pdf"));
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T11:00");

      expect(within(dialog).getByRole("button", { name: "Record as sent" })).toBeEnabled();
    });

    it("attaches what is chosen and finishes later, with the rest still needed to record it", async () => {
      const world = serve(documents([view({ versions: [document(FINALISED)] })]));
      const proofs: (string | null)[] = [];
      let filed = false;
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/evidence`, async ({ request }) => {
          const kind = multipart(await request.text(), "kind") as "approval" | "sent_mail";
          proofs.push(kind);
          const evidence = [...world.now.kinds[0].versions[0].evidence, proofOf(kind, { file_name: `kept-${proofs.length}.pdf` })];
          world.now = documents([view({ versions: [document({ ...FINALISED, evidence })] })]);
          return HttpResponse.json(world.now, { status: 201 });
        }),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, () => {
          filed = true;
          return HttpResponse.json(world.now);
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      let dialog = await screen.findByRole("dialog");
      const later = within(dialog).getByRole("button", { name: "Attach and finish later" });
      expect(later).toBeDisabled();
      await user.upload(within(dialog).getByLabelText(/^proof of internal approval/i), pdf("approval.pdf"));
      await user.click(later);

      await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
      expect(proofs).toEqual(["approval"]);
      expect(filed).toBe(false);
      expect(toast.success).toHaveBeenCalledWith("Proof attached", expect.any(String));
      // On the row, and by name, with neither the time nor the reference known.
      const row = screen.getByTestId("report-board_intimation");
      expect(await within(row).findByRole("link", { name: "kept-1.pdf" })).toBeInTheDocument();

      await user.click(within(row).getByRole("button", { name: "Record as sent" }));
      dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByRole("link", { name: "kept-1.pdf" })).toBeInTheDocument();
      const go = within(dialog).getByRole("button", { name: "Record as sent" });
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T11:00");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      expect(go).toBeDisabled();
      await user.upload(within(dialog).getByLabelText(/^the mail sent to the regulator/i), pdf("sent.pdf"));
      expect(go).toBeEnabled();
    });

    it("takes another proof until the report is filed, and names each one it holds", async () => {
      const world = serve(
        documents([
          view({
            versions: [
              document({
                ...FINALISED,
                evidence: [proofOf("approval", { file_name: "wrong.pdf" }), proofOf("sent_mail")],
              }),
            ],
          }),
        ]),
      );
      const proofs: (string | null)[] = [];
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/evidence`, async ({ request }) => {
          proofs.push(multipart(await request.text(), "kind"));
          return HttpResponse.json(world.now, { status: 201 });
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByRole("link", { name: "wrong.pdf" })).toBeInTheDocument();
      await user.upload(within(dialog).getByLabelText(/add another proof of internal approval/i), pdf("right.pdf"));
      await user.click(within(dialog).getByRole("button", { name: "Attach and finish later" }));

      await vi.waitFor(() => expect(proofs).toEqual(["approval"]));
    });

    it("records whichever finalised version was the one sent, even behind a newer draft", async () => {
      const sent = document({ ...FINALISED, evidence: [proofOf("approval"), proofOf("sent_mail")] });
      const draft = document({ report_uuid: NEWER, version: 2 });
      const world = serve(documents([view({ versions: [draft, sent] })]));
      let filed = false;
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, () => {
          filed = true;
          world.now = documents([
            view({ versions: [draft, document({ ...sent, state: "filed", filed_at: "2026-11-06T10:30:00Z" })] }),
          ]);
          return HttpResponse.json(world.now);
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      expect(await screen.findByRole("button", { name: "Continue the draft" })).toBeInTheDocument();
      // Not folded away: it still needs doing.
      expect(screen.getByRole("button", { name: "Record as sent" })).toBeVisible();
      await user.click(screen.getByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByRole("heading", { name: /version 1$/ })).toBeInTheDocument();
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T10:30");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));

      await vi.waitFor(() => expect(filed).toBe(true));
      await vi.waitFor(() => expect(screen.queryByRole("button", { name: "Record as sent" })).not.toBeInTheDocument());
    });
  });

  describe("Record as sent while a no has the duty aside", () => {
    it("says a filing during a no completes the duty at the next yes", async () => {
      const world = serve(
        documents([view({ duty_state: "not_applicable", versions: [document({ ...FINALISED, evidence: [proofOf("approval"), proofOf("sent_mail")] })] })]),
      );
      server.use(http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, () => HttpResponse.json(world.now)));
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByText("This duty is set aside while the No stands")).toBeInTheDocument();
      expect(within(dialog).getByText(/completes the duty at the next Yes, dated when it was sent/)).toBeInTheDocument();
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T10:30");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));

      await vi.waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith(
          "Recorded as sent",
          "It completes the duty at the next Yes, dated when it was sent.",
        ),
      );
    });

    it("names the version already recorded as sent as the one the yes records, and promises this one nothing", async () => {
      const v1 = document({
        ...FINALISED,
        state: "filed",
        filed_at: "2026-11-06T10:00:00Z",
        filed_reference: "DPB/1",
        filed_by_name: "Priya Menon",
        evidence: [proofOf("approval"), proofOf("sent_mail")],
      });
      const v2 = document({
        ...FINALISED,
        report_uuid: NEWER,
        version: 2,
        evidence: [proofOf("approval"), proofOf("sent_mail")],
      });
      const world = serve(documents([view({ duty_state: "not_applicable", versions: [v2, v1] })]));
      server.use(http.post(`${API}/breaches/${BREACH}/reports/${NEWER}/file`, () => HttpResponse.json(world.now)));
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByRole("heading", { name: /version 2$/ })).toBeInTheDocument();
      expect(within(dialog).getByText("This duty is set aside while the No stands")).toBeInTheDocument();
      expect(within(dialog).queryByText(/completes the duty at the next Yes/)).not.toBeInTheDocument();
      expect(
        within(dialog).getByText(
          "Version 1 is already recorded as sent, and its filing is the one the next Yes records. What is recorded here is kept as well.",
        ),
      ).toBeInTheDocument();
      await user.type(within(dialog).getByLabelText(/^Sent at/), "2026-11-06T14:00");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB/2");
      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));

      await vi.waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith(
          "Recorded as sent",
          "It is kept. Version 1's filing is the one the next Yes records.",
        ),
      );
    });

    it("names every version already recorded as sent when there are more than one", async () => {
      const filed = (version: number, uuid: string) =>
        document({
          ...FINALISED,
          report_uuid: uuid,
          version,
          state: "filed",
          filed_at: "2026-11-06T10:00:00Z",
          filed_reference: `DPB/${version}`,
        });
      const v3 = document({ ...FINALISED, report_uuid: crypto.randomUUID(), version: 3 });
      serve(
        documents([view({ duty_state: "not_applicable", versions: [v3, filed(2, NEWER), filed(1, REPORT)] })]),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      expect(
        within(dialog).getByText(
          "Versions 1 and 2 are already recorded as sent; the next Yes records the one recorded first. What is recorded here is kept as well.",
        ),
      ).toBeInTheDocument();
    });

    it("says nothing of it while the duty stands, or on a report that completes no duty", async () => {
      const cases = [
        view({ versions: [document(FINALISED)] }),
        view({
          kind: "closure",
          title: "Closure report",
          duty: null,
          duty_state: null,
          versions: [document({ ...FINALISED, kind: "closure" })],
        }),
      ];
      for (const kind of cases) {
        serve(documents([kind]));
        const { user, unmount } = render(<ReportsCard breach={breach()} />);
        await user.click(await screen.findByRole("button", { name: "Record as sent" }));
        const dialog = await screen.findByRole("dialog");
        expect(within(dialog).queryByText("This duty is set aside while the No stands")).not.toBeInTheDocument();
        unmount();
      }
    });

    it("puts a refusal of the time under Sent at", async () => {
      const sentence = "It cannot have been sent before the incident was first noticed";
      serve(documents([view({ versions: [document({ ...FINALISED, evidence: [proofOf("approval"), proofOf("sent_mail")] })] })]));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/file`, () =>
          HttpResponse.json(
            { error: { code: "validation_failed", message: sentence, field: "filed_at", request_id: "r" } },
            { status: 422 },
          ),
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Record as sent" }));
      const dialog = await screen.findByRole("dialog");
      const when = within(dialog).getByLabelText(/^Sent at/);
      await user.type(when, "2026-11-01T10:30");
      await user.type(within(dialog).getByLabelText(/reference returned/i), "DPB-1234");
      await user.click(within(dialog).getByRole("button", { name: "Record as sent" }));

      await vi.waitFor(() => expect(when).toHaveAccessibleDescription(sentence));
      expect(when).toHaveAttribute("aria-invalid", "true");
      expect(toast.error).toHaveBeenCalledWith("Not recorded", sentence);

      // Changed, it is no longer the time that was refused.
      await user.type(when, "2026-11-06T10:30");
      expect(when).not.toHaveAttribute("aria-invalid");
    });
  });

  it("asks first before a new version of a finalised report that has not been sent", async () => {
    const world = serve(documents([view({ versions: [document(FINALISED)] })]));
    let started = 0;
    server.use(
      http.post(`${API}/breaches/${BREACH}/reports`, () => {
        started += 1;
        world.now = documents([
          view({ versions: [document({ report_uuid: NEWER, version: 2 }), document(FINALISED)] }),
        ]);
        return HttpResponse.json(world.now, { status: 201 });
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    expect(await screen.findByRole("button", { name: "Record as sent" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "New version" }));
    let dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/it can still be recorded as sent/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(started).toBe(0);

    await user.click(screen.getByRole("button", { name: "New version" }));
    dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Start a new version" }));

    await vi.waitFor(() => expect(started).toBe(1));
    expect(await screen.findByLabelText(/nature and extent/i)).toBeInTheDocument();
  });

  it("does not ask before a new version of a report already sent", async () => {
    const filed = document({ ...FINALISED, state: "filed", filed_at: "2026-11-06T11:00:00Z" });
    const world = serve(documents([view({ versions: [filed] })]));
    let started = 0;
    server.use(
      http.post(`${API}/breaches/${BREACH}/reports`, () => {
        started += 1;
        return HttpResponse.json(world.now, { status: 201 });
      }),
    );
    const { user } = render(<ReportsCard breach={breach()} />);

    await user.click(await screen.findByRole("button", { name: "New version" }));

    await vi.waitFor(() => expect(started).toBe(1));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows an earlier version's sent date, reference, mail and proof, not its finalised date alone", async () => {
    const proof = proofOf("approval", { file_name: "approved.pdf" });
    const earlier = document({
      ...FINALISED,
      state: "filed",
      filed_at: "2026-11-06T15:30:00Z",
      filed_reference: "DPB-0001",
      evidence: [proof],
      mail: mail({
        delivered: 1,
        failed: 1,
        retryable: 1,
        recipients: [address(), address({ status: "failed", email: "chair@cmp.local" })],
      }),
    });
    serve(documents([view({ versions: [document({ report_uuid: NEWER, version: 2 }), earlier] })]));
    render(<ReportsCard breach={breach()} />);

    const row = await screen.findByTestId("report-board_intimation");
    expect(within(row).getByText(/sent to the regulator .*, reference DPB-0001/)).toBeInTheDocument();
    expect(within(row).getByText(/1 delivered/)).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: "approved.pdf" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/breaches/${BREACH}/attachments/${proof.attachment_uuid}`),
    );
  });

  it("lists a filed report's proofs on its row, to download", async () => {
    const approval = proofOf("approval", { file_name: "approved.pdf" });
    const filed = document({
      ...FINALISED,
      state: "filed",
      filed_at: "2026-11-06T11:00:00Z",
      evidence: [approval, proofOf("sent_mail", { file_name: "sent.eml" })],
    });
    serve(documents([view({ duty_state: "done", versions: [filed] })]));
    render(<ReportsCard breach={breach()} />);

    const link = await screen.findByRole("link", { name: "approved.pdf" });
    expect(link).toHaveAttribute("href", expect.stringContaining(`/attachments/${approval.attachment_uuid}`));
    expect(link).toHaveAttribute("download");
    expect(screen.getByRole("link", { name: "sent.eml" })).toBeInTheDocument();
    expect(screen.getByText(/Internal approval/)).toBeInTheDocument();
  });

  it("reads a report to the organisation's board as sent once it is finalised", async () => {
    serve(
      documents([
        boardView({
          duty_state: "done",
          versions: [document({ ...FINALISED, kind: "org_board", mail: mail({ delivered: 1, failed: 1, retryable: 1 }) })],
        }),
      ]),
    );
    render(<ReportsCard breach={breach()} />);

    const row = await screen.findByTestId("report-org_board");
    expect(within(row).getByText("Sent")).toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "Record as sent" })).not.toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("reads a board report whose mail has not landed as just that", async () => {
    const queued = address({ status: "queued" });
    serve(
      documents([
        boardView({ versions: [document({ ...FINALISED, kind: "org_board", mail: mail({ queued: 1, recipients: [queued] }) })] }),
      ]),
    );
    const { unmount } = render(<ReportsCard breach={breach()} />);
    expect(within(await screen.findByTestId("report-org_board")).getByText("Sending")).toBeInTheDocument();
    unmount();

    serve(
      documents([
        boardView({ versions: [document({ ...FINALISED, kind: "org_board", mail: mail({ failed: 2 }) })] }),
      ]),
    );
    render(<ReportsCard breach={breach()} />);
    expect(within(await screen.findByTestId("report-org_board")).getByText("Not reached")).toBeInTheDocument();
  });

  describe("the mail", () => {
    const finalised = (m: BreachDocumentMail) => documents([view({ versions: [document({ ...FINALISED, mail: m })] })]);
    /** How long the query waits before it looks again, as it stands. */
    function pollEvery(queryClient: QueryClient) {
      const query = queryClient.getQueryCache().find({ queryKey: keys.breach.reports(BREACH) });
      const every = query?.observers[0].options.refetchInterval as (q: unknown) => number;
      return every(query);
    }

    it("offers Try again for mail lost in the queue, sends it, and shows it moving again", async () => {
      const lost = address({ status: "queued" });
      const world = serve(
        finalised(mail({ delivered: 1, queued: 1, stale: 1, retryable: 1, recipients: [address(), lost] })),
      );
      let sent = 0;
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () => {
          sent += 1;
          // A new attempt, so its time moves and it is no longer held up.
          world.now = finalised(mail({ delivered: 1, queued: 1, recipients: [address(), { ...lost, attempt: 2 }] }));
          return HttpResponse.json({ ...world.now, queued: 1 });
        }),
      );
      const { user, queryClient } = render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/1 held up/)).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Try again" }));

      expect(await screen.findByText(/1 on the way/)).toBeInTheDocument();
      expect(screen.queryByText(/held up/)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      expect(toast.success).toHaveBeenCalledWith("Sending again", "Mailing 1 address.");
      expect(pollEvery(queryClient)).toBe(2_000);
      expect(sent).toBe(1);
    });

    it("says how many a press queued", async () => {
      const world = serve(finalised(mail({ failed: 2, retryable: 2 })));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () =>
          HttpResponse.json({ ...world.now, queued: 2 }),
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Try again" }));

      await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Sending again", "Mailing 2 addresses."));
    });

    it("says so when a press queued nothing", async () => {
      const world = serve(finalised(mail({ failed: 1, retryable: 1 })));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () =>
          HttpResponse.json({ ...world.now, queued: 0 }),
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Try again" }));

      await vi.waitFor(() => expect(toast.info).toHaveBeenCalledWith("Nothing to send", expect.any(String)));
      expect(toast.success).not.toHaveBeenCalled();
    });

    it("shows the server's sentence when a press is refused", async () => {
      serve(finalised(mail({ failed: 1, retryable: 1 })));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () =>
          HttpResponse.json(
            { error: { code: "report_superseded", message: "A later version of this report has been finalised" } },
            { status: 409 },
          ),
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Try again" }));

      await vi.waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Not sent", "A later version of this report has been finalised"),
      );
    });

    it("holds the button while a press is in flight, so repeats queue nothing more", async () => {
      const world = serve(finalised(mail({ failed: 1, retryable: 1 })));
      let presses = 0;
      let release = () => {};
      const held = new Promise<void>((resolve) => {
        release = resolve;
      });
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, async () => {
          presses += 1;
          await held;
          return HttpResponse.json({ ...world.now, queued: 1 });
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      const button = await screen.findByRole("button", { name: "Try again" });
      await user.click(button);
      await vi.waitFor(() => expect(button).toBeDisabled());
      await user.click(button);
      expect(button).toBeDisabled();

      release();
      await vi.waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
      expect(presses).toBe(1);
    });

    it("looks closely for a moment after a press, then goes back to its own pace", async () => {
      const queued = address({ status: "queued" });
      const world = serve(finalised(mail({ queued: 1, stale: 1, retryable: 1, recipients: [queued] })));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () =>
          HttpResponse.json({ ...world.now, queued: 0 }),
        ),
      );
      const { user, queryClient } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Try again" }));
      await vi.waitFor(() => expect(toast.info).toHaveBeenCalled());

      await vi.waitFor(() => expect(pollEvery(queryClient)).toBe(2_000));
      const later = Date.now() + 60_000;
      const clock = vi.spyOn(Date, "now").mockReturnValue(later);
      expect(pollEvery(queryClient)).toBe(30_000);
      clock.mockRestore();
    });

    it("offers nothing where sending again would queue nothing", async () => {
      serve(finalised(mail({ delivered: 1, failed: 1, retryable: 0, recipients: [address(), address({ status: "failed" })] })));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/1 failed/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    });

    it("does not offer to reach an address added to the list since: that takes a new version", async () => {
      serve(finalised(mail({ delivered: 2, retryable: 0, recipients: [address(), address({ email: "chair@cmp.local" })] })), BOARD);
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/^Organisation's board: 2 delivered$/)).toBeInTheDocument();
      expect(screen.queryByText(/added to the list since/)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    });

    it("still names the address when the only one was taken off the list", async () => {
      const gone = address({ full_name: "Old Member", email: "old@cmp.local", status: "failed", removed: true });
      serve(documents([view({ versions: [document({ ...FINALISED, mail: mail({ recipients: [gone] }) })] })], 1));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText("Old Member, old@cmp.local: removed from the list")).toBeInTheDocument();
    });

    describe("with nobody it went to still on the list", () => {
      const NOBODY = /Nobody this version went to is on the list any more/;
      const gone = address({ email: "old@cmp.local", status: "failed", removed: true });
      const left = (listed: number, over: Partial<BreachDocumentKindView> = {}, m = mail({ recipients: [gone] })) =>
        documents([boardView({ versions: [document({ ...FINALISED, kind: "org_board", mail: m })], ...over })], listed);

      it("says nobody it went to can be reached, and that a new version goes to whoever is chosen", async () => {
        // Somebody is on the list, but not anybody this version went to.
        auth.me = makeMe({ role: "dpo", nav: ["breaches", "breach-settings"] });
        serve(left(2));
        render(<ReportsCard breach={breach()} />);

        const row = await screen.findByTestId("report-org_board");
        expect(within(row).getByText(NOBODY)).toHaveTextContent(/A new version goes to whoever you choose\.$/);
        expect(within(row).queryByRole("link", { name: "Breach settings" })).not.toBeInTheDocument();
        expect(within(row).getByText(/^Meera Iyer, old@cmp\.local: removed from the list$/)).toBeVisible();
        expect(within(row).queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      });

      it("adds where to fill an empty list only for whoever can reach Breach settings", async () => {
        auth.me = makeMe({ role: "dpo", nav: ["breaches", "breach-settings"] });
        serve(left(0));
        const { unmount } = render(<ReportsCard breach={breach()} />);

        let row = await screen.findByTestId("report-org_board");
        expect(within(row).getByText(/The list is empty/)).toBeInTheDocument();
        expect(within(row).getByRole("link", { name: "Breach settings" })).toHaveAttribute("href", "/breach-settings");
        unmount();

        auth.me = makeMe({ role: "dpo", nav: ["breaches"] });
        render(<ReportsCard breach={breach()} />);
        row = await screen.findByTestId("report-org_board");
        expect(within(row).getByText(NOBODY)).toBeInTheDocument();
        expect(within(row).queryByText(/The list is empty/)).not.toBeInTheDocument();
        expect(within(row).queryByRole("link", { name: "Breach settings" })).not.toBeInTheDocument();
      });

      it("says nothing of it where somebody was reached, somebody still waits for it, or the report may not go", async () => {
        const cases = [
          left(0, { duty_state: "done" }, mail({ delivered: 1, recipients: [{ ...gone, status: "delivered" }] })),
          left(0, { blocked_by: "CERT-In was set aside as not reportable. Mark it reportable again first" }),
          documents(
            [
              view({
                kind: "cert_in",
                versions: [
                  document({
                    ...FINALISED,
                    kind: "cert_in",
                    mail: mail({ held: 1, recipients: [address({ status: "held", attempt: 0, recorded_at: null })] }),
                  }),
                ],
              }),
            ],
            0,
          ),
        ];
        for (const now of cases) {
          serve(now);
          const { unmount } = render(<ReportsCard breach={breach()} />);
          await screen.findByText(/^Organisation's board:/);
          expect(screen.queryByText(NOBODY)).not.toBeInTheDocument();
          unmount();
        }
      });
    });

    describe("when the mail landed and the board's duty was left waiting", () => {
      const landed = (over: Partial<BreachDocument> = {}) =>
        document({ ...FINALISED, kind: "org_board", mail: mail({ delivered: 2 }), ...over });

      it("offers Try again, which queues nothing, and says it completed the duty", async () => {
        const world = serve(documents([boardView({ versions: [landed()] })]));
        server.use(
          http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () => {
            world.now = documents([boardView({ duty_state: "done", versions: [landed()] })]);
            return HttpResponse.json({ ...world.now, queued: 0 });
          }),
        );
        const { user } = render(<ReportsCard breach={breach()} />);

        await user.click(await screen.findByRole("button", { name: "Try again" }));

        await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Duty completed", expect.any(String)));
        await vi.waitFor(() => expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument());
      });

      it("offers it on the newest finalised version alone, and not while mail is going or once the duty is done", async () => {
        const cases: [BreachDocumentKindView, number][] = [
          [boardView({ versions: [landed({ report_uuid: NEWER, version: 2 }), landed()] }), 1],
          [boardView({ versions: [landed({ mail: mail({ delivered: 1, queued: 1, recipients: [address({ status: "queued" })] }) })] }), 0],
          [boardView({ duty_state: "done", versions: [landed()] }), 0],
          [view({ versions: [landed({ kind: "board_intimation" })] }), 0],
        ];
        for (const [kind, buttons] of cases) {
          serve(documents([kind]));
          const { unmount } = render(<ReportsCard breach={breach()} />);
          await screen.findByTestId(`report-${kind.kind}`);
          expect(screen.queryAllByRole("button", { name: "Try again" })).toHaveLength(buttons);
          unmount();
        }
      });
    });

    describe("on an earlier version", () => {
      const board = (m: BreachDocumentMail) => document({ ...FINALISED, kind: "org_board", mail: m });
      const fold = (row: HTMLElement) => within(row).getByText("Earlier versions (1)").closest("details");

      it("stays folded with no Try again when a later version has replaced it", async () => {
        const newer = document({ ...FINALISED, report_uuid: NEWER, version: 2, kind: "org_board" });
        serve(documents([boardView({ duty_state: "done", versions: [newer, board(mail({ delivered: 1, failed: 1 }))] })]));
        render(<ReportsCard breach={breach()} />);

        const row = await screen.findByTestId("report-org_board");
        expect(fold(row)).not.toHaveAttribute("open");
        expect(within(row).queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      });

      it("opens by itself while it still has something that can be done", async () => {
        const draft = document({ report_uuid: NEWER, version: 2, kind: "org_board" });
        serve(documents([boardView({ versions: [draft, board(mail({ failed: 1, retryable: 1 }))] })]));
        render(<ReportsCard breach={breach()} />);

        const row = await screen.findByTestId("report-org_board");
        expect(fold(row)).toHaveAttribute("open");
        expect(within(row).getByRole("button", { name: "Try again" })).toBeVisible();
      });

      it("does not open on a closed breach, where nothing can be done", async () => {
        serve(documents([view({ versions: [document({ report_uuid: NEWER, version: 2, ...FINALISED }), document(FINALISED)] })]));
        render(<ReportsCard breach={breach({ status: "closed" })} />);

        expect(fold(await screen.findByTestId("report-board_intimation"))).not.toHaveAttribute("open");
      });
    });

    it("has nothing to try again while the mail is simply on its way", async () => {
      serve(finalised(mail({ delivered: 1, queued: 1, recipients: [address(), address({ status: "queued" })] })));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/1 on the way/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    });

    it("looks again every two seconds only while the worker may yet reach something", async () => {
      const queued = () => address({ status: "queued" });
      const cases: [BreachDocumentMail, number][] = [
        [mail({ queued: 2, recipients: [queued(), queued()] }), 2_000],
        [mail({ queued: 2, stale: 1, recipients: [queued(), queued()] }), 2_000],
        [mail({ queued: 2, stale: 2, recipients: [queued(), queued()] }), 30_000],
        // Taken off the list while queued: never counted stale, never coming.
        [mail({ queued: 2, stale: 1, recipients: [queued(), address({ status: "queued", removed: true })] }), 30_000],
        [mail({ delivered: 2 }), 30_000],
      ];
      for (const [m, every] of cases) {
        serve(finalised(m));
        const { queryClient, unmount } = render(<ReportsCard breach={breach()} />);
        await screen.findByTestId("report-board_intimation");
        expect(pollEvery(queryClient)).toBe(every);
        unmount();
      }
    });

    it("says who was not reached, address by address, and names one taken off the list", async () => {
      serve(
        finalised(
          mail({
            delivered: 1,
            failed: 2,
            recipients: [
              address({ email: "meera@cmp.local" }),
              address({ full_name: null, email: "chair@cmp.local", status: "failed", error: "SMTPDataError" }),
              address({ full_name: "Old Member", email: "old@cmp.local", status: "failed", error: "RecipientRemoved", removed: true }),
            ],
          }),
        ),
      );
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/^chair@cmp\.local: failed .*\(SMTPDataError\)$/)).toBeVisible();
      expect(screen.getByText("Old Member, old@cmp.local: removed from the list")).toBeVisible();
      expect(screen.getByText(/^Meera Iyer, meera@cmp\.local: delivered /)).toBeVisible();
    });

    it("folds the addresses away when everyone was reached", async () => {
      serve(finalised(mail({ delivered: 1, recipients: [address()] })));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText("Address by address (1)")).toBeInTheDocument();
      expect(screen.getByText(/^Meera Iyer, meera@cmp\.local: delivered /)).not.toBeVisible();
    });
  });

  describe("who it goes to", () => {
    const ready = () => documents([view({ versions: [document({ sections: FULL })] })]);
    /** The window, open on the draft, with the list read. */
    async function opened(user: ReturnType<typeof render>["user"]) {
      await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
      const dialog = await screen.findByRole("dialog");
      await within(dialog).findByRole("group", { name: "Who it goes to" });
      return dialog;
    }
    /** Finalise, answering with the reports as they stand, and keep what was sent. */
    function finalising(world: { now: BreachDocuments }, answer?: () => Response) {
      const sent: unknown[] = [];
      server.use(
        http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async ({ request }) => {
          sent.push(await request.json());
          return answer ? answer() : HttpResponse.json(world.now);
        }),
      );
      return sent;
    }

    it("sends the list less those left out, with the addresses added for this report", async () => {
      const world = serve(ready());
      const sent = finalising(world);
      const { user } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);

      await user.click(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" }));
      await user.type(within(dialog).getByLabelText(/^Name/), "Ravi Kumar");
      await user.type(within(dialog).getByLabelText(/^Mail ID/), "ravi@cmp.local");
      await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));
      await user.type(within(dialog).getByLabelText(/^Mail ID/), "auditor@cmp.local");
      await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));
      expect(within(dialog).getByText("Goes to 3 addresses.")).toBeInTheDocument();
      await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));

      await vi.waitFor(() =>
        expect(sent).toEqual([
          {
            recipients: [CHAIR],
            extra: [
              { full_name: "Ravi Kumar", email: "ravi@cmp.local" },
              { full_name: null, email: "auditor@cmp.local" },
            ],
          },
        ]),
      );
    });

    it("keeps what was left out and added through a read of the list, and takes in an address added meanwhile", async () => {
      const world = serve(ready());
      const sent = finalising(world);
      const { user, queryClient } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);
      await user.click(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" }));
      await user.type(within(dialog).getByLabelText(/^Mail ID/), "ravi@cmp.local");
      await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));

      const SECRETARY = "33333333-3333-4333-8333-333333333333";
      world.board = [...BOARD, entry({ recipient_uuid: SECRETARY, full_name: null, email: "secretary@cmp.local" })];
      await act(async () => {
        await queryClient.refetchQueries({ queryKey: keys.breach.boardList(BREACH) });
      });

      expect(await within(dialog).findByRole("checkbox", { name: "secretary@cmp.local" })).toBeChecked();
      expect(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" })).not.toBeChecked();
      expect(within(dialog).getByText("ravi@cmp.local")).toBeInTheDocument();
      await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));

      await vi.waitFor(() =>
        expect(sent).toEqual([{ recipients: [CHAIR, SECRETARY], extra: [{ full_name: null, email: "ravi@cmp.local" }] }]),
      );
    });

    it("keeps an address marked mandatory while the window is open, even after it was left out", async () => {
      const world = serve(ready());
      const sent = finalising(world);
      const { user, queryClient } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);
      await user.click(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" }));

      world.board = [BOARD[0], { ...BOARD[1], mandatory: true }];
      await act(async () => {
        await queryClient.refetchQueries({ queryKey: keys.breach.boardList(BREACH) });
      });

      const deputy = within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" });
      await vi.waitFor(() => expect(deputy).toBeChecked());
      expect(deputy).toBeDisabled();
      expect(within(dialog).getByText("Mandatory")).toBeInTheDocument();
      await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));

      await vi.waitFor(() => expect(sent).toEqual([{ recipients: [CHAIR, DEPUTY], extra: [] }]));
    });

    it("shows the server's sentence when the list changed under it, keeps the window and what was chosen, and reads the list again", async () => {
      const sentence = "Somebody chosen has been taken off the board list since. Look at the list again";
      const world = serve(ready());
      // Reads made once the refusal is on its way back: the save before it
      // reads the list too, and that read may predate the change.
      let readsAtRefusal = Infinity;
      const sent: unknown[] = [];
      server.use(
        http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async ({ request }) => {
          sent.push(await request.json());
          // Whatever the save set reading is done before the answer goes.
          await new Promise((resolve) => setTimeout(resolve, 100));
          readsAtRefusal = world.boardReads;
          return HttpResponse.json(
            { error: { code: "recipient_not_listed", message: sentence, request_id: "r", gone: [DEPUTY] } },
            { status: 409 },
          );
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);
      await user.click(within(dialog).getByRole("checkbox", { name: "Asha Rao, chair@cmp.local" }));
      await user.type(within(dialog).getByLabelText(/^Mail ID/), "ravi@cmp.local");
      await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));

      await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));

      await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith("Not done", sentence));
      expect(sent).toHaveLength(1);
      await vi.waitFor(() => expect(world.boardReads).toBeGreaterThan(readsAtRefusal));
      expect(screen.getByRole("dialog")).toBe(dialog);
      expect(within(dialog).getByRole("checkbox", { name: "Asha Rao, chair@cmp.local" })).not.toBeChecked();
      expect(within(dialog).getByText("ravi@cmp.local")).toBeInTheDocument();
    });

    it("says when the board's list cannot be read, and will not finalise", async () => {
      serve(ready());
      server.use(
        http.get(`${API}/breaches/${BREACH}/reports/recipients`, () =>
          HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment", request_id: "r" } }, { status: 409 }),
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
      const dialog = await screen.findByRole("dialog");

      expect(await within(dialog).findByText("The board's list could not be read")).toBeInTheDocument();
      expect(within(dialog).getByText("Down for a moment")).toBeInTheDocument();
      expect(within(dialog).getByRole("button", { name: "Finalise and tell the board" })).toBeDisabled();
    });

    it("marks the added address the server refused", async () => {
      const world = serve(ready());
      finalising(world, () =>
        HttpResponse.json(
          {
            error: {
              code: "validation_failed",
              message: "That is not an email address",
              field: "extra.1.email",
              request_id: "r",
            },
          },
          { status: 422 },
        ),
      );
      const { user } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);
      for (const address of ["ravi@cmp.local", "odd@cmp.local"]) {
        await user.type(within(dialog).getByLabelText(/^Mail ID/), address);
        await user.click(within(dialog).getByRole("button", { name: "Add for this report" }));
      }

      await user.click(within(dialog).getByRole("button", { name: "Finalise and tell the board" }));

      const added = within(dialog).getByRole("list", { name: "Added for this report" });
      const [first, second] = within(added).getAllByRole("listitem");
      await vi.waitFor(() => expect(within(second).getByRole("alert")).toHaveTextContent("That is not an email address"));
      expect(within(first).queryByRole("alert")).not.toBeInTheDocument();
    });

    it("asks before closing once who it goes to was changed, even after the words were saved", async () => {
      const world = serve(ready());
      server.use(http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)));
      const { user } = render(<ReportsCard breach={breach()} />);
      const dialog = await opened(user);
      await user.type(within(dialog).getByLabelText(/^Nature/), " today");
      await user.click(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" }));
      await user.click(within(dialog).getByRole("button", { name: "Save draft" }));
      await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Draft saved"));

      await user.click(within(dialog).getByRole("button", { name: "Close" }));

      expect(within(dialog).getByText("You have changes that are not saved.")).toBeInTheDocument();
      expect(screen.getByRole("dialog")).toBe(dialog);
    });

    it("names an address added for that report only, and never calls it removed from the list", async () => {
      serve(
        documents([
          view({
            versions: [
              document({
                ...FINALISED,
                mail: mail({
                  delivered: 2,
                  recipients: [
                    address({ full_name: null, email: "ravi@cmp.local", added_for_this_send: true }),
                    address({ email: "chair@cmp.local", mandatory: true }),
                  ],
                }),
              }),
            ],
          }),
        ]),
      );
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/^ravi@cmp\.local \(this report only\): delivered /)).toBeInTheDocument();
      expect(screen.getByText(/^Meera Iyer, chair@cmp\.local \(mandatory\): delivered /)).toBeInTheDocument();
      expect(screen.queryByText(/removed from the list/)).not.toBeInTheDocument();
    });
  });

  describe("a report to CERT-In before validation", () => {
    const HELD_TOAST =
      "The board's mail waits for validation: it goes at the first Yes, and not at all if the incident is never validated as a personal data breach. Nothing has gone to CERT-In.";
    const waiting = (over: Partial<BreachDocumentMailRecipient> = {}) =>
      address({ status: "held", attempt: 0, recorded_at: null, ...over });
    const certIn = (versions: BreachDocument[], over: Partial<BreachDocumentKindView> = {}) =>
      documents([
        view({ kind: "cert_in", title: "Report to CERT-In", duty: "cert_in", holds_mail: true, versions, ...over }),
      ]);
    const finalisedCertIn = (m: BreachDocumentMail, over: Partial<BreachDocument> = {}) =>
      document({ ...FINALISED, kind: "cert_in", title: "Report to CERT-In", mail: m, ...over });

    it("says in the window that the board's mail waits, and names the button for it", async () => {
      serve(certIn([document({ kind: "cert_in", title: "Report to CERT-In", sections: FULL })]));
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
      const dialog = await screen.findByRole("dialog");

      expect(await within(dialog).findByText("The board's mail waits for validation")).toBeInTheDocument();
      expect(within(dialog).getByRole("button", { name: "Finalise and hold for validation" })).toBeEnabled();
      expect(within(dialog).queryByRole("button", { name: "Finalise and tell the board" })).not.toBeInTheDocument();
      expect(within(dialog).getByText(/it does not go to the regulator/i)).toBeInTheDocument();
    });

    it("says it was held, not mailed, in the toast after finalising", async () => {
      const world = serve(certIn([document({ kind: "cert_in", title: "Report to CERT-In", sections: FULL })]));
      server.use(
        http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, () => {
          world.now = certIn([finalisedCertIn(mail({ held: 2, recipients: [waiting(), waiting({ email: "x@cmp.local" })] }))]);
          return HttpResponse.json(world.now);
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Continue the draft" }));
      const dialog = await screen.findByRole("dialog");
      await user.click(await within(dialog).findByRole("button", { name: "Finalise and hold for validation" }));

      await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Finalised", HELD_TOAST));
      expect(toast.success).not.toHaveBeenCalledWith("Finalised", expect.stringContaining("has been mailed"));
    });

    it("says the mail is waiting, to how many, and offers no Try again", async () => {
      serve(certIn([finalisedCertIn(mail({ held: 2, recipients: [waiting(), waiting({ email: "x@cmp.local" })] }))]));
      render(<ReportsCard breach={breach()} />);

      expect(
        await screen.findByText(
          "Organisation's board: waiting for validation. It goes to 2 addresses at the first Yes, and not at all if the incident is never validated as a personal data breach.",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText(/^Meera Iyer, meera@cmp\.local: waiting for validation$/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Send to the board" })).not.toBeInTheDocument();
    });

    it.each([
      [
        "held while CERT-In is set aside",
        { held: 1, recipients: [waiting()] },
        {},
        { duty_state: "not_applicable" as const, blocked_by: "CERT-In was set aside as not reportable. Mark it reportable again first" },
        "Organisation's board: not sent while CERT-In is set aside; mark it reportable again before validation and it goes at the Yes.",
      ],
      [
        "held, and replaced by a later version",
        { held: 1, recipients: [waiting()] },
        { superseded: true },
        {},
        "Organisation's board: replaced by a later version; it will not go.",
      ],
      [
        "never sent, and replaced by a later version",
        { unsent: 1, recipients: [waiting({ status: "unsent" })] },
        { superseded: true },
        { holds_mail: false },
        "Organisation's board: not sent: a later version replaced it.",
      ],
      [
        "withheld at the yes while CERT-In was set aside",
        { unsent: 1, recipients: [waiting({ status: "unsent" })] },
        {},
        { holds_mail: false, duty_state: "not_applicable" as const, blocked_by: "CERT-In was set aside as not reportable. Mark it reportable again first" },
        "Organisation's board: not sent: CERT-In was set aside when the incident was validated.",
      ],
    ])("says why the board was not sent it (%s)", async (_, m, doc, kind, line) => {
      serve(certIn([finalisedCertIn(mail(m), doc)], kind));
      render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(line)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Send to the board" })).not.toBeInTheDocument();
    });

    it("offers to send it to the board once CERT-In is marked again after a yes that withheld it", async () => {
      const unsent = mail({ unsent: 1, retryable: 1, recipients: [waiting({ status: "unsent" })] });
      const world = serve(certIn([finalisedCertIn(unsent)], { holds_mail: false }));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/resend`, () => {
          world.now = certIn(
            [finalisedCertIn(mail({ queued: 1, recipients: [address({ status: "queued" })] }))],
            { holds_mail: false },
          );
          return HttpResponse.json({ ...world.now, queued: 1 });
        }),
      );
      const { user } = render(<ReportsCard breach={breach()} />);

      expect(await screen.findByText(/CERT-In was set aside when the incident was validated/)).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Send to the board" }));

      await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Sending to the board", "Mailing 1 address."));
      expect(await screen.findByText(/1 on the way/)).toBeInTheDocument();
    });

    it("looks again at its own pace while the mail waits, and every two seconds once the yes sets it going", async () => {
      const world = serve(certIn([finalisedCertIn(mail({ held: 1, recipients: [waiting()] }))]));
      const { queryClient } = render(<ReportsCard breach={breach()} />);
      await screen.findByText(/waiting for validation\./);
      const every = () => {
        const query = queryClient.getQueryCache().find({ queryKey: keys.breach.reports(BREACH) });
        return (query?.observers[0].options.refetchInterval as (q: unknown) => number)(query);
      };
      expect(every()).toBe(30_000);

      world.now = certIn([finalisedCertIn(mail({ queued: 1, recipients: [address({ status: "queued" })] }))], {
        holds_mail: false,
      });
      await polled(queryClient);

      expect(await screen.findByText(/1 on the way/)).toBeInTheDocument();
      expect(every()).toBe(2_000);
    });
  });

  it("says plainly what a closed breach holds up, and offers nothing to do", async () => {
    serve(
      documents([
        view(),
        view({ kind: "closure", versions: [document({ ...FINALISED, kind: "closure", mail: mail({ failed: 1 }) })] }),
      ]),
    );
    render(<ReportsCard breach={breach({ status: "closed" })} />);

    await screen.findByTestId("report-board_intimation");
    expect(screen.getByText(/can only be written, sent or recorded after reopening/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Draft it" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record as sent" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});

describe("NotifyBoardButton", () => {
  it("is shown only while the board's duty is outstanding", async () => {
    let reads = 0;
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () => {
        reads += 1;
        return HttpResponse.json(documents([boardView()]));
      }),
    );
    const { unmount } = render(<NotifyBoardButton breach={breach({ obligations: [dutyOf({})] })} />);
    expect(await screen.findByRole("button", { name: "Notify Organization Board" })).toBeInTheDocument();
    unmount();

    for (const obligations of [[], [dutyOf({ state: "done" })], [dutyOf({ state: "not_applicable" })]]) {
      const before = reads;
      const { unmount: gone } = render(<NotifyBoardButton breach={breach({ obligations })} />);
      await vi.waitFor(() => expect(reads).toBeGreaterThan(before));
      expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
      gone();
    }
  });

  it("is not shown on an incident not yet recorded, whatever old duty it holds", async () => {
    let read = false;
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () => {
        read = true;
        return HttpResponse.json(documents([boardView()]));
      }),
    );
    render(<NotifyBoardButton breach={breach({ breach_reference: null, obligations: [dutyOf({})] })} />);

    await vi.waitFor(() => expect(read).toBe(true));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 10));
    });
    expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
  });

  it("is not shown on a closed breach", async () => {
    let read = false;
    server.use(
      http.get(`${API}/breaches/${BREACH}/reports`, () => {
        read = true;
        return HttpResponse.json(documents([boardView()]));
      }),
    );
    render(<NotifyBoardButton breach={breach({ status: "closed", obligations: [dutyOf({})] })} />);

    await vi.waitFor(() => expect(read).toBe(true));
    expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
  });

  it("drafts the report in a pop-up and sends it to the board's addresses", async () => {
    const draft = document({
      kind: "org_board",
      title: "Report to the organisation's board",
      sections: [{ key: "what_happened", label: "What happened", required: true, body: "A list was exposed" }],
    });
    const world = serve(documents([boardView()]));
    let to: unknown = null;
    server.use(
      http.post(`${API}/breaches/${BREACH}/reports`, () => {
        world.now = documents([boardView({ versions: [draft] })]);
        return HttpResponse.json(world.now, { status: 201 });
      }),
      http.put(`${API}/breaches/${BREACH}/reports/${REPORT}`, () => HttpResponse.json(world.now)),
      http.post(`${API}/breaches/${BREACH}/reports/${REPORT}/finalise`, async ({ request }) => {
        to = await request.json();
        world.now = documents([boardView({ duty_state: "done", versions: [document({ ...draft, ...FINALISED })] })]);
        return HttpResponse.json(world.now);
      }),
    );
    const { user } = render(<NotifyBoardButton breach={breach({ obligations: [dutyOf({})] })} />);

    await user.click(await screen.findByRole("button", { name: "Notify Organization Board" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(/what happened/i)).toHaveValue("A list was exposed");
    // Everyone on the list, ticked, each named by its address.
    expect(await within(dialog).findByRole("checkbox", { name: "Asha Rao, chair@cmp.local" })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: "deputy@cmp.local" })).toBeChecked();
    await user.click(within(dialog).getByRole("button", { name: "Send to the board" }));

    await vi.waitFor(() => expect(to).toEqual({ recipients: [CHAIR, DEPUTY], extra: [] }));
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Sent to the organisation's board",
        "Mailing 2 addresses. The duty completes when the mail lands.",
      ),
    );
  });

  it("opens the draft already waiting rather than starting another", async () => {
    const draft = document({ kind: "org_board", title: "Report to the organisation's board" });
    serve(documents([boardView({ versions: [draft] })]));
    const { user } = render(<NotifyBoardButton breach={breach({ obligations: [dutyOf({})] })} />);

    await user.click(await screen.findByRole("button", { name: "Notify Organization Board" }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("keeps an open draft through a change of duty", async () => {
    const draft = document({ kind: "org_board", title: "Report to the organisation's board" });
    serve(documents([boardView({ versions: [draft] })]));
    const { user, rerender } = render(<NotifyBoardButton breach={breach({ obligations: [dutyOf({})] })} />);

    await user.click(await screen.findByRole("button", { name: "Notify Organization Board" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/likely impact/i), "Typed, not saved");

    // A colleague's No sets the duty aside mid-draft.
    rerender(<NotifyBoardButton breach={breach({ obligations: [dutyOf({ state: "not_applicable" })] })} />);

    expect(within(screen.getByRole("dialog")).getByLabelText(/likely impact/i)).toHaveValue("Typed, not saved");
    expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
  });

  it("closes a draft somebody else finalised, says so, and does not open the next one by itself", async () => {
    const draft = document({ kind: "org_board", title: "Report to the organisation's board" });
    const world = serve(documents([boardView({ versions: [draft] })]));
    const { user, queryClient } = render(<NotifyBoardButton breach={breach({ obligations: [dutyOf({})] })} />);

    await user.click(await screen.findByRole("button", { name: "Notify Organization Board" }));
    await screen.findByRole("dialog");

    world.now = documents([boardView({ versions: [document({ ...draft, ...FINALISED })] })]);
    await polled(queryClient);

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.warning).toHaveBeenCalledTimes(1);
    expect(toast.warning).toHaveBeenCalledWith("That draft has been finalised", expect.any(String));

    world.now = documents([
      boardView({ versions: [document({ ...draft, report_uuid: NEWER, version: 2 }), document({ ...draft, ...FINALISED })] }),
    ]);
    await polled(queryClient);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  describe("once the report is finalised and the duty still stands", () => {
    const sent = (m: BreachDocumentMail, recipients = 2) =>
      documents(
        [
          boardView({
            versions: [document({ ...FINALISED, kind: "org_board", title: "Report to the organisation's board", mail: m })],
          }),
        ],
        recipients,
      );
    const due = breach({ obligations: [dutyOf({})] });

    it("says the mail is going rather than offering a new version", async () => {
      let started = false;
      serve(sent(mail({ queued: 2, recipients: [address({ status: "queued" }), address({ status: "queued" })] })));
      server.use(
        http.post(`${API}/breaches/${BREACH}/reports`, () => {
          started = true;
          return HttpResponse.json({});
        }),
      );
      render(<NotifyBoardButton breach={due} />);

      expect(await screen.findByText("Sending to the board")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
      expect(started).toBe(false);
    });

    it("points to Try again when every address failed", async () => {
      serve(sent(mail({ failed: 2, retryable: 2 })));
      render(<NotifyBoardButton breach={due} />);

      const link = await screen.findByRole("link", { name: /Not reached: Try again on the Reports tab/ });
      expect(link).toHaveAttribute("href", "#reports");
      expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
    });

    it("points to Try again when the mail was lost in the queue", async () => {
      serve(
        sent(mail({ queued: 2, stale: 2, retryable: 2, recipients: [address({ status: "queued" }), address({ status: "queued" })] })),
      );
      render(<NotifyBoardButton breach={due} />);

      expect(await screen.findByRole("link", { name: /Try again on the Reports tab/ })).toBeInTheDocument();
      expect(screen.queryByText("Sending to the board")).not.toBeInTheDocument();
    });

    it("reads the breach again when the mail lands, since the worker completes the duty", async () => {
      const world = serve(sent(mail({ queued: 1, recipients: [address({ status: "queued" })] })));
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(keys.breach.detail(BREACH), due);
      render(<NotifyBoardButton breach={due} />, { queryClient });
      await screen.findByText("Sending to the board");
      expect(queryClient.getQueryState(keys.breach.detail(BREACH))?.isInvalidated).toBe(false);

      world.now = sent(mail({ delivered: 1, recipients: [address()] }));
      await queryClient.refetchQueries({ queryKey: keys.breach.reports(BREACH) });

      await vi.waitFor(() =>
        expect(queryClient.getQueryState(keys.breach.detail(BREACH))?.isInvalidated).toBe(true),
      );
    });

    it("takes the reports' word that the duty is done, offers nothing, and reads the breach again", async () => {
      const landed = mail({ delivered: 1, recipients: [address()] });
      const world = serve(sent(landed));
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      queryClient.setQueryData(keys.breach.detail(BREACH), due);
      render(<NotifyBoardButton breach={due} />, { queryClient });
      await screen.findByRole("link", { name: /Delivered/ });
      await vi.waitFor(() =>
        expect(queryClient.getQueryState(keys.breach.detail(BREACH))?.isInvalidated).toBe(true),
      );
      // The first read came back before the worker had settled the duty.
      queryClient.setQueryData(keys.breach.detail(BREACH), due);

      world.now = documents([
        boardView({
          duty_state: "done",
          versions: [document({ ...FINALISED, kind: "org_board", mail: landed })],
        }),
      ]);
      await polled(queryClient);

      expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Delivered/ })).not.toBeInTheDocument();
      expect(queryClient.getQueryState(keys.breach.detail(BREACH))?.isInvalidated).toBe(true);
    });

    it("leads to the Reports tab rather than a second mailing when the mail landed and the duty still stands", async () => {
      serve(sent(mail({ delivered: 2 })));
      render(<NotifyBoardButton breach={due} />);

      const link = await screen.findByRole("link", { name: "Delivered: finish on the Reports tab" });
      expect(link).toHaveAttribute("href", "#reports");
      expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
    });

    it("offers a new version when nobody it went to is still on the list", async () => {
      auth.me = makeMe({ role: "dpo", nav: ["breaches", "breach-settings"] });
      for (const listed of [0, 1]) {
        serve(sent(mail({ recipients: [address({ status: "failed", removed: true })] }), listed));
        const { unmount } = render(<NotifyBoardButton breach={due} />);

        // Try again reaches only those it went to, so the way on is a new version.
        expect(await screen.findByRole("button", { name: "Notify Organization Board" })).toBeInTheDocument();
        expect(screen.queryByRole("link", { name: /Try again/ })).not.toBeInTheDocument();
        expect(screen.queryByRole("link", { name: "Breach settings" })).not.toBeInTheDocument();
        unmount();
      }
    });
  });
});
