/**
 * The seed accounts on the sign-in page (2026-10-06): whatever the API lists
 * - its own logins still on the seed password - with the password and a
 * button that fills the form. Nothing at all when the API lists none, and
 * nothing unless the development switch is on.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { SeedAccounts } from "@/features/dev/seed-accounts";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/lib/dev/dev-client", () => ({ DEV_CODES_ON: true }));

describe("SeedAccounts", () => {
  it("lists the accounts with the password, and Use fills the form", async () => {
    server.use(
      http.get(`${API}/dev/seed-accounts`, () =>
        HttpResponse.json({
          password: "SeedPassw0rd!2026",
          accounts: [
            { login: "dpo@cmp.local", role: "dpo", role_title: "Data Protection Officer" },
            { login: "dco@cmp.local", role: "dco", role_title: "Data Collection Owner" },
          ],
        }),
      ),
    );
    const onUse = vi.fn();
    const { user } = render(<SeedAccounts onUse={onUse} />);

    await user.click(await screen.findByText("Development accounts (2)"));
    expect(screen.getByText("SeedPassw0rd!2026")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use dco@cmp.local" }));
    expect(onUse).toHaveBeenCalledWith("dco@cmp.local", "SeedPassw0rd!2026");
  });

  it("shows nothing when no account is still on the seed password", async () => {
    let asked = false;
    server.use(
      http.get(`${API}/dev/seed-accounts`, () => {
        asked = true;
        return HttpResponse.json({ password: null, accounts: [] });
      }),
    );
    const { container } = render(<SeedAccounts onUse={vi.fn()} />);
    await vi.waitFor(() => expect(asked).toBe(true));
    expect(container).toBeEmptyDOMElement();
  });
});
