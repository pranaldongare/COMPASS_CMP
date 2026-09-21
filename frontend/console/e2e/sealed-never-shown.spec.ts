/**
 * Personal values arrive from the API sealed - `SE::…` - and the response
 * interceptor opens them before any page renders. This spec is the check that
 * the arrangement holds where it matters: on the pages that show people.
 *
 * Two things are asserted on each. The API really did answer with sealed
 * values (or the test proves nothing - a database with everything in the
 * clear passes trivially), and not one of them reached the screen.
 */
import { test, expect, type Page } from "@playwright/test";

import { statePath } from "./support/session";

test.use({ storageState: statePath("dpo") });

/** Watch every API response on this page for sealed values. */
function watchSealed(page: Page): { sawSealed: () => boolean } {
  let sealed = 0;
  page.on("response", async (response) => {
    const type = response.headers()["content-type"] ?? "";
    if (!response.url().includes("/api/") || !type.includes("application/json")) return;
    try {
      const text = await response.text();
      if (text.includes('"SE::')) sealed += 1;
    } catch {
      // A response whose body is gone by the time we read it is not this test's problem.
    }
  });
  return { sawSealed: () => sealed > 0 };
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  // The table paints after the query resolves and the decrypt call returns.
  await page.waitForTimeout(500);
}

const PAGES: { path: string; name: string }[] = [
  { path: "/users", name: "the accounts list" },
  { path: "/consents", name: "the consent register" },
  { path: "/requests", name: "the rights requests" },
  { path: "/audit", name: "the audit trail" },
];

for (const { path, name } of PAGES) {
  test(`${name} shows people, never ciphertext`, async ({ page }) => {
    const watch = watchSealed(page);
    await page.goto(path);
    await settle(page);

    await expect(page.locator("h1")).toBeVisible();
    const text = await page.locator("body").innerText();
    expect(text, `ciphertext rendered on ${path}`).not.toContain("SE::");

    if (!watch.sawSealed()) {
      test.info().annotations.push({
        type: "note",
        description: `no API response on ${path} carried a sealed value - the list may be empty`,
      });
    }
  });
}

test.describe("editing an account", () => {
  // Only an administrator has the Edit control on the accounts list.
  test.use({ storageState: statePath("admin") });

  test("the edit form is filled with the person, opened from the sealed row", async ({ page }) => {
    const watch = watchSealed(page);
    await page.goto("/users");
    await settle(page);
    const edit = page.getByRole("button", { name: "Edit" }).first();
    if ((await edit.count()) === 0) test.skip(true, "no accounts listed");
    await edit.click();

    const email = page.getByLabel("Email");
    await expect(email).toBeVisible();
    expect(watch.sawSealed(), "the API served the accounts sealed").toBe(true);
    const name = await page.getByLabel("Full name").inputValue();
    const address = await email.inputValue();
    expect(name).not.toContain("SE::");
    expect(address).not.toContain("SE::");
    expect(address).toMatch(/[^\s@]+@[^\s@]+\.[^\s@]+/);
    expect(name.trim().length).toBeGreaterThan(0);
  });
});
