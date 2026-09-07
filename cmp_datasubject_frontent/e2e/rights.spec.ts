/**
 * End-to-end: the rights flows, sections 11 to 14.
 *
 * Three journeys through a real browser against the real API, in the order
 * the product is used: a stranger asks from the public rights page; a data
 * principal asks from her account and names a nominee; the nominee accepts
 * through the link in the outbox. The DPO's half - walking the request down
 * the path and releasing the response - is on the staff console, a separate
 * deployment with its own suite.
 *
 * Serial, because the journeys share one request and one nomination, and
 * because the public form is rate limited.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { freshCode, latestCodeFor } from "./support/outbox";
import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

// Once, on desktop. The journeys share one data principal - who may hold only
// one live nomination - so a second project running them in parallel races the
// first over the same rows. The public pages are covered on
// the phone viewport by the consent-flow and visual specs.
test.skip(({ isMobile }) => Boolean(isMobile), "the rights journeys share one account and run on desktop only");

const OUTBOX =
  process.env.E2E_OUTBOX ??
  path.join(__dirname, "..", "..", "cmp_backend", "var", "outbox.log");

const SHOTS = process.env.E2E_SHOTS ?? "";

async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  fs.mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}

/** The newest nomination acceptance link the outbox holds for one recipient. */
function latestAcceptLinkFor(recipient: string): string | null {
  try {
    const lines = fs.readFileSync(OUTBOX, "utf8").split(/\r?\n/);
    let current: string | null = null;
    let found: string | null = null;
    for (const line of lines) {
      const to = /\bto:\s*(\S+)/.exec(line);
      if (to) {
        current = to[1];
        continue;
      }
      const link = /(https?:\/\/\S+\/rights\/nominations\/\S+)/.exec(line);
      if (link && current?.toLowerCase() === recipient.toLowerCase()) found = link[1];
    }
    return found;
  } catch {
    return null;
  }
}

const stamp = Date.now().toString(36);
const NOMINEE = `nominee-${stamp}@example.org`;
// Unique per run: a nominee's mobile is unique on the table.
const NOMINEE_MOBILE = `+91555${Date.now().toString().slice(-7)}`;

/** Shared across the serial journeys below. */
const shared: { reference: string | null } = { reference: null };

/* ==========================================================================
   1. A stranger, from the public rights page
   ========================================================================== */
test.describe("public rights page", () => {
  test("records a request and answers neutrally", async ({ page }) => {
    await page.goto("/rights");
    await expect(page.getByRole("heading", { name: /your rights/i })).toBeVisible();

    const form = page.locator("#request");
    await form.getByLabel(/what are you asking for/i).selectOption("access");
    await form.getByLabel(/email or mobile you registered with/i).fill(`stranger-${stamp}@example.org`);
    await form.getByLabel(/your name/i).fill("A Stranger");
    await form
      .getByLabel(/^your request/i)
      .fill("Please tell me what personal data you hold about me and who has seen it.");
    await shot(page, "rights-public-form");
    await form.getByRole("button", { name: /send the request/i }).click();

    // Recorded, with a reference - and no word about whether the contact matched anyone.
    await expect(form.getByText(/recorded/i).first()).toBeVisible({ timeout: 10_000 });
    // Anchored: the verify form below shows an example reference in its hint.
    await expect(form.getByText(/^RR-\d{4}-\d{6}$/)).toBeVisible();
    await expect(form).toContainText(/if we hold records for the contact you gave/i);
    await expect(form).not.toContainText(/no account|not found|unknown contact/i);

    // The second half is offered at once.
    await expect(form.getByLabel(/the code we sent/i)).toBeVisible();
    await shot(page, "rights-public-recorded");
  });

  test("the nominee entry point exists and stays neutral", async ({ page }) => {
    await page.goto("/rights/nominee");
    await expect(page.getByRole("heading", { name: /acting for someone/i })).toBeVisible();
    // A fresh reference each run: the endpoint rate-limits per nomination, and
    // a fixed placeholder would be a sixth attempt by the sixth run.
    await page.getByLabel(/nomination reference/i).fill(crypto.randomUUID());
    await page.getByLabel(/your email or mobile/i).fill("nobody@example.org");
    await page.getByRole("button", { name: /send me a code/i }).click();
    await expect(page.getByText(/if that nomination is in place/i)).toBeVisible({ timeout: 10_000 });
  });
});

/* ==========================================================================
   2. The data principal, from her account
   ========================================================================== */
