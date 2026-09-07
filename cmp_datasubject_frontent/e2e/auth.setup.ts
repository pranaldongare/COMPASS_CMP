/**
 * Sign in once as the data principal, and save the session for every spec to
 * reuse.
 *
 * The API allows only a handful of one-time codes per contact per hour - a
 * control that is working, and one the suite should live within rather than
 * switch off. Signing her in once and reusing the cookie removes the cause of
 * the flake that produced.
 *
 * **The session cookie is HttpOnly**, so it cannot be read and re-set by hand.
 * `storageState` captures it at the browser-context level, which is the only
 * mechanism that works for a cookie JavaScript is not allowed to see.
 */
import { test as setup, type Browser } from "@playwright/test";
import fs from "node:fs";

import { freshCode, latestCodeFor } from "./support/outbox";
import { STATE_DIR, statePath } from "./support/session";

/**
 * The data principal, who has no password at all.
 *
 * `password_hash` is nullable for exactly this reason: she never chose one and
 * was never given one. She signs in with a one-time code.
 */
const SUBJECT = { role: "subject", contact: "subject@cmp.local" };

/**
 * Is a saved session still good?
 *
 * Signing her in on every run spends the code budget on nothing: her session
 * outlives a single run, so the cheapest correct thing is to check the one
 * already on disk before asking for another.
 */
async function sessionStillWorks(browser: Browser, role: string): Promise<boolean> {
  if (!fs.existsSync(statePath(role))) return false;
  const context = await browser.newContext({
    storageState: statePath(role),
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
  });
  try {
    const page = await context.newPage();
    await page.goto("/my-consents");
    // Wait for the app to settle before reading the URL. The redirect to
    // sign-in is client-side, fired once `/auth/me` resolves, so checking at
    // `domcontentloaded` reports a dead session as a live one - and the run
    // then fails several tests later, somewhere unrelated.
    await page.waitForLoadState("networkidle").catch(() => {});
    return !page.url().includes("sign-in");
  } catch {
    return false;
  } finally {
    await context.close();
  }
}


setup(`sign in as ${SUBJECT.role}`, async ({ page, context, browser }) => {
  // Reuse before spending a one-time code. See `sessionStillWorks`.
  if (await sessionStillWorks(browser, SUBJECT.role)) return;

  const before = latestCodeFor(SUBJECT.contact);

  await page.goto("/sign-in");
  await page.getByRole("radio", { name: /^email$/i }).check();
  await page.getByLabel(/email address/i).fill(SUBJECT.contact);
  await page.getByRole("button", { name: /send.*code|continue/i }).click();

  await page.getByLabel(/six-digit code/i).fill(await freshCode(SUBJECT.contact, before));
  await page.getByRole("button", { name: /^verify$/i }).click();

  await page.waitForURL(/\/my-consents/, { timeout: 20_000 });

  fs.mkdirSync(STATE_DIR, { recursive: true });
  await context.storageState({ path: statePath(SUBJECT.role) });
});
