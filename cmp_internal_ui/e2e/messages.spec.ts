/**
 * The Messages page: the office rewords what the platform sends.
 *
 * One journey, as the DPO: open the page, pick the data principal's sign-in
 * code, switch to SMS, write new words that use a variable, preview them with
 * the sample values, save, see the card say it is customised, and put the
 * default back. The server's refusal of an unknown variable is asserted too,
 * because it is the guard that keeps a template from shipping `{name}`.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

test.describe("messages", () => {
  test.use({ storageState: statePath("dpo") });

  test("the office rewords an SMS, previews it, saves it and resets it", async ({
    page,
  }) => {
    await page.goto("/messages");
    await expect(page.getByRole("heading", { name: "Messages", level: 1 })).toBeVisible();

    const card = page.locator("#message-login_code");
    await expect(card.getByText("Data principal sign-in code")).toBeVisible();
    await card.getByRole("tab", { name: "SMS" }).click();

    // Unique per run: a save with the words already in force is a no-op, and
    // the previous run may have left its words behind if it stopped early.
    const stamp = Date.now();
    const body = card.getByLabel(/^Message/);
    await body.fill(`Test words ${stamp}: {code} signs you in for {minutes} minutes.`);

    // Preview renders the sample values, not the placeholders.
    await card.getByRole("button", { name: "Preview" }).click();
    await expect(
      card.getByText(`Test words ${stamp}: 482913 signs you in for 10 minutes.`),
    ).toBeVisible();

    await card.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Words saved")).toBeVisible();
    await expect(card.getByText("Customised", { exact: true })).toBeVisible();

    // Two clicks to reset, on purpose.
    await card.getByRole("button", { name: "Reset to default" }).click();
    await card.getByRole("button", { name: "Yes, use the default words" }).click();
    await expect(page.getByText("Back to the default")).toBeVisible();
    await expect(card.getByText("Default words", { exact: true })).toBeVisible();
  });

  test("a variable the message does not provide is refused, naming the allowed ones", async ({
    page,
  }) => {
    await page.goto("/messages");
    const card = page.locator("#message-mfa_code");
    const body = card.getByLabel(/^Body/);
    await body.fill("Dear {full_name}, your code is {code}.");
    await card.getByRole("button", { name: "Save" }).click();
    await expect(card.getByRole("alert")).toContainText("{full_name}");
    await expect(card.getByRole("alert")).toContainText("{code}");
  });
});
