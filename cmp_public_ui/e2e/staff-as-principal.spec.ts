/**
 * A member of staff is also a data principal.
 *
 * The DPO's corporate address signs her in here with a code, like anybody's,
 * and what she gets is a data principal's session and nothing more: her own
 * consents, requests and rights, and none of the console. Before this the same
 * code minted a session with every power her role has - the password and the
 * second factor that every staff role requires, bypassed by reading one email.
 *
 * Codes are read from the dev outbox, so this needs the running stack and the
 * seeded accounts.
 */
import { expect, test } from "@playwright/test";

import { freshCode, latestCodeFor } from "./support/outbox";

const DPO = "dpo@cmp.local";

async function signInByEmail(page: import("@playwright/test").Page, contact: string) {
  const before = latestCodeFor(contact);
  await page.goto("/sign-in");
  await page.getByRole("radio", { name: /^email$/i }).check();
  await page.getByLabel(/email address/i).fill(contact);
  await page.getByRole("button", { name: /send.*code|continue/i }).click();
  await page.getByLabel(/six-digit code/i).fill(await freshCode(contact, before));
  await page.getByRole("button", { name: /^verify$/i }).click();
  await page.waitForURL(/\/my-consents/, { timeout: 20_000 });
}

test.describe("a member of staff on the portal", () => {
  // Serial: the sign-in codes for one address are capped per hour.
  test.describe.configure({ mode: "serial" });

  test("signs in with a code and is a data principal here, nothing more", async ({
    page,
  }) => {
    await signInByEmail(page, DPO);

    // She is told which account this is, and where the console lives.
    await expect(page.getByText(/signed in with your staff account/i)).toBeVisible();

    // The session acts as a data principal; the row still says DPO.
    const me = (await (await page.request.get("/api/auth/me")).json()) as {
      role: string;
      account_role: string;
      nav: string[];
    };
    expect(me.role).toBe("data_subject");
    expect(me.account_role).toBe("dpo");
    expect(me.nav).not.toContain("audit");
    expect(me.nav).not.toContain("users");

    // And the console's endpoints refuse this session - the whole point.
    for (const path of ["/api/users", "/api/audit", "/api/requests", "/api/notices"]) {
      expect((await page.request.get(path)).status(), path).toBe(403);
    }
    // While her own record answers.
    expect((await page.request.get("/api/me/consents")).status()).toBe(200);
  });

  test("adds a personal address and confirms it with the code sent there", async ({
    page,
  }) => {
    await signInByEmail(page, DPO);
    await page.goto("/account");

    const row = page.getByTestId("contact-secondary_email");
    await expect(row).toBeVisible();

    const personal = `personal-${Date.now()}@example.org`;
    const before = latestCodeFor(personal);
    await row.getByRole("button", { name: /^(add|change)$/i }).click();
    await row.getByLabel(/email/i).fill(personal);
    await row.getByRole("button", { name: /save and send a code/i }).click();

    // Saved, unconfirmed, and asking for the code that was just sent. Exact,
    // because the address also appears inside the "sent to ..." hint.
    await expect(row.getByText(personal, { exact: true })).toBeVisible();
    await expect(row.getByText(/not confirmed/i)).toBeVisible();
    await row.getByLabel(/six-digit code/i).fill(await freshCode(personal, before));
    await row.getByRole("button", { name: /^confirm$/i }).click();

    await expect(row.getByText(/^confirmed$/i)).toBeVisible({ timeout: 10_000 });
  });
});
