/**
 * Check in DataVault, on a rights request (0070): the card draws the server's
 * answer - whether DataVault can be asked, what it last listed, and whether a
 * later attempt failed - and the button makes the one call. On an erasure
 * request (0071) it also tells DataVault to erase, asked first, and asks how
 * far each asset has got.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  DataVaultAsset,
  DataVaultCheck,
  DataVaultErasure,
  RequestDataVault,
} from "@/features/datavault/api";
import {
  RequestDataVaultCard,
  erasureSummary,
} from "@/features/datavault/components/request-datavault-card";
import { TicketDataVault } from "@/features/datavault/components/ticket-datavault";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const UUID = "99999999-9999-4999-8999-999999999999";

const asset = (over: Partial<DataVaultAsset> = {}): DataVaultAsset => ({
  asset_ref: "DV-IMG-000101",
  consent_ref: "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71",
  project_ref: "0e8d6c4b-2a19-4f7e-b5d3-c1a9e7f50b22",
  consent_uuid: "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71",
  consent_no: 812,
  project_uuid: "0e8d6c4b-2a19-4f7e-b5d3-c1a9e7f50b22",
  project_no: 31,
  project_name: "Voice Study",
  mid: "4909",
  datapath: "/vault/img/000101",
  in_scope: true,
  erasure_status: null,
  erasure_status_at: null,
  erasure_completed_at: null,
  erasure_reason: null,
  ...over,
});

const check = (over: Partial<DataVaultCheck> = {}): DataVaultCheck => ({
  check_uuid: crypto.randomUUID(),
  asked_at: "2026-11-13T09:00:00Z",
  automatic: false,
  asked_by_name: "Dev DPO",
  outcome: "answered",
  failure: null,
  failure_said: null,
  asset_count: 1,
  ...over,
});

const state = (over: Partial<RequestDataVault> = {}): RequestDataVault => ({
  configured: true,
  may_check: true,
  why_not: null,
  answer: null,
  assets: [],
  last_failure: null,
  erasure: null,
  ...over,
});

const erasure = (over: Partial<DataVaultErasure> = {}): DataVaultErasure => ({
  may_erase: true,
  why_not: null,
  to_send: 2,
  left_out: 0,
  open: 0,
  may_check_status: false,
  counts: { unanswered: 0, pending: 0, erased: 0, failed: 0, not_held: 0 },
  last_asked_at: null,
  last_failure: null,
  last_failure_said: null,
  ...over,
});

function serve(found: RequestDataVault, after?: RequestDataVault) {
  const asked = vi.fn();
  server.use(
    http.get(`${API}/requests/${UUID}/datavault`, () => HttpResponse.json(found)),
    http.post(`${API}/requests/${UUID}/datavault/check`, () => {
      asked();
      return HttpResponse.json(after ?? found);
    }),
  );
  return asked;
}

beforeEach(() => vi.clearAllMocks());

describe("Check in DataVault", () => {
  it("not set up: says who sets it up, and offers no button", async () => {
    serve(state({ configured: false, may_check: false }));
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText(/DataVault is not set up/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /check/i })).not.toBeInTheDocument();
  });

  it("asks once and shows what DataVault listed", async () => {
    const after = state({
      answer: check({ asset_count: 2 }),
      assets: [
        asset(),
        asset({
          asset_ref: "DV-AUD-000103",
          consent_uuid: null,
          consent_no: null,
          project_uuid: null,
          project_no: null,
          project_name: null,
          consent_ref: "C2",
          project_ref: "P-unknown",
          mid: null,
          datapath: null,
        }),
      ],
    });
    const asked = serve(state(), after);
    const { user } = render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText("Not checked yet.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Check in DataVault" }));
    const first = (await screen.findByText("DV-IMG-000101")).closest("tr")!;
    expect(asked).toHaveBeenCalledTimes(1);
    expect(within(first).getByRole("link", { name: "Consent ID 812" })).toHaveAttribute(
      "href",
      "/consents/9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71",
    );
    expect(within(first).getByRole("link", { name: "Voice Study" })).toBeInTheDocument();
    expect(within(first).getByText("4909")).toBeInTheDocument();
    expect(within(first).getByText("/vault/img/000101")).toBeInTheDocument();

    // What matched nothing of this person's is shown as sent, and says so.
    const second = screen.getByText("DV-AUD-000103").closest("tr")!;
    expect(within(second).getByText("C2")).toBeInTheDocument();
    expect(
      within(second).getAllByText(/Not found among this person's records/),
    ).toHaveLength(2);
    expect(within(second).queryByRole("link")).not.toBeInTheDocument();

    expect(screen.getByText(/Checked by Dev DPO/)).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith("DataVault listed 2 assets");
    expect(
      screen.getByRole("button", { name: "Check again in DataVault" }),
    ).toBeInTheDocument();
  });

  it("an answer of nothing is said as one", async () => {
    serve(
      state({ answer: check({ asset_count: 0, automatic: true, asked_by_name: null }) }),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(
      await screen.findByText("DataVault holds nothing of this person."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Checked by the platform when holders were found/),
    ).toBeInTheDocument();
  });

  it("a failed attempt is said beside the earlier answer, which stays", async () => {
    serve(
      state({
        answer: check(),
        assets: [asset()],
        last_failure: check({
          outcome: "failed",
          failure: "timeout",
          failure_said: "DataVault did not answer in time.",
          asset_count: 0,
        }),
      }),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    const alert = await screen.findByText(/DataVault did not answer in time\./);
    expect(alert).toHaveTextContent(/The earlier answer is shown below/);
    expect(screen.getByText("DV-IMG-000101")).toBeInTheDocument();
  });

  it("a request that cannot be asked about says why", async () => {
    serve(state({ may_check: false, why_not: "RR-2026-0007 is closed." }));
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText("RR-2026-0007 is closed.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /check/i })).not.toBeInTheDocument();
  });

  it("an API without the route yet leaves the page as it was", async () => {
    server.use(
      http.get(
        `${API}/requests/${UUID}/datavault`,
        () => new HttpResponse(null, { status: 404 }),
      ),
    );
    const { container } = render(<RequestDataVaultCard requestUuid={UUID} />);
    await vi.waitFor(() => expect(container.querySelector(".animate-pulse")).toBeNull());
    expect(screen.queryByText("DataVault")).not.toBeInTheDocument();
  });
});

describe("the platform's own check", () => {
  /** Nothing yet on the first read, the answer on a later one: as when the
   *  worker finishes a moment after the request was started. */
  function landsLater() {
    const reads = vi.fn();
    server.use(
      http.get(`${API}/requests/${UUID}/datavault`, () => {
        reads();
        return HttpResponse.json(
          reads.mock.calls.length < 3
            ? state()
            : state({
                answer: check({ automatic: true, asked_by_name: null }),
                assets: [asset()],
              }),
        );
      }),
    );
    return reads;
  }

  it("is looked for again until it lands, when a DCO Admin is among the holders", async () => {
    const reads = landsLater();
    render(
      <RequestDataVaultCard
        requestUuid={UUID}
        platformAsks
        holdersReadAt="2026-11-13T09:00:00Z"
        watchEveryMs={20}
      />,
    );
    expect(
      await screen.findByText(
        /the platform asks DataVault by itself; its answer appears here/,
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("DV-IMG-000101")).toBeInTheDocument();
    expect(
      screen.getByText(/Checked by the platform when holders were found/),
    ).toBeInTheDocument();
    // Answered: it stops looking.
    const settled = reads.mock.calls.length;
    await new Promise((done) => setTimeout(done, 120));
    expect(reads.mock.calls.length).toBe(settled);
  });

  it("is not looked for when nothing says the platform will ask", async () => {
    const reads = landsLater();
    render(<RequestDataVaultCard requestUuid={UUID} watchEveryMs={20} />);
    expect(await screen.findByText("Not checked yet.")).toBeInTheDocument();
    await new Promise((done) => setTimeout(done, 120));
    expect(reads).toHaveBeenCalledTimes(1);
  });

  it("is not looked for while DataVault is not set up", async () => {
    const reads = vi.fn();
    server.use(
      http.get(`${API}/requests/${UUID}/datavault`, () => {
        reads();
        return HttpResponse.json(state({ configured: false, may_check: false }));
      }),
    );
    render(<RequestDataVaultCard requestUuid={UUID} platformAsks watchEveryMs={20} />);
    expect(await screen.findByText(/DataVault is not set up/)).toBeInTheDocument();
    await new Promise((done) => setTimeout(done, 120));
    expect(reads).toHaveBeenCalledTimes(1);
  });
});

