/**
 * The cover form offers the colleagues the delegations API names - not the
 * users register, which only the DPO and administrator may read, so a DCO was
 * always offered nobody.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { GrantCoverForm } from "@/features/delegations/components/grant-cover-form";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "dco" }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

describe("GrantCoverForm", () => {
  it("offers the colleagues the server names", async () => {
    server.use(
      http.get(`${API}/delegations/candidates`, () =>
        HttpResponse.json([{ uuid: "44444444-4444-4444-8444-444444444444", full_name: "Ravi Kumar", email: "ravi@example.org" }]),
      ),
    );
    render(<GrantCoverForm onDone={() => undefined} />);
    expect(await screen.findByRole("option", { name: /ravi kumar/i })).toBeInTheDocument();
    expect(screen.queryByText(/nobody else in your role/i)).not.toBeInTheDocument();
  });

  it("says so when there really is nobody", async () => {
    server.use(http.get(`${API}/delegations/candidates`, () => HttpResponse.json([])));
    render(<GrantCoverForm onDone={() => undefined} />);
    expect(await screen.findByText(/nobody else in your role/i)).toBeInTheDocument();
  });
});
