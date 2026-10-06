/**
 * Incidents and breaches, as the DPO (S3-01, S3-06).
 *
 * One journey: log an incident noticed five hours ago, mark it reportable to
 * CERT-In and read the hour that is left, validate it as a personal data
 * breach - which records it with a BR reference - and see the three DPDP
 * duties appear, and find the breach refusing to close
 * while they are outstanding. Then a collection owner, who is told the page
 * is not part of their account - the server answers them 404.
 */
import { expect, test, type Page } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

/** A `datetime-local` value for a moment `hours` ago, in the browser's zone. */
function hoursAgo(hours: number): string {
  const at = new Date(Date.now() - hours * 3_600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** The breach page's sections are tabs; a tab's name carries its count. */
function openTab(page: Page, name: string) {
  return page.getByRole("tab", { name: new RegExp(`^${name}`) }).click();
}

test.describe("the DPO", () => {
  test.use({ storageState: statePath("dpo") });

  test("logs an incident, starts the CERT-In clock, records it as a breach and cannot yet close it", async ({
    page,
  }) => {
    await page.goto("/breaches");
    await expect(page.getByRole("heading", { name: "Incidents and personal data breaches", level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Log an incident" }).click();
    const title = `E2E breach ${Date.now()}`;
    await page.getByLabel(/^Title/).fill(title);
    await page.getByLabel(/^First noticed/).fill(hoursAgo(5));
    // The email that reported it, kept with the incident as it is logged.
    await page.getByRole("button", { name: "Attach a file" }).click();
    await page.getByLabel(/^File 1/).setInputFiles({
      name: "report.eml",
      mimeType: "message/rfc822",
      buffer: Buffer.from("From: someone@example.org\r\nSubject: Not mine\r\n\r\nHello.\r\n"),
    });
    await page.getByRole("button", { name: "Log the incident" }).click();

    // Lands on the incident itself, titled by its incident reference.
    await expect(page.getByText("Incident, being validated", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-\d{4}-\d{4}$/);
    const incident = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
    await expect(page.getByText(title)).toBeVisible();
    await openTab(page, "Attachments");
    await expect(page.locator("#attachments").getByText("report.eml")).toBeVisible();
    await expect(page.locator("#attachments").getByText("Email", { exact: true })).toBeVisible();
    await openTab(page, "Duties");

    // The organisation's board is owed from the moment it was logged, from when
    // it was first noticed: five hours ago is long past thirty minutes.
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await expect(orgBoard.getByText(/^Overdue by /)).toBeVisible();
    await page.getByRole("link", { name: "Brief for the organisation's board" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Brief for the organisation's board - ${incident}`);
    await expect(page.getByText("Whether it is a personal data breach - validation is still pending")).toBeVisible();
    await page.getByRole("link", { name: "Back to the incident" }).click();
    await orgBoard.getByRole("button", { name: "Record the report" }).click();
    await page.getByLabel(/^Reported at/).fill(hoursAgo(4.5));
    await page.getByLabel(/^Reported to/).fill("The chair, by phone");
    await page.getByRole("dialog").getByRole("button", { name: "Record", exact: true }).click();
    await expect(orgBoard.getByText("Done")).toBeVisible();
    await expect(orgBoard.getByText(/to The chair, by phone/)).toBeVisible();

    await page.getByRole("button", { name: "Mark reportable to CERT-In" }).click();
    const certIn = page.getByRole("row", { name: /Report to CERT-In/ });
    await expect(certIn).toBeVisible();
    // Five hours after noticing, under an hour is left - not six.
    await expect(certIn.getByText(/^\d+ min left$/)).toBeVisible();

    await openTab(page, "Validation");
    await page.getByLabel(/^Became aware at/).fill(hoursAgo(4));
    await page.getByLabel(/^Reasoning/).fill("Names and mobile numbers were on the copy");
    await page.getByRole("button", { name: "Record the validation" }).click();
    // The yes records it: a BR reference, with the INC it was logged as kept.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    await expect(page.getByText("Personal data breach", { exact: true })).toBeVisible();
    // In the Details card: beside the close card on a wide screen, after the
    // tabs on a phone - one of the two placements is shown.
    await expect(page.getByText(incident, { exact: true }).filter({ visible: true })).toBeVisible();
    await openTab(page, "Duties");
    await expect(page.getByRole("row", { name: /Board - initial intimation/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Board - detailed report/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Principals notified/ })).toBeVisible();

    // Who it touched: the platform's own tables, as recorded, confirmed as revision 1.
    await openTab(page, "People & notices");
    await page.getByRole("button", { name: "Derive who it touched" }).click();
    // Accounts created from a few minutes ahead: nobody, which keeps the dev
    // database's people off an end-to-end breach's list - including the
    // breach-only logins e2e/breach-tickets.spec.ts made the minute before.
    await page.getByRole("checkbox", { name: "auth_user" }).check();
    await page.getByLabel(/^Rows written from/).fill(hoursAgo(-0.1));
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
    await openTab(page, "Duties");
    await expect(page.getByRole("row", { name: /Principals notified/ }).getByText("Done")).toBeVisible();

    await expect(page.getByText("Report to CERT-In is outstanding")).toBeVisible();
    await expect(page.getByText("Principals notified is outstanding")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Close the breach" })).toBeDisabled();

    // The Board's documents, drafted from the register; the account of notices in (vi).
    const reference = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
    await page.getByRole("link", { name: "Documents for the Board" }).click();
    await expect(page.getByText("Initial intimation - Rule 7(2)(a)")).toBeVisible();
    await expect(page.getByText("Detailed report - Rule 7(2)(b)")).toBeVisible();
    await expect(page.getByText("(vi) The account of notices to the Data Principals affected")).toBeVisible();
    await expect(page.getByText(/^1 of the 1 Data Principals listed as affected have been notified/)).toBeVisible();

    // Found in the register by the reference it was logged as, and by its
    // title; the search stays in the address.
    await page.goto("/breaches?status=all");
    const search = page.getByRole("searchbox", { name: "Search" });
    await search.fill(incident);
    await search.press("Enter");
    await expect(page).toHaveURL(new RegExp(`q=${incident}`));
    await expect(page.getByRole("link", { name: reference })).toBeVisible();
    await expect(page.getByText(/^1 of \d+ shown$/)).toBeVisible();

    // And on the dashboard, with every duty's clock.
    await page.goto("/dashboard");
    // Logging an incident is always one click from the DPO's landing page.
    await expect(page.getByRole("button", { name: "Log an incident" })).toBeVisible();
    const open = page.getByLabel("Open breaches");
    await expect(open.getByText(reference)).toBeVisible();
  });
});

test.describe("anyone else", () => {
  test.use({ storageState: statePath("dco") });

  test("is told the register is not part of their account", async ({ page }) => {
    await page.goto("/breaches");
    await expect(page.getByText("Not part of your account")).toBeVisible();
  });
});
