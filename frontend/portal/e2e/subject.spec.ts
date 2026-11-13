/**
 * A data principal stays on her own side of the product.
 *
 * Reported: opening Notifications as a data subject led to an admin screen. The
 * feed itself was correct — her own events and nothing else — but every row
 * carried a link resolved for staff, and her registration event resolved to
 * `/users`, the administrator's account register.
 *
 * Two things are tested because there were two faults: the link is no longer
 * offered, and the page no longer renders if something else produces the URL.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

test.describe("data subject", () => {
  test.use({ storageState: statePath("subject") });

  test("her notifications link to her own pages, never a console", async ({ page }) => {
    await page.goto("/notifications");
    await expect(page.getByRole("heading", { name: /updates/i }).first()).toBeVisible();

    // Every link on the page has to be somewhere she can go. Asserted over all
    // of them rather than the first: the bug was one entity type among several.
    const hrefs = await page.locator("main a[href^='/']").evaluateAll((links) =>
      links.map((l) => l.getAttribute("href") ?? ""),
    );
    const staffOnly = hrefs.filter((h) =>
      /^\/(users|consents|notices|projects|audit|sources|processors|sites|links|exports|imports|collections|approvals|purposes)(\/|$)/.test(
        h,
      ),
    );
    expect(staffOnly, `staff routes offered to a data subject: ${staffOnly}`).toEqual([]);
  });

  test("a staff URL does not exist on this portal", async ({ page }) => {
    // The second half. Whatever produced the URL — an old link, a bookmark, a
    // notification from before the fix — the account register is not her page.
    // On this deployment it is not a page at all.
    const response = await page.goto("/users");

    expect(response?.status()).toBe(404);
    await expect(page.getByRole("button", { name: /create account|provision/i })).toHaveCount(0);
  });

  test("her own sections still work", async ({ page }) => {
    // The guard must not have locked her out of her own product.
    for (const path of [
      "/home",
      "/my-consents",
      "/my-requests",
      "/account",
      "/notifications",
    ]) {
      await page.goto(path);
      await expect(page.getByText(/not part of your account/i)).toHaveCount(0);
    }
  });

  test("a consent opens beside the list: its purposes, the notice she was given, its history and its record", async ({
    page,
  }) => {
    // My consents is a list and a detail (2026-11-12). Each tab reads from the
    // API when it is opened, and the record is a file: all four are calls a
    // portal on the far side of the relay has to be able to make.
    await page.goto("/my-consents");
    const list = page.getByRole("list", { name: "Your consents" });
    test.skip((await list.count()) === 0, "the seeded data principal has no consent on this database");
    await expect(page.getByRole("tab", { name: /^Purposes/ })).toBeVisible();

    const ok = (part: string) =>
      page.waitForResponse((r) => new URL(r.url()).pathname.endsWith(part) && r.request().method() === "GET");
    const [notice] = await Promise.all([ok("/notice"), page.getByRole("tab", { name: "Notice" }).click()]);
    expect(notice.status()).toBe(200);
    const [trail] = await Promise.all([ok("/trail"), page.getByRole("tab", { name: "History" }).click()]);
    expect(trail.status()).toBe(200);

    const [file] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download record" }).click(),
    ]);
    expect(file.suggestedFilename()).toMatch(/\.pdf$/);
    // Nothing she is shown is ciphertext, on either side of the relay.
    await expect(page.locator("main")).not.toContainText("SE::");
  });
});
