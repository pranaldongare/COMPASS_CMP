/**
 * The one thing each role starts from scratch, on its dashboard (2026-10-06):
 * the DPO logs an incident - thirty minutes run from first noticed - an R&D
 * user registers a project, an administrator provisions an account. The
 * collection roles start nothing without a project or a site, so get none.
 */
import { describe, expect, it, vi } from "vitest";

import { QuickAction } from "@/features/dashboard/components/quick-action";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/dashboard",
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: null }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

describe("QuickAction", () => {
  it("gives the DPO Log an incident, which opens the form there", async () => {
    const { user } = render(<QuickAction me={makeMe({ role: "dpo", writes: ["breach", "notice"] })} />);
    await user.click(screen.getByRole("button", { name: "Log an incident" }));
    expect(screen.getByRole("dialog", { name: "Log an incident" })).toBeInTheDocument();
  });

  it("gives an R&D user Register a project and an administrator Provision an account", () => {
    const { unmount } = render(<QuickAction me={makeMe({ role: "rnd_user", writes: ["project"] })} />);
    expect(screen.getByRole("button", { name: "Register a project" })).toBeInTheDocument();
    unmount();
    render(<QuickAction me={makeMe({ role: "admin", writes: ["user"] })} />);
    expect(screen.getByRole("button", { name: "Provision an account" })).toBeInTheDocument();
  });

  it("gives the collection roles nothing to start without a project or a site", () => {
    for (const role of ["dco", "dco_admin", "rco"] as const) {
      const { container, unmount } = render(<QuickAction me={makeMe({ role, writes: ["link", "site"] })} />);
      expect(container).toBeEmptyDOMElement();
      unmount();
    }
  });
});
