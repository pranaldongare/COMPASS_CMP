/**
 * A data principal's own pages: the API serves their name, contacts, consents
 * and requests sealed, and the interceptor opens them before the page renders.
 * Here that is checked on the screen, as the person would see it.
 */
import { test, expect, type Page } from "@playwright/test";

import { statePath } from "./support/session";

test.use({ storageState: statePath("subject") });

function watchSealed(page: Page): { sawSealed: () => boolean } {
  let sealed = 0;
  page.on("response", async (response) => {
    const type = response.headers()["content-type"] ?? "";
    if (!response.url().includes("/api/") || !type.includes("application/json")) return;
    try {
      if ((await response.text()).includes('"SE::')) sealed += 1;
    } catch {
      // body already released
    }
  });
  return { sawSealed: () => sealed > 0 };
}

for (const path of ["/my-consents", "/account", "/my-requests"]) {
  test(`${path} shows the person, never ciphertext`, async ({ page }) => {
    const watch = watchSealed(page);
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    const text = await page.locator("body").innerText();
    expect(text, `ciphertext rendered on ${path}`).not.toContain("SE::");
    if (path === "/account") {
      // The account page always carries the person's own name and contact,
      // so here the API is required to have sealed something - otherwise a
      // database with everything in the clear would pass this file trivially.
      expect(watch.sawSealed(), "the API served the account sealed").toBe(true);
      expect(text).toMatch(/[^\s@]+@[^\s@]+\.[^\s@]+|\+91/);
    } else if (!watch.sawSealed()) {
      test.info().annotations.push({
        type: "note",
        description: `no API response on ${path} carried a sealed value`,
      });
    }
  });
}
