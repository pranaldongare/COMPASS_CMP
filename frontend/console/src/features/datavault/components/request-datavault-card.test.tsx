/**
 * Check in DataVault, on a rights request (0070): the card draws the server's
 * answer - whether DataVault can be asked, what it last listed, and whether a
 * later attempt failed - and the button makes the one call.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  DataVaultAsset,
  DataVaultCheck,
  RequestDataVault,
} from "@/features/datavault/api";
import { RequestDataVaultCard } from "@/features/datavault/components/request-datavault-card";
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
