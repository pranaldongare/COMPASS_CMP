/**
 * End-to-end: reporting an incident from the public link, with no account.
 *
 * A stranger fills the form, gets one code wrong and loses nothing, then sends
 * the report and is given its reference. The office's half, claiming or
 * dismissing it, is on the staff console, a separate deployment with its own
 * suite. Run on the phone as well: the link is given to anybody, and a report
 * is as likely to be made from one.
 */
import { expect, test } from "@playwright/test";

import { expectNoSidewaysScroll } from "./support/layout";
import { freshCode, latestCodeFor } from "./support/outbox";

const stamp = Date.now().toString(36);

test("a stranger reports an incident and is given a reference", async ({ page }, testInfo) => {
  // One address per project: both spend a code, and the address is rate limited.
  const email = `reporter-${stamp}-${testInfo.project.name}@example.org`;
  const before = latestCodeFor(email);

  await page.goto("/report-incident");
  await expect(page.getByRole("heading", { name: /report an incident/i })).toBeVisible();
  await expect(page.getByText(/we keep your name and email/i)).toBeVisible();
  // And what they may ask if it is not taken up (2026-11-07).
  await expect(page.getByText(/to see it or to erase your name and email from it/i)).toBeVisible();

  await page.getByLabel(/your name/i).fill("A Reporter");
  await page.getByLabel(/your email/i).fill(email);
  await page.getByLabel(/what happened in one line/i).fill("A laptop was stolen");
  await page.getByLabel(/^what happened\s*\*?$/i).fill("From a car park, on Tuesday evening.");
  await page.getByText(/more details \(optional\)/i).click();
  await page.getByLabel(/where it started/i).fill("The sales team");
  await page.getByRole("radio", { name: /not sure/i }).check();
  await expectNoSidewaysScroll(page);
  await page.getByRole("button", { name: /^send code$/i }).click();

  const box = page.getByLabel(/the code we sent/i);
  await expect(box).toBeVisible({ timeout: 10_000 });
  const code = await freshCode(email, before);

  // Never the right one: six digits that are not the code just issued.
  await box.fill(code === "000000" ? "000001" : "000000");
  await page.getByRole("button", { name: /send the report/i }).click();
  await expect(page.getByText(/invalid or expired code/i)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByLabel(/where it started/i)).toHaveValue("The sales team");

  await box.fill(code);
  await page.getByRole("button", { name: /send the report/i }).click();
  await expect(page.getByText(/report received/i)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/^INC-\d{4}-\d+$/)).toBeVisible();
  await expect(page.getByLabel(/your name/i)).toHaveCount(0);
  await expectNoSidewaysScroll(page);
});

test("the rights page links to it, and it asks for no session", async ({ page }) => {
  await page.goto("/rights");
  await page.getByRole("link", { name: /report an incident/i }).click();
  await expect(page).toHaveURL(/\/report-incident$/);
  await expect(page.getByRole("button", { name: /^send code$/i })).toBeVisible();
});
