/**
 * A member of staff managing their own contacts, from the console.
 *
 * The console account page used to show who you are and nothing you could do
 * about how you are reached. That mattered twice over: an administrator can put
 * a mobile on somebody's account, and the number arrives unconfirmed; and a
 * member of staff is also a data principal, whose corporate address stops being
 * theirs the day they leave while the consents they gave do not.
 *
 * Codes are read from the dev outbox, so this needs the running stack and the
 * seeded accounts.
 */
import { expect, test } from "@playwright/test";

import { expectNoSidewaysScroll } from "./support/layout";
import { freshCode, latestCodeFor } from "./support/outbox";
import { statePath } from "./support/session";

test.describe("the account page's contacts", () => {
  // Serial: the codes for one contact are capped per hour.
  test.describe.configure({ mode: "serial" });
  test.use({ storageState: statePath("dpo") });

  test("adds a personal address and confirms it with the code sent there", async ({
    page,
  }) => {
    await page.goto("/account");

    const row = page.getByTestId("contact-secondary_email");
    await expect(row).toBeVisible();

    const personal = `console-${Date.now()}@example.org`;
    const before = latestCodeFor(personal);
    await row.getByRole("button", { name: /^(add|change)$/i }).click();
    await row.getByLabel(/personal email/i).fill(personal);
    await row.getByRole("button", { name: /save and send a code/i }).click();

    // Saved, unconfirmed, and asking for the code. Exact, because the address
    // also appears inside the "we have sent a code to ..." toast.
    await expect(row.getByText(personal, { exact: true })).toBeVisible();
    await expect(row.getByText(/not confirmed/i)).toBeVisible();
    await row.getByLabel(/six-digit code/i).fill(await freshCode(personal, before));
    await row.getByRole("button", { name: /^confirm$/i }).click();

    await expect(row.getByText(/^confirmed$/i)).toBeVisible({ timeout: 10_000 });
  });

  test("the work address is shown but is not theirs to change here", async ({ page }) => {
    await page.goto("/account");

    const row = page.getByTestId("contact-email");
    await expect(row.getByText("dpo@cmp.local", { exact: true })).toBeVisible();
    await expect(row.getByRole("button", { name: /^(add|change|remove)$/i })).toHaveCount(
      0,
    );
  });

  /**
   * A session's user-agent is one long unbroken string, and the column holding
   * it defaulted to `min-width: auto` - so the page grew wider than the phone,
   * mobile Chrome zoomed out to the content width, and a contact's button was
   * hit-tested under a label from the row above it.
   */
  test("fits the viewport it was given", async ({ page }) => {
    await page.goto("/account");
    await expect(page.getByTestId("contact-mobile")).toBeVisible();
    await expectNoSidewaysScroll(page);
  });
});
