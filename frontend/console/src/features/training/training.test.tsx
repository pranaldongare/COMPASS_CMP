/**
 * Training (2026-11-24): each staff role's course, step by step, after
 * signing in.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

import TrainingModulePage from "@/app/(app)/training/[id]/page";
import TrainingPage from "@/app/(app)/training/page";
import { ALL_STAFF, MODULES, modulesFor } from "@/features/training/content";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor, within } from "@/test/render";
import type { Me, Role } from "@/types";

const route = { id: "getting-started" };
vi.mock("next/navigation", () => ({
  useParams: () => route,
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => `/training/${route.id}`,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

let me: Me | null = null;
vi.mock("@/providers", () => ({
  useAuth: () => ({ me }),
  useOptionalAuth: () => ({ me }),
}));

beforeEach(() => {
  window.localStorage.clear();
});

describe("the course content", () => {
  it("gives every staff role a course of its own, and none to a data principal", () => {
    for (const role of ALL_STAFF) {
      const mine = modulesFor(role);
      expect(mine.length, role).toBeGreaterThanOrEqual(3);
      // Something beyond what everybody takes: the role's own work.
      expect(
        mine.some((m) => m.roles.length < ALL_STAFF.length),
        role,
      ).toBe(true);
    }
    expect(modulesFor("data_subject" as Role)).toEqual([]);
  });

  it("holds together: unique ids, steps, and answers that exist", () => {
    expect(new Set(MODULES.map((m) => m.id)).size).toBe(MODULES.length);
    for (const m of MODULES) {
      expect(m.steps.length, m.id).toBeGreaterThan(0);
      expect(m.check.length, m.id).toBeGreaterThan(0);
      for (const q of m.check) {
        expect(q.answer, `${m.id}: ${q.question}`).toBeLessThan(q.options.length);
        expect(q.why.length).toBeGreaterThan(0);
      }
    }
  });
});

describe("the course page", () => {
  it("lists the reader's modules with where they are in each", async () => {
    me = makeMe({ role: "dco" });
    render(<TrainingPage />);

    const list = await screen.findByRole("list", { name: "Modules" });
    const titles = within(list)
      .getAllByRole("heading", { level: 3 })
      .map((h) => h.textContent);
    expect(titles).toEqual(modulesFor("dco").map((m) => m.title));
    expect(titles).toContain("Collection sites and consent links");
    expect(titles).not.toContain("Responding to a personal data breach");
    expect(screen.getByRole("link", { name: /Start: Getting started/ })).toHaveAttribute(
      "href",
      "/training/getting-started",
    );
  });
});

describe("a module", () => {
  it("walks the steps, checks the answers, and remembers completion", async () => {
    me = makeMe({ role: "management" });
    route.id = "reports-and-schedules";
    const mod = MODULES.find((m) => m.id === route.id)!;
    const { user } = render(<TrainingModulePage />);

    expect(
      await screen.findByRole("heading", { name: mod.steps[0].title }),
    ).toBeInTheDocument();
    // The page it happens on is one management reaches: offered, and said to be live.
    expect(screen.getByRole("link", { name: /Open Analytics/ })).toHaveAttribute(
      "href",
      "/analytics",
    );
    expect(screen.getByText(/anything you do there is real/)).toBeInTheDocument();

    for (let i = 0; i < mod.steps.length; i++) {
      await user.click(screen.getByRole("button", { name: /^Done - / }));
    }
    // Focus follows the content, for a keyboard or screen reader.
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Check your understanding" }),
      ).toHaveFocus(),
    );

    // Wrong first: told why, not passed.
    const q = mod.check[0];
    const wrong = q.options.findIndex((_, i) => i !== q.answer);
    await user.click(screen.getAllByRole("radio")[wrong]);
    await user.click(screen.getByRole("button", { name: "Check answers" }));
    expect(screen.getByText(/Not quite\./)).toBeInTheDocument();
    expect(screen.queryByText("Module complete")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("radio")[q.answer]);
    await user.click(screen.getByRole("button", { name: "Check answers" }));
    expect(await screen.findByText("Module complete")).toBeInTheDocument();

    const saved = JSON.parse(
      window.localStorage.getItem(`cmp.training.v1.${me.uuid}`) ?? "{}",
    );
    expect(saved[mod.id].passed).toBe(true);
    expect(saved[mod.id].completedAt).toBeTruthy();
  });

  it("offers no link to a page the reader's role cannot open", async () => {
    // The scorecard module names Analytics; a module page only links pages
    // the server granted, so a role without them sees the words alone.
    me = makeMe({ role: "legal", nav: ["dashboard", "tickets", "training"] });
    route.id = "reading-the-scorecard";
    render(<TrainingModulePage />);

    expect(
      await screen.findByRole("heading", { name: "Choose the period and the office" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Open Analytics/ })).not.toBeInTheDocument();
  });

  it("refuses a module that is not the reader's", async () => {
    me = makeMe({ role: "hr_user" });
    route.id = "breach-response";
    render(<TrainingModulePage />);

    expect(
      await screen.findByText("This module is not part of your training"),
    ).toBeInTheDocument();
  });
});
