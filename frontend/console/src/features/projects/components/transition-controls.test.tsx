/**
 * A project's one-click moves ask first (2026-11-12).
 *
 * Submitting for approval emails every DPO, and closing is final and stops
 * the project's consent links - each used to happen on one click. The pop-up
 * says who is told and what cannot be undone; Cancel moves nothing.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { TransitionControls } from "@/features/projects/components/transition-controls";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const PROJECT = "11111111-2222-4333-8444-555555555555";

function serve(current: string, to: string) {
  const moved: Array<{ to: string }> = [];
  server.use(
    http.get(`${API}/projects/${PROJECT}/transitions`, () =>
      HttpResponse.json({ current, available: [{ to, allowed: true, blocked_by: null, blockers: [] }] }),
    ),
    http.post(`${API}/projects/${PROJECT}/transition`, async ({ request }) => {
      moved.push((await request.json()) as { to: string });
      return HttpResponse.json({ from: current, to });
    }),
  );
  return moved;
}

describe("a project's one-click moves", () => {
  it("asks before submitting for approval, saying every DPO is emailed", async () => {
    const moved = serve("in_draft", "pending_approval");
    const { user } = render(<TransitionControls projectUuid={PROJECT} currentStatus="in_draft" />);

    await user.click(await screen.findByRole("button", { name: /submit for approval/i }));
    const question = await screen.findByRole("dialog", { name: "Submit this project for approval?" });
    expect(within(question).getByText(/Every DPO is emailed that it is waiting for a decision\./)).toBeInTheDocument();
    await user.click(within(question).getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(moved).toEqual([]);

    await user.click(screen.getByRole("button", { name: /submit for approval/i }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Submit for approval" }),
    );
    await vi.waitFor(() => expect(moved.map((m) => m.to)).toEqual(["pending_approval"]));
  });

  it("asks before closing, saying it is final and the consent links stop", async () => {
    const moved = serve("approved", "closed");
    const { user } = render(<TransitionControls projectUuid={PROJECT} currentStatus="approved" />);

    await user.click(await screen.findByRole("button", { name: /close project/i }));
    const question = await screen.findByRole("dialog", { name: "Close this project?" });
    expect(within(question).getByText(/a closed project cannot be reopened/)).toBeInTheDocument();
    expect(within(question).getByText(/Its consent links stop working at once/)).toBeInTheDocument();
    expect(moved).toEqual([]);

    await user.click(within(question).getByRole("button", { name: "Close project" }));
    await vi.waitFor(() => expect(moved.map((m) => m.to)).toEqual(["closed"]));
  });
});
