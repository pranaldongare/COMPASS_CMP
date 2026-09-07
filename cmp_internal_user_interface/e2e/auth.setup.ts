/**
 * Sign in once per role, and save the session for every spec to reuse.
 *
 * This exists because the suite was fighting a security control that is working
 * correctly. The API locks an account after five failed-or-otherwise login
 * attempts in thirty minutes, and four parallel workers each signing in as the
 * same DPO trip that within a single run. Every subsequent test then failed
 * with what looked like an application bug — a missing element, a redirect to
 * sign-in — and each of them passed when run alone, which is the most expensive
 * kind of flake to diagnose.
 *
 * Signing in once per role and reusing the cookie removes the cause. It is also
 * three or four seconds faster per test, which at forty tests is most of a
 * minute.
 *
 * **The session cookie is HttpOnly**, so it cannot be read and re-set by hand.
 * `storageState` captures it at the browser-context level, which is the only
 * mechanism that works for a cookie JavaScript is not allowed to see.
 *
 * Not covered here: `e2e/auth.spec.ts` deliberately signs in itself, because
 * the thing it tests *is* the sign-in.
 */
import { test as setup, type Browser, type Page } from "@playwright/test";
import fs from "node:fs";

import { freshCode, latestCodeFor } from "./support/outbox";
import { STATE_DIR, statePath } from "./support/session";

const PASSWORD = process.env.E2E_PASSWORD ?? "SeedPassw0rd!2026";

/**
 * The staff roles. Every one of them signs in with a password and then a code
 * that only exists in the dev outbox - since 2026-09-06 the second factor is
 * not the DPO's alone. Skipped where the outbox is not readable.
 *
 * The administrator is seeded too, but no spec drives that console, so no
 * session is minted for it: each sign-in spends a code from a per-account
 * budget that the suite should live within.
 */
const STAFF = [
  { role: "dco", login: "dco@cmp.local" },
  { role: "rnd", login: "rnd@cmp.local" },
  { role: "dcoadmin", login: "dcoadmin@cmp.local" },
  { role: "rco", login: "rco@cmp.local" },
  { role: "dpo", login: "dpo@cmp.local" },
];

/**
 * Is a saved session still good?
 *
 * Every staff sign-in spends an MFA code from a per-account budget the suite
 * should live within rather than switch off. A session outlives a single run,
 * so the cheapest correct thing is to check the one already on disk before
 * asking for another. `e2e/auth.spec.ts` still signs in from scratch, because
 * the thing it tests *is* the sign-in.
 */
async function sessionStillWorks(browser: Browser, role: string): Promise<boolean> {
  if (!fs.existsSync(statePath(role))) return false;
  const context = await browser.newContext({
    storageState: statePath(role),
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
  });
  try {
    const page = await context.newPage();
    await page.goto("/dashboard");
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


async function submitPassword(page: Page, login: string) {
  await page.goto("/sign-in");
  await page.getByLabel(/email or username/i).fill(login);
  await page.getByLabel(/^password/i).fill(PASSWORD);
  await page.getByRole("button", { name: /^sign in$/i }).click();
}

for (const { role, login } of STAFF) {
  setup(`sign in as ${role}`, async ({ page, context, browser }) => {
    // Reuse before spending a code. See `sessionStillWorks`.
    if (await sessionStillWorks(browser, role)) return;
    const before = latestCodeFor(login);
    await submitPassword(page, login);
    await page.waitForURL(/dashboard|verify/, { timeout: 20_000 });
    if (page.url().includes("verify")) {
      // The code is written after the response returns, so it may not be on
      // disk the instant this runs, and the one already there is a previous
      // run's, which the server will reject.
      await page.getByLabel(/digit code/i).fill(await freshCode(login, before));
      await page.getByRole("button", { name: /verify and continue/i }).click();
      await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
    }
    // The shell renders after /auth/me resolves. Waiting for a nav link rather
    // than the URL is the difference between "signed in" and "the redirect
    // fired" - and a state file saved before the cookie settles is useless.
    await page.locator("#sidebar-nav a").first().waitFor({ state: "attached", timeout: 20_000 });
    fs.mkdirSync(STATE_DIR, { recursive: true });
    await context.storageState({ path: statePath(role) });
  });
}
