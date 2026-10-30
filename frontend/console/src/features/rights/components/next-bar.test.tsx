/**
 * The next move on a request, on every tab (2026-10-30): verify, classify,
 * claim, start, then the holders - each named in the order the server checks
 * them, made from the bar when it is one button, otherwise a way to its tab.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NextBar, nextStep } from "@/features/rights/components/next-bar";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";
import type { RightsRequestDetail } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const BLOCKED = (blocked_by: string): RightsRequestDetail["transitions"] => [
  { to: "in_progress", allowed: false, via: "transition", blocked_by },
];

function received(overrides: Partial<RightsRequestDetail> = {}): RightsRequestDetail {
  return makeRequestDetail({
    status: "received",
    verification_status: "verified",
    classified_at: "2026-10-30T10:27:00Z",
    office: "rnd",
    transitions: [{ to: "in_progress", allowed: true, via: "transition" }],
    ...overrides,
  });
}

describe("nextStep", () => {
  it("asks for identity, then the classification, then a claim", () => {
    expect(
      nextStep(
        received({
          verification_status: "pending",
          transitions: BLOCKED("Identity is not verified"),
        }),
      ),
    ).toMatchObject({ title: "Verify who it is", go: "identity" });
    expect(
      nextStep(
        received({
          classified_at: null,
          transitions: BLOCKED("The request has not been classified as a rights request"),
        }),
      ),
    ).toMatchObject({ title: "Confirm what kind of request it is", go: "identity" });
    expect(
      nextStep(
        received({ office: null, transitions: BLOCKED("Claim it for your office first") }),
      ),
    ).toMatchObject({ title: "Claim it for your office", claim: true });
  });

  it("starts the work when nothing stands in the way, then points at the holders", () => {
    expect(nextStep(received())).toMatchObject({ move: "in_progress" });
    expect(
      nextStep(
        received({
          status: "in_progress",
          transitions: [
            {
              to: "collating",
              allowed: false,
              via: "transition",
              blocked_by: "Tickets are outstanding",
            },
          ],
        }),
      ),
    ).toMatchObject({ title: "Find who holds the data", go: "holders" });
  });

  it("is not there for a closed request, or for someone offered no move", () => {
    expect(nextStep(received({ status: "closed" }))).toBeNull();
    expect(nextStep(received({ transitions: [] }))).toBeNull();
  });
});

describe("NextBar", () => {
  it("claims a request in the shared intake from the bar", async () => {
    let claimed = false;
    server.use(
      http.post(`${API}/requests/:uuid/claim`, () => {
        claimed = true;
        return HttpResponse.json(received());
      }),
    );
    const request = received({
      office: null,
      transitions: BLOCKED("Claim it for your office first"),
    });
    const { user } = render(<NextBar request={request} tab="identity" onGo={vi.fn()} />);
    expect(screen.getByText("Claim it for your office")).toBeInTheDocument();
    expect(screen.getByText(/Then: move to in progress → Holders/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Claim for my office" }));
    await vi.waitFor(() => expect(claimed).toBe(true));
  });

  it("opens the tab the move is made on, and offers no button on that tab", async () => {
    const onGo = vi.fn();
    const request = received({
      verification_status: "pending",
      transitions: BLOCKED("Identity is not verified"),
    });
    const { user, rerender } = render(
      <NextBar request={request} tab="overview" onGo={onGo} />,
    );
    await user.click(screen.getByRole("button", { name: /go to identity/i }));
    expect(onGo).toHaveBeenCalledWith("identity");

    rerender(<NextBar request={request} tab="identity" onGo={onGo} />);
    expect(screen.getByText("Verify who it is")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
