/**
 * The breach register, as the DPO (S3-01).
 *
 * One journey: record a breach noticed five hours ago, mark it reportable to
 * CERT-In and read the hour that is left, determine it a personal data breach
 * and see the three DPDP duties appear, and find the breach refusing to close
 * while they are outstanding. Then a collection owner, who is told the page
 * is not part of their account - the server answers them 404.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

/** A `datetime-local` value for a moment `hours` ago, in the browser's zone. */
function hoursAgo(hours: number): string {
  const at = new Date(Date.now() - hours * 3_600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

test.describe("the DPO", () => {
  test.use({ storageState: statePath("dpo") });

  test("records a breach, starts the CERT-In clock, determines it and cannot yet close it", async ({ page }) => {
    await page.goto("/breaches");
    await expect(page.getByRole("heading", { name: "Personal data breaches", level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Record a breach" }).click();
    const title = `E2E breach ${Date.now()}`;
    await page.getByLabel(/^Title/).fill(title);
    await page.getByLabel(/^First noticed/).fill(hoursAgo(5));
    await page.getByRole("button", { name: "Record the breach" }).click();

    // Lands on the breach itself, titled by its reference.
    await expect(page.getByText("Personal data breach", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    await expect(page.getByText(title)).toBeVisible();

    await page.getByRole("button", { name: "Mark reportable to CERT-In" }).click();
    const certIn = page.getByRole("row", { name: /Report to CERT-In/ });
    await expect(certIn).toBeVisible();
    // Five hours after noticing, under an hour is left - not six.
    await expect(certIn.getByText(/^\d+ min left$/)).toBeVisible();

    await page.getByLabel(/^Became aware at/).fill(hoursAgo(4));
    await page.getByLabel(/^Reasoning/).fill("Names and mobile numbers were on the copy");
    await page.getByRole("button", { name: "Record the determination" }).click();
    await expect(page.getByRole("row", { name: /Board - initial intimation/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Board - detailed report/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Principals notified/ })).toBeVisible();

    // Who it touched: the platform's own tables, as recorded, confirmed as revision 1.
    await page.getByRole("button", { name: "Derive who it touched" }).click();
    // Accounts created from now on: nobody, which keeps the dev database's
    // people off an end-to-end breach's list.
    await page.getByRole("checkbox", { name: "auth_user" }).check();
    await page.getByLabel(/^Rows written from/).fill(hoursAgo(0));
    await page.getByRole("button", { name: "Show what the records say" }).click();
    await expect(page.getByText(/The records place \d+ people here/)).toBeVisible();
    await page.getByRole("button", { name: "Confirm the list" }).click();
    await expect(page.getByText(/^Revision 1, /)).toBeVisible();

    // The seeded principal, added by hand: the records cannot show her here.
    await page.getByRole("button", { name: "Revise the list" }).click();
    await page.getByRole("button", { name: "Remove this place" }).click();
    await page.getByLabel(/^Add someone the records cannot show/).fill("subject@cmp.local");
    await page.getByRole("button", { name: "Find" }).click();
    await page.getByRole("button", { name: "Add", exact: true }).first().click();
    await page.getByRole("button", { name: "Confirm the list" }).click();
    await expect(page.getByText(/^Revision 2, /)).toBeVisible();

    // Draft, approve and send; nothing goes before approval.
    await page.getByRole("button", { name: "Draft the notice" }).click();
    const words: Array<[RegExp, string]> = [
      [/^What happened/, "A copy of a contact list went to the wrong address."],
      [/^The consequences likely/, "Someone may have seen your name and mobile number."],
      [/^What has been done/, "The recipient deleted it; the list now travels encrypted."],
      [/^What she can do/, "Be wary of calls that mention the study."],
      [/^Who to contact/, "The Privacy Office, privacy@cmp.local"],
    ];
    for (const [label, text] of words) await page.getByLabel(label).fill(text);
    await page.getByRole("button", { name: "Save draft" }).click();
    await expect(page.getByText("Draft saved")).toBeVisible();
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await page.getByRole("button", { name: "Send version 1" }).click();
    // Her account at once; her email and SMS by the worker, which records each.
    await expect(page.getByText("1 of 1 listed person has been notified on every channel.")).toBeVisible({
      timeout: 60_000,
    });
    await page.reload();
    await expect(page.getByRole("row", { name: /Principals notified/ }).getByText("Done")).toBeVisible();

    await expect(page.getByText("Report to CERT-In is outstanding")).toBeVisible();
    await expect(page.getByText("Principals notified is outstanding")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Close the breach" })).toBeDisabled();
  });
});

test.describe("anyone else", () => {
  test.use({ storageState: statePath("dco") });

  test("is told the register is not part of their account", async ({ page }) => {
    await page.goto("/breaches");
    await expect(page.getByText("Not part of your account")).toBeVisible();
  });
});
