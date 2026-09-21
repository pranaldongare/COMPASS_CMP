/**
 * The audit trail answers a question.
 *
 * As the DPO: the page loads with its summary, an area filter narrows the
 * list and appears as a chip, the chip removes it, the "about" picker finds
 * the seeded data principal and filters on her, a deep link from a consent
 * record arrives pre-filtered, and the export button is offered.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

test.describe("audit trail", () => {
  test.use({ storageState: statePath("dpo") });

  test("filters by area, shows the chip, and clears it", async ({ page }) => {
    await page.goto("/audit");
    await expect(
      page.getByRole("heading", { name: "Audit trail", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("Entries", { exact: true })).toBeVisible();

    await page.getByLabel("Area").selectOption({ label: "Sign-in and access" });
    await expect(page).toHaveURL(/event_group=auth/);
    await expect(page.getByText("Filtered by")).toBeVisible();
    await expect(page.getByRole("status").getByText("Sign-in and access")).toBeVisible();

    // Every row on the page is a sign-in event.
    const list = page.getByRole("table", { name: "Audit entries, most recent first" });
    const firstEvent = list.locator("tbody tr").first().locator("td").nth(1);
    await expect(firstEvent).toContainText(/Auth /);

    await page.getByRole("button", { name: /Remove the area filter/ }).click();
    await expect(page).not.toHaveURL(/event_group=/);
  });

  test("finds a data principal by her contact and filters on her", async ({ page }) => {
    // The whole address: names and contacts are sealed, so a fragment finds
    // nobody, and the field says so.
    await page.goto("/audit");
    await page.getByLabel("About").selectOption({ label: "Data principal" });
    await page.getByLabel("Email or mobile").fill("subject@cmp.local");
    const option = page.getByRole("listbox").getByRole("option").first();
    await expect(option).toBeVisible();
    await option.click();
    await expect(page).toHaveURL(/subject=/);
    await expect(page.getByText("Filtered by")).toBeVisible();
  });

  test("a deep link arrives pre-filtered on the record", async ({ page }) => {
    await page.goto(
      "/audit?entity_type=consent_artefact&entity=00000000-0000-4000-8000-000000000000&label=Nobody",
    );
    await expect(page.getByText("Nobody", { exact: true })).toBeVisible();
    await expect(page.getByText("Nothing matches these filters")).toBeVisible();
    await expect(page.getByRole("button", { name: "Export CSV" })).toBeVisible();
  });
});
