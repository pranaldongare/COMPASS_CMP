/**
 * Automated accessibility checks on the key screens (2026-10-10).
 *
 * axe finds what a linter cannot - contrast on the rendered page, names on
 * controls built at runtime, landmarks, ARIA that does not add up. It does not
 * replace a keyboard and screen-reader pass; it catches regressions between
 * them. Serious and critical findings fail the run.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

const SCREENS: { role: string; path: string }[] = [
  { role: "dpo", path: "/dashboard" },
  { role: "dpo", path: "/projects" },
  { role: "dpo", path: "/consents" },
  { role: "dpo", path: "/requests" },
  { role: "dpo", path: "/sources" },
  { role: "dpo", path: "/messages" },
  { role: "dco", path: "/dashboard" },
  { role: "admin", path: "/users" },
];

for (const { role, path } of SCREENS) {
  test.describe(`${path} as ${role}`, () => {
    test.use({ storageState: statePath(role) });

    test("has no serious accessibility violations", async ({ page }) => {
      await page.goto(path);
      await page.locator("main h1").first().waitFor();
      // Lists and figures arrive after the heading.
      await page.waitForLoadState("networkidle");
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        // The framework's development overlay is not ours.
        .exclude("nextjs-portal")
        .analyze();
      const serious = results.violations
        .filter((v) => v.impact === "serious" || v.impact === "critical")
        .map((v) => `${v.id}: ${v.help} (${v.nodes.length}) ${v.nodes[0]?.target.join(" ")}`);
      expect(serious, serious.join("\n")).toEqual([]);
    });
  });
}