test.describe("data principal", () => {
  test.use({ storageState: statePath("subject") });

  test("makes a request from her dashboard and sees its clock", async ({ page }) => {
    await page.goto("/my-requests");
    await expect(page.getByRole("heading", { name: /your requests/i })).toBeVisible();

    await page.getByRole("button", { name: /make a request/i }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/what are you asking for/i).selectOption("access");
    await dialog
      .getByLabel(/^your request/i)
      .fill(`E2E ${stamp}: a summary of what you hold about me, and who it was shared with.`);
    await dialog.getByRole("button", { name: /send the request/i }).click();

    // The card for *this* request: the innermost box holding both the text just
    // typed and a reference. Her page keeps every request she has ever made, so
    // "the first reference on the page" is somebody else's run once the
    // database is no longer fresh.
    const card = page
      .locator("div")
      .filter({ hasText: `E2E ${stamp}` })
      .filter({ has: page.getByText(/^RR-\d{4}-\d{6}$/) })
      .last();
    const referenceOnCard = card.getByText(/^RR-\d{4}-\d{6}$/).first();
    await expect(referenceOnCard).toBeVisible({ timeout: 10_000 });
    const reference = await referenceOnCard.textContent();
    shared.reference = reference?.trim() ?? null;
    expect(shared.reference).toMatch(/^RR-\d{4}-\d{6}$/);

    // The session verified her, so the clock started and the path shows it.
    // A request opens expanded the moment it is made; open it only if it is not.
    await expect(card.getByText(/received/i).first()).toBeVisible();
    const collapsed = page.getByRole("button", { name: /show progress/i }).first();
    if (!(await page.getByRole("button", { name: /hide progress/i }).first().isVisible().catch(() => false))) {
      await collapsed.click();
    }
    await expect(page.getByText(/days? to respond/i).first()).toBeVisible();
    await expect(page.getByText(/the CMP answers its own records/i).first()).toBeVisible();
    await shot(page, "my-requests");
  });

  test("names a nominee, who is not usable until they accept", async ({ page }) => {
    await page.goto("/my-requests");
    // The card loads after the page does. Wait for it to settle before deciding
    // whether a nomination from an earlier run has to be revoked first.
    await expect(page.getByText(/somebody to act for you/i)).toBeVisible();
    const revoke = page.getByRole("button", { name: /revoke this nomination/i });
    const form = page.getByLabel(/their name/i);
    await expect(revoke.or(form).first()).toBeVisible({ timeout: 10_000 });
    if (await revoke.isVisible()) {
      await revoke.click();
      await expect(revoke).toHaveCount(0, { timeout: 10_000 });
    }

    await expect(form).toBeVisible({ timeout: 10_000 });
    await form.fill("Ravi Verma");
    await page.getByLabel(/their mobile/i).fill(NOMINEE_MOBILE);
    await page.getByLabel(/their email/i).fill(NOMINEE);
    // Partial scope: access only.
    for (const label of [/correction/i, /erasure/i, /grievance/i]) {
      await page.getByRole("checkbox", { name: label }).uncheck();
    }
    await page.getByRole("button", { name: /^nominate$/i }).click();

    await expect(page.getByText(/waiting for the nominee to accept/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/may ask for: access\./i)).toBeVisible();
    await shot(page, "my-requests-nomination-pending");
  });
});

/* ==========================================================================
   3. The nominee, through the link in the outbox
   ========================================================================== */
test.describe("nominee", () => {
  test("accepts through the single-use link", async ({ page }) => {
    let link: string | null = null;
    await expect
      .poll(() => (link = latestAcceptLinkFor(NOMINEE)), { timeout: 15_000 })
      .not.toBeNull();
    const url = new URL(link!);
    await page.goto(url.pathname);

    await expect(page.getByRole("heading", { name: /has nominated you/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/^Access$/).first()).toBeVisible();
    await shot(page, "nomination-accept");

    // The link alone accepts nothing: a code to a recorded contact first. Both
    // are offered, masked; the mobile is chosen, and the code arrives by SMS
    // in the same outbox.
    const before = latestCodeFor(NOMINEE_MOBILE);
    await page.getByRole("radio", { name: /mobile/i }).check();
    await page.getByRole("button", { name: /send me a code/i }).click();
    await page.getByLabel(/six-digit code/i).fill(await freshCode(NOMINEE_MOBILE, before));
    await page.getByRole("button", { name: /accept the nomination/i }).click();
    await expect(page.getByText(/^accepted$/i)).toBeVisible({ timeout: 10_000 });

    // Single use: the same link is now not valid, and says only that.
    await page.goto(url.pathname);
    await expect(page.getByText(/this link is not valid/i)).toBeVisible({ timeout: 10_000 });
  });
});
