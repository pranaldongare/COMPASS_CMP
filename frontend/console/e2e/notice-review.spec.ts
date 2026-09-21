/**
 * The officer's half of a notice, on the notice.
 *
 * An imported document leaves its purposes as drafts, because only the Privacy
 * Office may activate them and an author who could do it by uploading a file
 * would be approving their own. The officer therefore has nine decisions to
 * take, and they used to be taken somewhere else: the checklist named a purpose
 * code, and the only control that acted on it was a row in the purposes
 * register, reached by a different route, filtered by hand.
 *
 * So this asserts the two things that moved. Every blocking line points at the
 * card that clears it, and the purposes can be activated from the notice that
 * carries them, one at a time, which is the review the separate decisions are
 * there to make somebody do.
 *
 * **It picks its notice rather than taking the first.** Activating a purpose is
 * a real write against the development database, so this spec consumes the
 * thing it needs: after enough runs the first draft in the list has nothing
 * blocking left, and the assertions failed on a notice that was simply finished
 * rather than on anything being wrong. So it asks the API which draft still has
 * work outstanding, and skips - loudly - when none does.
 */
import { expect, test, type Page } from "@playwright/test";

import { statePath } from "./support/session";

/** A draft notice whose checklist still blocks, or null if every one is clear.
 *
 *  Through the console's own `/api` proxy, so it carries the same session
 *  cookie the browser does and needs no second set of credentials. */
async function aDraftStillBlocking(
  page: Page,
  wanted?: (blocking: string[]) => boolean,
): Promise<string | null> {
  const list = await page.request.get("/api/notices?status=draft&limit=25");
  if (!list.ok()) return null;
  const { items = [] } = (await list.json()) as { items?: { notice_uuid: string }[] };

  for (const { notice_uuid } of items) {
    const res = await page.request.get(`/api/notices/${notice_uuid}/checklist`);
    if (!res.ok()) continue;
    const { blocking = [] } = (await res.json()) as { blocking?: string[] };
    if (blocking.length && (!wanted || wanted(blocking))) return notice_uuid;
  }
  return null;
}

test.describe("a draft notice, as the Privacy Office", () => {
  test.use({ storageState: statePath("dpo") });

  test("every blocker points at what clears it", async ({ page }) => {
    await page.goto("/notices?status=draft");
    const uuid = await aDraftStillBlocking(page);
    test.skip(uuid === null, "every draft notice is publishable - nothing to point at");

    await page.goto(`/notices/${uuid}`);
    await expect(page).toHaveURL(/\/notices\/[0-9a-f-]{36}/, { timeout: 15_000 });

    await expect(page.getByText(/blocking publication/i)).toBeVisible({ timeout: 15_000 });
    const lines = page
      .getByRole("listitem")
      .filter({ hasText: /purpose|text|URL|addresses/i });
    await expect(lines.first()).toBeVisible();

    // The links land on this page, at the card that fixes the line.
    const fix = page.getByRole("link", { name: /fix this/i }).first();
    await expect(fix).toBeVisible();
    await expect(fix).toHaveAttribute("href", /#notice-(purposes|languages|rule3)/);

    // And the anchors exist, so the link is not a promise to nowhere.
    await expect(page.locator("#notice-purposes")).toBeAttached();
    await expect(page.locator("#notice-languages")).toBeAttached();
  });

  test("a draft purpose is activated from the notice that carries it", async ({ page }) => {
    await page.goto("/notices?status=draft");
    const uuid = await aDraftStillBlocking(page, (lines) =>
      lines.some((line) => /not activated/i.test(line)),
    );
    test.skip(uuid === null, "no draft notice is carrying an unactivated purpose");

    await page.goto(`/notices/${uuid}`);
    await expect(page).toHaveURL(/\/notices\/[0-9a-f-]{36}/, { timeout: 15_000 });
    await expect(page.getByText(/blocking publication/i)).toBeVisible({ timeout: 15_000 });

    const activate = page.getByRole("button", { name: /^activate$/i });
    const before = await activate.count();
    expect(
      before,
      "the checklist named one, so the control has to be here",
    ).toBeGreaterThan(0);

    const blocking = page.getByText(/item\(s\) blocking publication/i);
    const said = (await blocking.innerText()).trim();

    await activate.first().click();

    // One fewer control, and one fewer line, without a reload: activating a
    // purpose is what clears a checklist line, so both queries are invalidated.
    await expect(activate).toHaveCount(before - 1, { timeout: 15_000 });
    await expect(blocking).not.toHaveText(said, { timeout: 15_000 });
  });
});