describe("DataVault on a DCO Admin's ticket", () => {
  it("lists the project's assets, without links to pages a holder may not open", async () => {
    server.use(
      http.get(`${API}/tickets/${UUID}/datavault`, () =>
        HttpResponse.json({ asked_at: "2026-11-13T09:00:00Z", assets: [asset()] }),
      ),
    );
    render(<TicketDataVault holderUuid={UUID} />);
    const row = (await screen.findByText("DV-IMG-000101")).closest("tr")!;
    expect(within(row).getByText("Consent ID 812")).toBeInTheDocument();
    expect(within(row).getByText("Voice Study")).toBeInTheDocument();
    expect(within(row).queryByRole("link")).not.toBeInTheDocument();
    expect(within(row).queryByText(/Not found among/)).not.toBeInTheDocument();
  });

  it("shows nothing on any other ticket", async () => {
    const called = vi.fn();
    server.use(
      http.get(`${API}/tickets/${UUID}/datavault`, () => {
        called();
        return HttpResponse.json({ asked_at: null, assets: [] });
      }),
    );
    const { container } = render(<TicketDataVault holderUuid={UUID} />);
    await vi.waitFor(() => expect(called).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Erase in DataVault, on an erasure request", () => {
  function serveErasure(
    found: RequestDataVault,
    erased: RequestDataVault,
    asked?: RequestDataVault,
  ) {
    const calls = { erase: vi.fn(), status: vi.fn() };
    server.use(
      http.get(`${API}/requests/${UUID}/datavault`, () => HttpResponse.json(found)),
      http.post(`${API}/requests/${UUID}/datavault/erase`, () => {
        calls.erase();
        return HttpResponse.json(erased);
      }),
      http.post(`${API}/requests/${UUID}/datavault/erase/status`, () => {
        calls.status();
        return HttpResponse.json(asked ?? erased);
      }),
    );
    return calls;
  }

  const listed = [
    asset(),
    asset({ asset_ref: "DV-VID-000102", consent_no: 813, consent_uuid: null }),
  ];

  it("asks first, with the count, and sends nothing on a no", async () => {
    const calls = serveErasure(
      state({ answer: check({ asset_count: 2 }), assets: listed, erasure: erasure() }),
      state(),
    );
    const { user } = render(<RequestDataVaultCard requestUuid={UUID} />);
    await user.click(
      await screen.findByRole("button", { name: "Erase in DataVault (2 assets)" }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("Tell DataVault to erase 2 assets?");
    expect(dialog).toHaveTextContent(/cannot be taken back/);
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(calls.erase).not.toHaveBeenCalled();
  });

  it("sends on a yes and shows where each asset stands", async () => {
    const after = state({
      answer: check({ asset_count: 2 }),
      assets: [
        asset({ erasure_status: "erased", erasure_completed_at: "2026-11-13T09:30:00Z" }),
        asset({ asset_ref: "DV-VID-000102", erasure_status: "pending" }),
      ],
      erasure: erasure({
        may_erase: false,
        why_not: "Everything this request reaches has been sent to DataVault.",
        to_send: 0,
        open: 1,
        may_check_status: true,
        counts: { unanswered: 0, pending: 1, erased: 1, failed: 0, not_held: 0 },
        last_asked_at: "2026-11-13T09:30:00Z",
      }),
    });
    const calls = serveErasure(
      state({ answer: check({ asset_count: 2 }), assets: listed, erasure: erasure() }),
      after,
    );
    const { user } = render(<RequestDataVaultCard requestUuid={UUID} />);
    await user.click(
      await screen.findByRole("button", { name: "Erase in DataVault (2 assets)" }),
    );
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "Erase in DataVault",
      }),
    );
    await vi.waitFor(() => expect(calls.erase).toHaveBeenCalledTimes(1));
    const first = (await screen.findByText("Erased")).closest("tr")!;
    expect(within(first).getByText("DV-IMG-000101")).toBeInTheDocument();
    const second = screen.getByText("DV-VID-000102").closest("tr")!;
    expect(within(second).getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText(/1 erased · 1 pending/)).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith("Sent to DataVault", "1 erased · 1 pending");
    // Sent: the button stays, greyed out, with the reason beside it.
    expect(screen.getByRole("button", { name: "Erase in DataVault" })).toBeDisabled();
    expect(
      screen.getByText("Everything this request reaches has been sent to DataVault."),
    ).toBeInTheDocument();
    expect(screen.getByText(/1 asset is still with DataVault/)).toBeInTheDocument();
  });

  it("checks status, once, and says what came back", async () => {
    const pendingNow = state({
      answer: check(),
      assets: [asset({ erasure_status: "pending" })],
      erasure: erasure({
        may_erase: false,
        why_not: "Everything this request reaches has been sent to DataVault.",
        to_send: 0,
        open: 1,
        may_check_status: true,
        counts: { unanswered: 0, pending: 1, erased: 0, failed: 0, not_held: 0 },
      }),
    });
    const done = state({
      answer: check(),
      assets: [asset({ erasure_status: "erased" })],
      erasure: erasure({
        may_erase: false,
        why_not: "Everything this request reaches has been sent to DataVault.",
        to_send: 0,
        counts: { unanswered: 0, pending: 0, erased: 1, failed: 0, not_held: 0 },
      }),
    });
    const calls = serveErasure(pendingNow, pendingNow, done);
    const { user } = render(<RequestDataVaultCard requestUuid={UUID} />);
    await user.click(await screen.findByRole("button", { name: "Check status" }));
    await vi.waitFor(() => expect(calls.status).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Erased")).toBeInTheDocument();
    expect(toast.success).toHaveBeenCalledWith("DataVault answered", "1 erased");
    expect(screen.queryByRole("button", { name: "Check status" })).not.toBeInTheDocument();
    expect(calls.erase).not.toHaveBeenCalled();
  });

  it("an ask that was not answered says so, and that Check status sends it again", async () => {
    serveErasure(
      state({
        answer: check(),
        assets: [asset({ erasure_status: "unanswered" })],
        erasure: erasure({
          may_erase: false,
          why_not: "Everything this request reaches has been sent to DataVault.",
          to_send: 0,
          open: 1,
          may_check_status: true,
          counts: { unanswered: 1, pending: 0, erased: 0, failed: 0, not_held: 0 },
          last_failure: "timeout",
          last_failure_said: "DataVault did not answer in time.",
        }),
      }),
      state(),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText("Sent, no answer yet")).toBeInTheDocument();
    expect(
      screen.getByText(/DataVault did not answer in time\. The instruction is kept/),
    ).toBeInTheDocument();
  });

  it("greys the button out with the server's reason while it may not be pressed", async () => {
    serveErasure(
      state({
        answer: check(),
        assets: [asset()],
        erasure: erasure({
          may_erase: false,
          to_send: 1,
          why_not:
            "A legal hold stands on this person. Nothing is erased in DataVault until it is released.",
        }),
      }),
      state(),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    const button = await screen.findByRole("button", { name: "Erase in DataVault" });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription(/A legal hold stands on this person/);
  });

  it("marks what a request about one consent leaves out, and does not send it", async () => {
    serveErasure(
      state({
        answer: check({ asset_count: 2 }),
        assets: [asset(), asset({ asset_ref: "DV-OTHER-1", in_scope: false })],
        erasure: erasure({ to_send: 1, left_out: 1 }),
      }),
      state(),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    const other = (await screen.findByText("DV-OTHER-1")).closest("tr")!;
    expect(
      within(other).getByText("Left out: this request does not reach it"),
    ).toBeInTheDocument();
    const mine = screen.getByText("DV-IMG-000101").closest("tr")!;
    expect(within(mine).getByText("Not sent")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Erase in DataVault (1 asset)" }),
    ).toBeEnabled();
    expect(screen.getByText(/1 asset DataVault listed is left out/)).toBeInTheDocument();
  });

  it("offers nothing to a reader who may not act on the request", async () => {
    serveErasure(
      state({
        may_check: false,
        answer: check(),
        assets: [asset()],
        erasure: erasure({ may_erase: false, why_not: null }),
      }),
      state(),
    );
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText("DV-IMG-000101")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /erase/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check status" })).not.toBeInTheDocument();
  });

  it("shows no erasure on any other request", async () => {
    serve(state({ answer: check(), assets: [asset()] }));
    render(<RequestDataVaultCard requestUuid={UUID} />);
    expect(await screen.findByText("DV-IMG-000101")).toBeInTheDocument();
    expect(screen.queryByText("Erasure in DataVault")).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Erasure" })).not.toBeInTheDocument();
  });

  it("says the statuses in order and leaves out those with none", () => {
    expect(
      erasureSummary(
        erasure({
          counts: { unanswered: 1, pending: 2, erased: 3, failed: 1, not_held: 0 },
        }),
      ),
    ).toBe("3 erased · 2 pending · 1 not answered yet · 1 not erased");
    expect(erasureSummary(erasure())).toBe("");
  });
});
