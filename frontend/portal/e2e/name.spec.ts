/**
 * She corrects her own name from her profile, and puts it back (s.12).
 *
 * Against the running stack: the new name is saved, sealed at rest and opened
 * for the page, and shows at once where her name is shown. The test restores
 * the seeded name before it ends, so the other specs see what they expect.
 */
import { expect, test, type Page } from "@playwright/test";

import { statePath } from "./support/session";

test.use({ storageState: statePath("subject") });

async function rename(page: Page, to: string) {
  const identity = page.getByTestId("name-view");
  await identity.getByRole("button", { name: "Change" }).click();
  const field = page.getByLabel(/^Name/);
  await field.fill(to);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByTestId("name-view").getByText(to, { exact: true })).toBeVisible();
}

test("she renames herself and the page shows it", async ({ page }) => {
  await page.goto("/account");
  const before = (await page.getByTestId("name-view").locator("span").first().textContent())?.trim() ?? "";
  expect(before).not.toBe("");
  try {
    await rename(page, `${before} Test`);
    await page.reload();
    await expect(page.getByTestId("name-view").getByText(`${before} Test`, { exact: true })).toBeVisible();
  } finally {
    await rename(page, before);
  }
});
