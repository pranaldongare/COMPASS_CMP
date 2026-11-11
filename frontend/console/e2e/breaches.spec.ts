/**
 * Incidents and breaches, as the DPO (S3-01, S3-06, ADR 0037).
 *
 * One journey: log an incident noticed five hours ago, find that nothing is
 * owed yet, mark it reportable to CERT-In and read the hour that is left,
 * validate it as a personal data breach - which records it with a BR reference
 * and starts the three DPDP duties and the organisation's board's thirty
 * minutes - and find the breach refusing to close while they are outstanding.
 * Then a collection owner, who is told the page is not part of their account -
 * the server answers them 404.
 *
 * The whole of a report's path - the public link, the board's mail, filing with
 * proof - is `breach-workflow.spec.ts`. This one lists its one person by hand:
 * an end-to-end breach must never sweep up the dev database's people.
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

    // Nothing is owed at logging: the organisation's board's duty waits for a
    // validation of yes, so an incident that is junk can close untold.
    await expect(page.getByText(/^No duty yet\./)).toBeVisible();
    await expect(page.getByRole("row", { name: /Organisation's board/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Notify Organization Board" })).toHaveCount(0);

    await page.getByRole("button", { name: "Mark reportable to CERT-In" }).click();
    const certIn = page.getByRole("row", { name: /Report to CERT-In/ });
    await expect(certIn).toBeVisible();
    // Five hours after noticing, under an hour is left - not six.
    await expect(certIn.getByText(/^\d+ min left$/)).toBeVisible();
    // A mark made in error may be set aside before anybody has validated it
    // (2026-11-07). Not pressed: the journey needs the duty outstanding.
    await expect(certIn.getByRole("button", { name: "Not reportable to CERT-In" })).toBeVisible();

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
    // Thirty minutes from the yes, not from when it was noticed five hours ago.
    await expect(page.getByRole("row", { name: /Organisation's board/ }).getByText(/^(29|30) min left$/)).toBeVisible();
    await expect(page.getByRole("row", { name: /Board - initial intimation/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Board - detailed report/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /Principals notified/ })).toBeVisible();
    // And after the yes: validation neither allows it nor stands in its way.
    await expect(certIn.getByRole("button", { name: "Not reportable to CERT-In" })).toBeVisible();

    // The seeded principal, added by hand by her mail ID: one person, and nobody
    // else from the dev database, however many of them a project or a vendor
    // would find. Her account is matched, so she is listed as herself.
    await openTab(page, "People & notices");
    await expect(page.getByText("Nobody is listed yet.")).toBeVisible();
    await page.getByRole("button", { name: "Add people" }).click();
    const adding = page.getByRole("dialog");
    await adding.getByRole("button", { name: /^Add by mail ID or mobile number/ }).click();
    await adding.getByLabel(/^Mail IDs/).fill("subject@cmp.local");
    await adding.getByRole("button", { name: "Check" }).click();
    await adding.getByRole("button", { name: "Add 1 person" }).click();
    await expect(page.getByText("1 person added to the list")).toBeVisible();
    await expect(page.locator("#affected").getByRole("cell", { name: "Added by hand" })).toBeVisible();

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
    // One button, and it asks first.
    await page.getByRole("button", { name: "Send to 1 affected person" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Send to 1 affected person" }).click();
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

    // The 72-hour report, drafted from the register; the account of notices in (vi).
    const reference = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
    await openTab(page, "Reports");
    await expect(page.getByTestId("report-board_intimation").getByText("Rule 7(2)(a)")).toBeVisible();
    await page.getByTestId("report-board_report").getByRole("button", { name: "Draft it" }).click();
    const report = page.getByRole("dialog");
    await expect(report.getByRole("heading", { name: /^72-hour report to the DPDP Board · version 1$/ })).toBeVisible();
    await expect(report.getByLabel(/^\(vi\) The account of notices/)).toHaveValue(
      /^1 of the 1 Data Principals listed as affected have been notified/,
    );
    await report.getByRole("button", { name: "Cancel" }).click();

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
