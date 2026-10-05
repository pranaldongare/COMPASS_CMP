/**
 * Breach tickets, end to end (S3-08).
 *
 * The DPO logs an incident, validates it a breach, and asks the DCO to act;
 * the DCO finds the ticket on Tickets - the breach reference and the ask,
 * nothing else from the register - writes and returns it; the DPO closes the
 * ticket, and only then does the breach close.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

function minutesAgo(minutes: number): string {
  const at = new Date(Date.now() - minutes * 60_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

const shared: { url: string; reference: string; title: string } = { url: "", reference: "", title: "" };

test.describe("the DPO asks", () => {
  test.use({ storageState: statePath("dpo") });

  test("logs, records the breach, tells the board and assigns a ticket to the DCO", async ({ page }) => {
    shared.title = `E2E ticket breach ${Date.now()}`;
    await page.goto("/breaches");
    await page.getByRole("button", { name: "Log an incident" }).click();
    await page.getByLabel(/^Title/).fill(shared.title);
    await page.getByLabel(/^First noticed/).fill(minutesAgo(20));
    await page.getByRole("button", { name: "Log the incident" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-/);

    // Before the yes, nobody can be asked.
    await expect(page.getByText("Tickets wait for the breach to be recorded")).toBeVisible();

    await page.getByLabel(/^Became aware at/).fill(minutesAgo(10));
    await page.getByLabel(/^Reasoning/).fill("Contact details were on the drive");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    shared.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();
    shared.url = page.url();

    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await orgBoard.getByRole("button", { name: "Record the report" }).click();
    await page.getByLabel(/^Reported at/).fill(minutesAgo(5));
    await page.getByLabel(/^Reported to/).fill("The chair, by phone");
    await page.getByRole("dialog").getByRole("button", { name: "Record", exact: true }).click();
    await expect(orgBoard.getByText("Done")).toBeVisible();

    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^Find them/).fill("dco@cmp.local");
    const who = dialog.getByLabel(/^Who/);
    await expect(who.locator("option", { hasText: "dco@cmp.local" })).toHaveCount(1);
    await who.selectOption({ label: (await who.locator("option", { hasText: "dco@cmp.local" }).textContent()) ?? "" });
    await dialog.getByLabel(/^What you are asking them to do/).fill("Export the drive's access log and keep it");
    await dialog.getByRole("button", { name: "Assign", exact: true }).click();
    const tickets = page.locator("#tickets");
    await expect(tickets.getByRole("row", { name: /Waiting on the holder/ })).toBeVisible();
  });
});

test.describe("the DCO answers", () => {
  test.use({ storageState: statePath("dco") });

  test("finds the ticket with the reference and the ask, writes and returns it", async ({ page }) => {
    await page.goto("/tickets");
    const card = page.getByTestId("breach-ticket").filter({ hasText: shared.reference });
    await expect(card).toBeVisible();
    await expect(card.getByText("Export the drive's access log and keep it")).toBeVisible();
    // Nothing else from the register reaches the holder.
    await expect(page.getByText(shared.title)).toHaveCount(0);

    await card.getByRole("button", { name: "Respond" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^When you return the ticket/).selectOption("done");
    await dialog.getByLabel("Message", { exact: true }).fill("Exported to the evidence share; nothing deleted.");
    await dialog.getByText("This is my return").click();
    await dialog.getByTestId("composer-send").click();
    await expect(page.getByText("Ticket returned")).toBeVisible();

    // The register is still not theirs.
    await page.goto(shared.url);
    await expect(page.getByText("Not part of your account")).toBeVisible();
  });
});

test.describe("the DPO closes", () => {
  test.use({ storageState: statePath("dpo") });

  test("closes the ticket, and only then can the breach close", async ({ page }) => {
    await page.goto(shared.url);
    // The open ticket is what stands in the way, among the rest.
    await expect(page.getByText("1 breach ticket is still open")).toBeVisible();
    const tickets = page.locator("#tickets");
    const row = tickets.getByRole("row", { name: /Returned/ });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Open" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Exported to the evidence share; nothing deleted.")).toBeVisible();
    await dialog.getByRole("button", { name: "Close the ticket" }).click();
    await expect(page.getByText("Ticket closed")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(tickets.getByRole("row", { name: /Closed/ })).toBeVisible();

    // Validated no after all: the DPDP duties set aside, nothing left open.
    await page.getByLabel(/^Validation/).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("The drive held test accounts only");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByText("Validation recorded")).toBeVisible();
    await expect(page.getByText("1 breach ticket is still open")).toHaveCount(0);
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
    // On a phone the toasts sit over the foot of the page until they fade.
    await expect(page.getByRole("region", { name: "Notifications" }).locator("p")).toHaveCount(0, {
      timeout: 15_000,
    });
    // At the foot of a phone's viewport the pointer's hit-test lands on the
    // card around it; the keyboard presses the same button.
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Breach closed")).toBeVisible();
  });
});
