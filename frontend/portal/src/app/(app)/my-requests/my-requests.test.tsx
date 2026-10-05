/**
 * A link that names a request opens that request (UX review 2026-10-05).
 *
 * "Our response to RR-2026-000002 is ready" opened the top of My requests, at
 * a different, newer reference, with nothing expanded. The link now carries
 * the request (`?request=`) and the page opens that card; several responses
 * open the "ready to download" view (`?view=ready`).
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MyRequestsPage from "@/app/(app)/my-requests/page";
import { makeMyRequest } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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
  download_available: true,
  download_expires_at: "2026-11-01T00:00:00Z",
  received_at: "2026-09-01T10:00:00Z",
});

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  server.use(http.get(`${API}/me/requests`, () => HttpResponse.json([NEWER, READY])));
});

describe("My requests opened from a link", () => {
  it("opens the request the link names", async () => {
    window.history.replaceState(null, "", `/my-requests?request=${READY.request_uuid}`);
    render(<MyRequestsPage />);
    const opened = await screen.findByRole("button", { expanded: true });
    const card = opened.closest("[id^='request-']");
    expect(card).toHaveTextContent(READY.reference);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it("shows only the responses ready to download", async () => {
    window.history.replaceState(null, "", "/my-requests?view=ready");
    render(<MyRequestsPage />);
    expect(await screen.findByText(READY.reference)).toBeInTheDocument();
    expect(screen.queryByText(NEWER.reference)).not.toBeInTheDocument();
  });
});

describe("a folded request card", () => {
  const ANSWERED = { ...READY, response_text: "Here is everything we hold about you." };

  beforeEach(() => {
    window.history.replaceState(null, "", "/my-requests");
    server.use(http.get(`${API}/me/requests`, () => HttpResponse.json([NEWER, ANSWERED])));
  });

  it("is a summary, with the details one click away", async () => {
    // 48 requests used to be 48 full cards, every response written out (UX
    // review 2026-10-05). Folded, a card says what it is and where it stands.
    const { user } = render(<MyRequestsPage />);
    await screen.findByText(ANSWERED.reference);

    expect(screen.queryByText(ANSWERED.response_text)).not.toBeInTheDocument();
    expect(screen.queryByText(/the path/i)).not.toBeInTheDocument();

    const card = screen.getByText(ANSWERED.reference).closest("[id^='request-']") as HTMLElement;
    const toggle = card.querySelector("button[aria-expanded]") as HTMLButtonElement;
    expect(toggle).toHaveTextContent("Show details");
    await user.click(toggle);

    expect(screen.getByText(ANSWERED.response_text)).toBeInTheDocument();
    expect(toggle).toHaveTextContent("Hide details");
  });

  it("still offers a response that is ready to download", async () => {
    // The download window closes; folding must not hide it.
    render(<MyRequestsPage />);
    await screen.findByText(ANSWERED.reference);

    expect(screen.getByText(/our response is ready/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /download the file/i })).toBeInTheDocument();
  });
});
