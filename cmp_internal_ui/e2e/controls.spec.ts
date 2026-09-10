/**
 * No write control where the matrix grants no write.
 *
 * The sidebar is generated from the server's table, so it cannot drift. The
 * buttons inside a page are placed by hand, and a page that offers "Register"
 * to a role the API refuses is a control that 403s on click - the same fault
 * the navigation test was written for, one level down.
 *
 * The server says which resources a role may write (`me.writes`). For every
 * section in the role's navigation whose resource is not among them, the page
 * must offer no control whose name is a write. Where a write is granted the
 * page may offer what it likes; this test only ever asserts absence.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

const API = process.env.E2E_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** The resource each section is about, by its route. Personal sections are
 * not here: tickets, notifications and the profile are the account's own. */
const RESOURCE_OF: Record<string, string> = {
  "/projects": "project",
  "/approvals": "approval",
  "/notices": "notice",
  "/purposes": "purpose",
  "/consents": "consent",
  "/links": "link",
  "/sites": "site",
  "/processors": "processor",
  "/sources": "data_source",
  "/collections": "collection",
  "/exports": "export",
  "/imports": "import",
  "/requests": "rights_request",
  "/audit": "audit",
  "/users": "user",
};

/** Verbs that change something. "Show", "Hide", "Download" and "Open" are reads. */
const WRITE_VERB =
  /^(register|create|new|add|publish|approve|reject|suspend|reinstate|delete|remove|revoke|edit|upload|import|mint|provision|assign|withdraw|issue|log a request|generate|record|derive|confirm|escalate|reassign|remind)\b/i;

const ROLES = ["dco", "rnd", "dcoadmin", "rco", "dpo", "admin"] as const;

test.describe.configure({ mode: "serial" });

for (const role of ROLES) {
  test.describe(role, () => {
    test.use({ storageState: statePath(role) });

    test("offers no write control where the matrix grants no write", async ({ page, request }) => {
      const me = (await (await request.get(`${API}/auth/me`)).json()) as {
        nav: string[];
        writes: string[];
        role: string;
      };
      expect(Array.isArray(me.writes), "the session carries the role's writes").toBe(true);

      await page.goto("/dashboard");
      await page.locator("#sidebar-nav a").first().waitFor({ state: "attached", timeout: 15_000 });
      const hrefs = (await page
        .locator("#sidebar-nav a")
        .evaluateAll((links) => links.map((a) => (a as HTMLAnchorElement).getAttribute("href") ?? ""))) as string[];

      const offered: string[] = [];
      for (const href of hrefs) {
        const resource = RESOURCE_OF[href];
        if (!resource || me.writes.includes(resource)) continue;
        await page.goto(href);
        await expect(page.locator("h1")).toHaveCount(1);
        await page.waitForLoadState("networkidle").catch(() => {});
        const names = (await page
          .locator("main button, main a[role=button], main [data-testid=page-actions] a")
          .evaluateAll((els) => els.map((el) => (el.textContent ?? "").trim()))) as string[];
        for (const name of names) {
          if (WRITE_VERB.test(name)) offered.push(`${href}: "${name}"`);
        }
      }
      expect(offered, `${me.role} is offered write controls it may not use`).toEqual([]);
    });
  });
}
