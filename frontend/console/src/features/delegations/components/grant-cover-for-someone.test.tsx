/**
 * An administrator arranges cover for somebody away (2026-10-09): choose
 * whose work, then a colleague in their role - the server's list for that
 * person - and the arrangement names them as the delegator.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { GrantCoverForm } from "@/features/delegations/components/grant-cover-form";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "admin" }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

const AWAY = "55555555-5555-4555-8555-555555555555";
const COVER = "66666666-6666-4666-8666-666666666666";

describe("GrantCoverForm, for someone", () => {
  it("asks whose work, offers their colleagues, and names them as the delegator", async () => {
    let asked: string | null = null;
    let sent: unknown = null;
    server.use(
      http.get(`${API}/users/staff`, () =>
        HttpResponse.json([
          { uuid: AWAY, full_name: "Asha Rao", email: "asha@example.org", role: "dco" },
          { uuid: "77777777-7777-4777-8777-777777777777", full_name: "Rnd Person", email: "r@example.org", role: "rnd_user" },
        ]),
      ),
      http.get(`${API}/delegations/candidates`, ({ request }) => {
        asked = new URL(request.url).searchParams.get("for_user");
        return HttpResponse.json([{ uuid: COVER, full_name: "Ravi Kumar", email: "ravi@example.org" }]);
      }),
      http.post(`${API}/delegations`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ delegation_uuid: "x", grants_access: true, message: "ok" }, { status: 201 });
      }),
    );
    const { user } = render(<GrantCoverForm forSomeone onDone={() => undefined} />);

    expect(await screen.findByRole("option", { name: /asha rao/i })).toBeInTheDocument();
    // An R&D User's work cannot be covered, so they are not offered.
    expect(screen.queryByRole("option", { name: /rnd person/i })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/whose work/i), AWAY);
    await user.selectOptions(await screen.findByLabelText(/who takes over/i), await screen.findByRole("option", { name: /ravi kumar/i }));
    expect(asked).toBe(AWAY);
    await user.click(screen.getByRole("button", { name: "Delegate" }));
    await vi.waitFor(() =>
      expect(sent).toMatchObject({ delegator_user_uuid: AWAY, delegate_user_uuid: COVER }),
    );
  });
});
