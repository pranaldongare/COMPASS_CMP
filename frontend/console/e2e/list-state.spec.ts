/**
 * A list keeps its filter through reload, a shared link, and Back from a row
 * (review 2026-10-01, UX-5).
 *
 * The filter was read from the URL once and then held in the page: reload, or
 * open a notice and press Back, and the list came back unfiltered on its first
 * page. The URL is the list's state now.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe("list state lives in the URL", () => {
  test.use({ storageState: statePath("dpo") });

  test("filter, reload, open a row, come back: still filtered", async ({ page }) => {
    await page.goto("/notices");
    const status = page.getByLabel("Status");
    await status.selectOption("published");
    await expect(page).toHaveURL(/[?&]status=published/);

    await page.reload();
    await expect(page.getByLabel("Status")).toHaveValue("published");

    const first = page.locator('a[href^="/notices/"]').first();
    await first.waitFor({ timeout: 15_000 });
    await first.click();
    await expect(page).toHaveURL(/\/notices\/[0-9a-f-]{36}/);

    await page.goBack();
    await expect(page).toHaveURL(/[?&]status=published/);
    await expect(page.getByLabel("Status")).toHaveValue("published");
  });
});
