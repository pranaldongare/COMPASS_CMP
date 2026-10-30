/**
 * End-to-end: an employee's `sso` consent link (ADR 0034), signed in through
 * the API's stand-in for the organisation's sign-in (`SSO_MOCK`).
 *
 * The journey crosses every leg the public relay had to learn (ADR 0035): the
 * start, the stand-in's `/dev/sso/*`, the callback whose 303 is the one
 * redirect that crosses, the pending employee's cookie on the mobile step, and
 * the session at the end. It runs the same against a portal that calls the API
 * directly and one whose `/api` is the relay's bridge.
 *
 * It needs the raw token of an `sso` link (an HR activity's), an API with
 * `SSO_MOCK=true`, and `PUBLIC_BASE_URL` and `SSO_REDIRECT_URL` naming the
 * portal under test, which the stand-in sends the browser to:
 *
 *   E2E_SSO_TOKEN=<token> npx playwright test e2e/sso-link.spec.ts
 *
 * Without the token it skips. Each run creates an employee account with a new
 * address and mobile, as the first sign-in of an employee does.
 */
import { expect, test } from "@playwright/test";

import { freshCode, latestCodeFor } from "./support/outbox";

const TOKEN = process.env.E2E_SSO_TOKEN;
const VIA_RELAY = !!process.env.E2E_VIA_RELAY;

test.describe("an employee's sso link", () => {
  test.skip(!TOKEN, "set E2E_SSO_TOKEN to an sso link's token");
  // The link and the code routes are rate limited per address, like the
  // consent journey's.
  test.describe.configure({ mode: "serial" });

  test("signs a new employee in through the organisation, then a mobile", async ({
    page,
  }) => {
    const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-9);
    const email = `e2e.sso.${stamp}@corp.example`;
    const mobile = `+9155${stamp.padStart(9, "0").slice(-8)}`;

    await page.goto(`/c/${TOKEN}`);
    await expect(
      page.getByText("Sign in with your organisation account", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: /continue with your organisation account/i })
      .click();

    // The stand-in's page, where the organisation's sign-in would be.
    await page.waitForURL(/\/sso-mock\?/);
    await page.getByLabel(/work email/i).fill(email);
    const before = latestCodeFor(email);
    await page.getByRole("button", { name: /send a code/i }).click();
    await page.getByLabel(/the code we sent/i).fill(await freshCode(email, before));
    await page.getByRole("button", { name: /^sign in$/i }).click();

    // Back through the callback's 303 to the link: a new employee confirms a
    // mobile first. The address is the link's own path on this portal.
    await page.waitForURL(new RegExp(`/c/${TOKEN}\\?sso=mobile$`));
    await page.getByLabel(/mobile number/i).fill(mobile);
    const previous = latestCodeFor(mobile);
    await page.getByRole("button", { name: /send a code/i }).click();
    await page.getByLabel(/the code we sent/i).fill(await freshCode(mobile, previous));
    const verified = page.waitForResponse((r) => r.url().includes("/sso/mobile/verify"));
    await page.getByRole("button", { name: /^confirm$/i }).click();
    expect((await verified).ok()).toBe(true);
    // The account is new and has no date of birth, so the link asks for one
    // before the notice: the step it settles on, signed in.
    await expect(page.getByRole("heading", { name: /your date of birth/i })).toBeVisible({
      timeout: 10_000,
    });

    // Signed in as a data principal, in no office, on an employee account.
    const origin = new URL(page.url()).origin;
    const me = await page.request.get(`${origin}/api/auth/me`);
    expect(me.ok()).toBe(true);
    const body = await me.json();
    expect(body).toMatchObject({
      role: "data_subject",
      office: null,
      person_type: "employee",
      status: "active",
    });
    if (VIA_RELAY) {
      // The relay's reply carries no sealed value: the API opened them.
      expect(body.mobile).toBe(mobile);
      expect(String(body.full_name)).not.toMatch(/^SE::/);
    }
  });
});
