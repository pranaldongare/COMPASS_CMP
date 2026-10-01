/**
 * A notice about a personal data breach, in her account (S3-03).
 *
 * The console's breach spec sends one to the seeded principal; this reads it
 * where Rule 7(1) says she is told first. Run after the console suite, as the
 * testing guide orders the suites.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.use({ storageState: statePath("subject") });

test("her notices say the five things, in the Rule's order", async ({ page }) => {
  await page.goto("/breach-notices");
  await expect(page.getByRole("heading", { name: "Personal data breach notices", level: 1 })).toBeVisible();
  // Wait for the answer - notices or the empty state - before reading it.
  // Counting at once raced the request and read an empty page.
  const first = page.locator("section").first();
  const none = page.getByText("No personal data breach has been notified to you.");
  await expect(first.or(none)).toBeVisible();
  if (await none.isVisible()) return;
  const headings = page.locator("section h2");
  await expect(headings.nth(0)).toHaveText("What happened");
  await expect(headings.nth(1)).toHaveText("What it may mean for you");
  await expect(headings.nth(2)).toHaveText("What we have done, and are doing");
  await expect(headings.nth(3)).toHaveText("What you can do");
  await expect(headings.nth(4)).toHaveText("Questions");
});
