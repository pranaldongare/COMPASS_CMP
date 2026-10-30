/**
 * My requests: a short list and the chosen request beside it (2026-10-30).
 *
 * A link that names a request opens that request (UX review 2026-10-05);
 * "ready to download" narrows the list to answers waiting for her. Opening a
 * request no longer unfolds the office's clock and flow diagram in the list:
 * the request shows beside it - its answer first, four plain steps, what she
 * asked - and the address names it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MyRequestsPage from "@/app/(app)/my-requests/page";
import { makeMyRequest } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => "/my-requests",
}));
vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
  useAuth: () => ({ me: null, refresh: vi.fn() }),
}));

const NEWER = makeMyRequest({
  request_uuid: "11111111-1111-4111-8111-111111111111",
  reference: "RR-2026-000009",
  received_at: "2026-10-04T10:00:00Z",
});
const READY = makeMyRequest({
  request_uuid: "22222222-2222-4222-8222-222222222222",
  reference: "RR-2026-000002",
  status: "closed",
  outcome: "complete",
  response_text: "Here is everything we hold about you.",
  responded_at: "2026-09-20T10:00:00Z",
  closed_at: "2026-09-20T10:00:00Z",
  download_available: true,
  download_expires_at: "2026-11-01T00:00:00Z",
  received_at: "2026-09-01T10:00:00Z",
});

function detail(): HTMLElement {
  return document.getElementById("request-detail") as HTMLElement;
}

beforeEach(() => {
  router.replace.mockClear();
  server.use(http.get(`${API}/me/requests`, () => HttpResponse.json([NEWER, READY])));
});

describe("My requests opened from a link", () => {
  it("shows the request the link names beside the list", async () => {
    window.history.replaceState(null, "", `/my-requests?request=${READY.request_uuid}`);
    render(<MyRequestsPage />);
    await screen.findByRole("list", { name: "Your requests" });
    expect(within(detail()).getByRole("heading")).toHaveTextContent(READY.reference);
    const row = screen.getByRole("button", { name: new RegExp(READY.reference) });
    expect(row).toHaveAttribute("aria-current", "true");
  });

  it("shows only the responses ready to download", async () => {
    window.history.replaceState(null, "", "/my-requests?view=ready");
    render(<MyRequestsPage />);
    expect(
      await screen.findByRole("button", { name: new RegExp(READY.reference) }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: new RegExp(NEWER.reference) }),
    ).not.toBeInTheDocument();
  });
});

describe("The list and the request beside it", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/my-requests");
  });

  it("shows the first request until she chooses another, and names it in the address", async () => {
    const { user } = render(<MyRequestsPage />);
    await screen.findByRole("list", { name: "Your requests" });
    expect(within(detail()).getByRole("heading")).toHaveTextContent(NEWER.reference);

    await user.click(screen.getByRole("button", { name: new RegExp(READY.reference) }));
    expect(within(detail()).getByRole("heading")).toHaveTextContent(READY.reference);
    expect(router.replace).toHaveBeenCalledWith(
      `/my-requests?request=${READY.request_uuid}`,
      { scroll: false },
    );
  });

  it("says in the list which answer is ready to download", async () => {
    render(<MyRequestsPage />);
    const row = await screen.findByRole("button", { name: new RegExp(READY.reference) });
    expect(row).toHaveTextContent(/ready to download/i);
  });

  it("puts her answer first, in plain steps, without the office's clock or flow", async () => {
    const { user } = render(<MyRequestsPage />);
    await user.click(
      await screen.findByRole("button", { name: new RegExp(READY.reference) }),
    );
    const panel = within(detail());
    expect(panel.getByRole("region", { name: "Your answer" })).toHaveTextContent(
      READY.response_text as string,
    );
    expect(panel.getByRole("button", { name: /download your data/i })).toBeInTheDocument();
    expect(panel.getByRole("list", { name: "Where it is" })).toHaveTextContent(/answered/i);
    expect(panel.queryByText(/the path/i)).not.toBeInTheDocument();
    expect(panel.queryByText(/halfway|tickets issued|collate/i)).not.toBeInTheDocument();
  });
});

describe("Make a request from Home", () => {
  it("opens the form when the link asks for it (`?new=1`)", async () => {
    window.history.replaceState(null, "", "/my-requests?new=1");
    render(<MyRequestsPage />);
    expect(
      await screen.findByRole("dialog", { name: /make a request/i }),
    ).toBeInTheDocument();
  });

  it("does not open it otherwise", async () => {
    window.history.replaceState(null, "", "/my-requests");
    render(<MyRequestsPage />);
    await screen.findByRole("list", { name: "Your requests" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
