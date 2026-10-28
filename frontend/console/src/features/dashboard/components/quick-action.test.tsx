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
    const { user } = render(
      <QuickAction me={makeMe({ role: "dpo", writes: ["breach", "notice"] })} />,
    );
    await user.click(screen.getByRole("button", { name: "Log an incident" }));
    expect(screen.getByRole("dialog", { name: "Log an incident" })).toBeInTheDocument();
  });

  it("gives the DPO a notice template beside it, which opens the template form", async () => {
    const { user } = render(
      <QuickAction me={makeMe({ role: "dpo", writes: ["breach", "notice"] })} />,
    );
    await user.click(screen.getByRole("button", { name: "New notice template" }));
    expect(screen.getByRole("dialog", { name: "New notice template" })).toBeInTheDocument();
  });

  it("gives an R&D user Register a project and an administrator Provision an account", () => {
    const { unmount } = render(
      <QuickAction me={makeMe({ role: "rnd_user", writes: ["project"] })} />,
    );
    expect(screen.getByRole("button", { name: "Register a project" })).toBeInTheDocument();
    unmount();
    render(<QuickAction me={makeMe({ role: "admin", writes: ["user"] })} />);
    expect(
      screen.getByRole("button", { name: "Provision an account" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "New notice template" }),
    ).not.toBeInTheDocument();
  });

  it("gives the Legal PoC Log an incident, and an HR PoC New activity", async () => {
    const { unmount } = render(
      <QuickAction me={makeMe({ role: "legal", writes: ["breach", "hr_category"] })} />,
    );
    expect(screen.getByRole("button", { name: "Log an incident" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "New notice template" }),
    ).not.toBeInTheDocument();
    unmount();
    const { user } = render(
      <QuickAction me={makeMe({ role: "hr_user", writes: ["project"], nav: ["dashboard", "hr-activities"] })} />,
    );
    await user.click(screen.getByRole("button", { name: "New activity" }));
    expect(screen.getByRole("dialog", { name: "New activity" })).toBeInTheDocument();
  });

  // Nothing is created from here without its site or processor (the reason
  // these roles once had no button): the button opens the register where that
  // choice is made (2026-10-10, the role-dashboard design).
  it("sends the collection roles to the register they start from", () => {
    for (const [role, label, href] of [
      ["dco", /new consent link/i, "/links"],
      ["rco", /new consent link/i, "/links"],
      ["dco_admin", /register a data source/i, "/sources?new=1"],
    ] as const) {
      const { unmount } = render(
        <QuickAction
          me={makeMe({ role, writes: ["link", "site"], nav: ["dashboard", "links", "sources"] })}
        />,
      );
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", href);
      unmount();
    }
  });

  it("gives a collection role nothing when its register is not open to it", () => {
    const { container } = render(
      <QuickAction me={makeMe({ role: "dco", writes: [], nav: ["dashboard"] })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
