/**
 * DataVault (0070): the administrator's connection page, and the card on a
 * rights request.
 *
 * Nothing here calls DataVault or saves the connection: the page is read as
 * it stands. The card on a request is looked at only when `E2E_DV_REQUEST`
 * names a request uuid, since which request has an answer is this database's
 * own business.
 *
 * Starting a request is walked only when `E2E_DV_START` names one that is
 * received and ready to start, for a person whose project a DCO Admin answers
 * for, with DataVault switched on: it moves that request, so it is never run
 * against a request somebody is working on.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe("the administrator", () => {
  test.use({ storageState: statePath("admin") });

  test("reaches DataVault connection from the menu, and the key is never shown", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await page.getByRole("link", { name: "DataVault connection" }).first().click();
    await expect(page).toHaveURL(/\/datavault$/);
    await expect(page.getByRole("heading", { name: "DataVault connection" })).toBeVisible();
    await expect(page.getByLabel("DataVault address")).toBeVisible();
    await expect(page.getByLabel("API key")).toHaveValue("");
    await expect(page.getByLabel("Header the key is sent in")).toHaveValue(/.+/);
    await expect(page.getByLabel("Switched on")).toBeVisible();
    await expect(page.getByText("SE::")).toHaveCount(0);
  });
});

test.describe("the DPO", () => {
  test.use({ storageState: statePath("dpo") });

  test("has no DataVault connection page", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("link", { name: "DataVault connection" })).toHaveCount(0);
    await page.goto("/datavault");
    await expect(page.getByLabel("DataVault address")).toHaveCount(0);
  });
});

test.describe("the office that answers a request", () => {
  // E2E_DV_ROLE: whose request it is (dpo or legal).
  test.use({ storageState: statePath(process.env.E2E_DV_ROLE ?? "dpo") });

  test("sees the DataVault card on a request's Holders tab", async ({ page }) => {
    const uuid = process.env.E2E_DV_REQUEST;
    test.skip(!uuid, "set E2E_DV_REQUEST to a rights request's uuid");
    await page.goto(`/requests/${uuid}#holders`);
    const card = page
      .locator("section, div")
      .filter({ has: page.getByRole("heading", { name: "DataVault", exact: true }) })
      .last();
    await expect(card).toBeVisible();
    await expect(card.getByText("SE::")).toHaveCount(0);
    if (process.env.E2E_DV_SHOT)
      await page.screenshot({ path: process.env.E2E_DV_SHOT, fullPage: true });
  });
});

test.describe("as a request starts", () => {
  test.use({ storageState: statePath(process.env.E2E_DV_ROLE ?? "dpo") });

  test("the holders are found and DataVault's answer lands on the card, with no reload", async ({
    page,
  }) => {
    const uuid = process.env.E2E_DV_START;
    test.skip(
      !uuid,
      "set E2E_DV_START to the uuid of a received request that is ready to start",
    );
    await page.goto(`/requests/${uuid}`);
    // The bar, not the "Next step" section of the Overview tab.
    const next = page.locator('section[aria-label="Next step"]');
    await expect(next).toContainText("Start the work");
    await expect(next).toContainText("the platform finds who holds the data");
    await next.getByRole("button", { name: /move to in progress/i }).click();

    // Found by the platform: the next step is to confirm who answers, not to
    // find anybody.
    await expect(next).toContainText("Confirm who answers");
    await expect(next).not.toContainText("Find who holds the data");
    await page.getByRole("tab", { name: /holders/i }).click();
    await expect(page.getByText(/· DCO Admin/).first()).toBeVisible();

    // The platform's own check lands a moment later; the card looks again.
    await expect(
      page.getByText("Checked by the platform when holders were found"),
    ).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/^DV-/).first()).toBeVisible();
    await expect(page.getByText("SE::")).toHaveCount(0);
    if (process.env.E2E_DV_SHOT)
      await page.screenshot({ path: process.env.E2E_DV_SHOT, fullPage: true });
  });
});
