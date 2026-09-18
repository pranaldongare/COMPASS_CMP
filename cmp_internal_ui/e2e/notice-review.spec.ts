/**
 * The officer's half of a notice, on the notice.
 *
 * An imported document leaves its purposes as drafts, because only the Privacy
 * Office may activate them and an author who could do it by uploading a file
 * would be approving their own. The officer therefore has nine decisions to
 * take, and they used to be taken somewhere else: the checklist named a purpose
 * code, and the only control that acted on it was a row in the purposes
 * register, reached by a different route, filtered by hand.
 *
 * So this asserts the two things that moved. Every blocking line points at the
 * card that clears it, and the purposes can be activated from the notice that
 * carries them, one at a time, which is the review the separate decisions are
 * there to make somebody do.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe("a draft notice, as the Privacy Office", () => {
  test.use({ storageState: statePath("dpo") });

  test("every blocker points at what clears it", async ({ page }) => {
    await page.goto("/notices?status=draft");
    const first = page.locator('a[href^="/notices/"]').first();
    await expect(first).toBeVisible({ timeout: 15_000 });
    await first.click();
    await expect(page).toHaveURL(/\/notices\/[0-9a-f-]{36}/, { timeout: 15_000 });

    await expect(page.getByText(/blocking publication/i)).toBeVisible({ timeout: 15_000 });
    const lines = page
      .getByRole("listitem")
      .filter({ hasText: /purpose|text|URL|addresses/i });
    await expect(lines.first()).toBeVisible();

    // The links land on this page, at the card that fixes the line.
    const fix = page.getByRole("link", { name: /fix this/i }).first();
    await expect(fix).toBeVisible();
    await expect(fix).toHaveAttribute("href", /#notice-(purposes|languages|rule3)/);

    // And the anchors exist, so the link is not a promise to nowhere.
    await expect(page.locator("#notice-purposes")).toBeAttached();
    await expect(page.locator("#notice-languages")).toBeAttached();
  });

  test("a draft purpose is activated from the notice that carries it", async ({ page }) => {
    await page.goto("/notices?status=draft");
    await page.locator('a[href^="/notices/"]').first().click();
    await expect(page).toHaveURL(/\/notices\/[0-9a-f-]{36}/, { timeout: 15_000 });
    await expect(page.getByText(/blocking publication/i)).toBeVisible({ timeout: 15_000 });

    const activate = page.getByRole("button", { name: /^activate$/i });
    const before = await activate.count();
    test.skip(before === 0, "this notice has no draft purposes left to activate");

    const blocking = page.getByText(/item\(s\) blocking publication/i);
    const said = (await blocking.innerText()).trim();

    await activate.first().click();

    // One fewer control, and one fewer line, without a reload: activating a
    // purpose is what clears a checklist line, so both queries are invalidated.
    await expect(activate).toHaveCount(before - 1, { timeout: 15_000 });
    await expect(blocking).not.toHaveText(said, { timeout: 15_000 });
  });
});
