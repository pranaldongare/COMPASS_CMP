/**
 * A template page belongs to either office's section (0052).
 *
 * The DPO reaches templates under Notices; the Legal PoC, who has no Notices
 * section, through Notice templates. The guard takes either key for that
 * prefix, and still turns away a role with neither - and keeps the Legal PoC
 * off the DPO's notices.
 */
import { describe, expect, it, vi } from "vitest";

import { RequireSection } from "@/components/security/require-section";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import type { Me } from "@/types";

let currentMe: Me | null = makeMe();
let pathname = "/notices/templates";

vi.mock("next/navigation", () => ({ usePathname: () => pathname }));
vi.mock("@/providers", () => ({ useAuth: () => ({ me: currentMe }) }));

function page(path: string, nav: string[]) {
  pathname = path;
  currentMe = makeMe({ nav });
  render(
    <RequireSection>
      <p>The page</p>
    </RequireSection>,
  );
}

describe("RequireSection", () => {
  it("lets the DPO reach a template through Notices", () => {
    page("/notices/templates/abc", ["dashboard", "notices"]);
    expect(screen.getByText("The page")).toBeInTheDocument();
  });

  it("lets the Legal PoC reach one through Notice templates", () => {
    page("/notices/templates/abc", ["dashboard", "templates"]);
    expect(screen.getByText("The page")).toBeInTheDocument();
  });

  it("keeps the Legal PoC off the DPO's notices", () => {
    page("/notices/abc", ["dashboard", "templates"]);
    expect(screen.queryByText("The page")).not.toBeInTheDocument();
    expect(screen.getByText("Not part of your account")).toBeInTheDocument();
  });

  it("turns away a role with neither", () => {
    page("/notices/templates", ["dashboard", "projects"]);
    expect(screen.queryByText("The page")).not.toBeInTheDocument();
  });

  it("gives the HR categories to whoever was granted them", () => {
    page("/hr-categories/abc", ["dashboard", "hr-categories"]);
    expect(screen.getByText("The page")).toBeInTheDocument();
  });
});
