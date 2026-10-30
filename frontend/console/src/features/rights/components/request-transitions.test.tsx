/**
 * Back from collating (2026-10-08): a request moved to collating too soon goes
 * back - to add a holder, or ask one for more - with a reason the trail keeps.
 * The summary's Next never points backwards.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NextBar } from "@/features/rights/components/next-bar";
import { RequestSummary } from "@/features/rights/components/request-summary";
import { RequestTransitions } from "@/features/rights/components/staff-actions";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: null }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const collating = makeRequestDetail({
  status: "collating",
  transitions: [
    { to: "closed", allowed: true, via: "respond" },
    { to: "awaiting_holders", allowed: true, via: "transition", reason_required: true },
  ],
});

describe("Back from collating", () => {
  it("asks why, then moves back with the reason's code", async () => {
    let sent: unknown = null;
    server.use(
      http.post(`${API}/requests/${collating.request_uuid}/transition`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...collating, status: "awaiting_holders" });
      }),
    );
    const { user } = render(<RequestTransitions request={collating} />);

    const back = screen.getByRole("button", { name: /back to awaiting holders/i });
    expect(back).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Why"), "new_holder");
    await user.click(back);
    await vi.waitFor(() => expect(sent).toEqual({ to: "awaiting_holders", reason: "new_holder" }));
  });

  it("is never the summary's next move", () => {
    render(<RequestSummary request={collating} actionsHref="#actions" />);
    expect(screen.getByRole("link", { name: /respond and close/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /awaiting holders/i })).not.toBeInTheDocument();
  });
});

// Started, nobody asked yet (2026-10-30): the server allows collating at once,
// for nothing to ask anyone, and the page offered that as the next step while
// the bar above said Go to Holders. Finding the holders comes first,
// everywhere; collating stays, as the exception.
const started = makeRequestDetail({
  status: "in_progress",
  holders: [],
  transitions: [
    {
      to: "awaiting_holders",
      allowed: false,
      via: "transition",
      blocked_by: "No tickets have been issued yet",
    },
    { to: "collating", allowed: true, via: "transition" },
  ],
});

describe("Started, with nobody asked yet", () => {
  it("leads with the holders everywhere, and keeps collating as the exception", () => {
    render(
      <>
        <NextBar request={started} tab="overview" onGo={vi.fn()} />
        <RequestSummary request={started} actionsHref="#actions" />
        <RequestTransitions request={started} />
      </>,
    );
    // The bar, the summary's Next and the card agree.
    expect(screen.getAllByText("Find who holds the data").length).toBe(3);
    expect(screen.getByRole("link", { name: /find who holds the data/i })).toHaveAttribute(
      "href",
      "#holders",
    );
    expect(screen.getByRole("link", { name: /go to holders/i })).toHaveAttribute(
      "href",
      "#holders",
    );
    expect(screen.getByText(/nothing to ask anyone\? move to collating/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /move to collating/i })).not.toBeInTheDocument();
  });
});
