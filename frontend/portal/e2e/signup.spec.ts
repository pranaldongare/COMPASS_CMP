/**
 * End-to-end: a data principal creates her account, mobile first.
 *
 * She gives a mobile and an email; a code goes to each; both are entered
 * together and she is signed in. A wrong pair is refused without spending the
 * right codes, which is why the same codes then work - the design under test.
 *
 * Desktop only: every run registers a fresh account and spends two codes, and
 * the phone project would spend two more for the same answer.
 */
import { expect, test } from "@playwright/test";

import { freshCode, latestCodeFor } from "./support/outbox";

test.skip(({ isMobile }) => Boolean(isMobile), "one registration per run is enough");

// Serial: the second test needs the account the first one made.
test.describe.configure({ mode: "serial" });

const stamp = Date.now().toString();
const MOBILE = `+91555${stamp.slice(-7)}`;
const EMAIL = `signup-${stamp.slice(-6)}@example.org`;

test("sign-up authenticates every contact given, then signs her in", async ({ page }) => {
  const mobileBefore = latestCodeFor(MOBILE);
  const emailBefore = latestCodeFor(EMAIL);

  await page.goto("/sign-up");
  await page.getByLabel(/full name/i).fill("Signup Principal");
  await page.getByLabel(/mobile number/i).fill(MOBILE);
  await page.getByLabel(/email address/i).fill(EMAIL);
  await page.getByLabel(/date of birth/i).fill("1990-01-01");
  await page.getByRole("button", { name: /create account/i }).click();

  await expect(page.getByRole("heading", { name: /confirm your contacts/i })).toBeVisible({
    timeout: 10_000,
  });

  // The wrong pair first: refused, and nothing spent.
  await page.getByLabel(/code sent to your mobile/i).fill("000000");
  await page.getByLabel(/code sent to your email/i).fill("000000");
  await page.getByRole("button", { name: /confirm and sign in/i }).click();
  // Filtered: Next.js adds a route announcer with the same role.
  await expect(page.getByRole("alert").filter({ hasText: /invalid|expired/i })).toBeVisible();

  // Then the real ones, one by SMS and one by email, from the same outbox.
  const mobileCode = await freshCode(MOBILE, mobileBefore);
  const emailCode = await freshCode(EMAIL, emailBefore);
  expect(mobileCode).not.toBe(emailCode);
  await page.getByLabel(/code sent to your mobile/i).fill(mobileCode);
  await page.getByLabel(/code sent to your email/i).fill(emailCode);
  await page.getByRole("button", { name: /confirm and sign in/i }).click();

  await expect(page).toHaveURL(/\/my-consents/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("a contact that is already registered is refused on its field, with sign-in offered", async ({
  page,
}) => {
  // The mobile the first test registered, with a different email. The form
  // must say which field is taken, stay on the details step so it can be
  // changed, and offer sign-in with that contact filled in - the person
  // typing it is most likely its owner, who has no password to remember.
  await page.goto("/sign-up");
  await page.getByLabel(/full name/i).fill("Signup Principal Again");
  await page.getByLabel(/mobile number/i).fill(MOBILE);
  await page.getByLabel(/email address/i).fill(`again-${stamp.slice(-6)}@example.org`);
  await page.getByLabel(/date of birth/i).fill("1990-01-01");
  await page.getByRole("button", { name: /continue|create/i }).click();

  await expect(page.getByText(/that mobile is already registered/i)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /confirm your contacts/i })).toHaveCount(0);
  const signIn = page.getByRole("link", { name: /sign in with this mobile/i });
  await expect(signIn).toBeVisible();
  expect(await signIn.getAttribute("href")).toContain(encodeURIComponent(MOBILE));
});
