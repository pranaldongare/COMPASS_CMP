/**
 * Every nav destination must load, for every role.
 *
 * This is the test that would have caught the original problem: the sidebar was
 * rendered from `me.nav`, but most of those destinations had no page behind them,
 * so the product shipped a menu of 404s. Asserting "the link exists" would not
 * have caught it either - the link existed. The assertion has to be that
 * following it produces a page.
 *
 * Runs serially: these are authenticated sessions against a rate-limited API.
 */
import { expect, test } from "@playwright/test";

import { statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

/** Every staff role. The setup project reads the MFA code from the dev outbox. */
const ROLES = [
  {
    role: "dco",
    name: "DCO",
    // `/sources` because a collection owner registers the rigs they will run.
    // Which processor they may register under is the constraint, not whether.
    expected: [
      "/dashboard",
      "/projects",
      "/sites",
      "/sources",
      "/links",
      "/consents",
      "/exports",
      "/imports",
      "/collections",
      "/cover",
    ],
  },
  {
    role: "rnd",
    name: "R&D User",
    // `/notices` and `/processors` because the author now writes the notice and
    // names who will collect. Both used to be the DPO's, and both were things
    // the DPO had to be told before they could enter them.
    expected: [
      "/dashboard",
      "/projects",
      "/notices",
      "/processors",
      "/approvals",
      "/imports",
      "/collections",
    ],
  },
  {
    role: "dcoadmin",
    name: "DCO Admin",
    // `/sources` is the difference from a DCO, and it is the whole job: the
    // routing queue is sources with nobody accountable, and making somebody
    // accountable is what moves a project.
    expected: [
      "/dashboard",
      "/projects",
      "/sites",
      "/sources",
      "/links",
      "/consents",
      "/exports",
      "/imports",
      "/collections",
      "/cover",
    ],
  },
  {
    role: "dpo",
    name: "DPO",
    // Oversight reaches everything it may read: approvals, sites and
    // collections had read rights and no way in except through a project.
    expected: [
      "/dashboard",
      "/projects",
      "/approvals",
      "/notices",
      "/purposes",
      "/sites",
      "/collections",
      "/processors",
      "/sources",
      "/consents",
      "/links",
      "/exports",
      "/imports",
      "/requests",
      "/audit",
      "/users",
      "/cover",
    ],
  },
  {
    role: "admin",
    name: "Administrator",
    // Accounts, lockouts, cover, the registry, and the grievances escalated
    // away from the DPO - which is what "/requests" is for this role.
    expected: ["/dashboard", "/users", "/processors", "/sources", "/requests", "/audit", "/cover"],
  },
  {
    role: "rco",
    name: "RCO",
    // The same sections as a DCO. The difference is which processors their
    // registry offers — in-house rather than a third party's — not which pages
    // they can open.
    expected: [
      "/dashboard",
      "/projects",
      "/sites",
      "/sources",
      "/links",
      "/consents",
      "/exports",
      "/imports",
      "/collections",
      "/cover",
    ],
  },
];

for (const role of ROLES) {
  test.describe(`${role.name}`, () => {
    // Each role's session is saved once by the setup project. Signing in here
    // would put four workers through the login endpoint as the same account and
    // trip the lockout.
    test.use({ storageState: statePath(role.role) });

    test("every sidebar link reaches a real page", async ({ page }) => {
      await page.goto("/dashboard");
      await page
        .locator("#sidebar-nav a")
        .first()
        .waitFor({ state: "attached", timeout: 15_000 });

      // Take the destinations from the rendered sidebar, not from a hardcoded
      // list: the sidebar is built from what the *server* says this role has, so
      // this asserts against the real contract rather than our assumption of it.
      const hrefs = await page
        .locator("#sidebar-nav a")
        .evaluateAll((links) =>
          links.map((a) => (a as HTMLAnchorElement).getAttribute("href")).filter(Boolean),
        );

      expect(hrefs.length, "the sidebar rendered no links").toBeGreaterThan(0);

      for (const href of hrefs) {
        const failures: string[] = [];
        page.on("response", (r) => {
          if (r.status() >= 500) failures.push(`${r.status()} ${r.url()}`);
        });

        await page.goto(href!);

        // Not a 404 shell, and not an empty body.
        await expect(
          page.getByText(/this page could not be found/i),
          `${href} rendered Next's 404`,
        ).toHaveCount(0);

        // The page heading proves a real page rendered, not a blank route.
        await expect(page.locator("h1"), `${href} has no heading`).toHaveCount(1);

        expect(failures, `${href} produced a server error`).toEqual([]);
        page.removeAllListeners("response");
      }
    });

    test("the expected sections are present", async ({ page }) => {
      await page.goto("/dashboard");
      await page
        .locator("#sidebar-nav a")
        .first()
        .waitFor({ state: "attached", timeout: 15_000 });

      const hrefs = await page
        .locator("#sidebar-nav a")
        .evaluateAll((links) =>
          links.map((a) => (a as HTMLAnchorElement).getAttribute("href")),
        );

      for (const expected of role.expected) {
        expect(hrefs, `${role.name} is missing ${expected}`).toContain(expected);
      }
    });

    test("no section this role may not use is offered", async ({ page }) => {
      await page.goto("/dashboard");
      await page
        .locator("#sidebar-nav a")
        .first()
        .waitFor({ state: "attached", timeout: 15_000 });

      const hrefs = await page
        .locator("#sidebar-nav a")
        .evaluateAll((links) =>
          links.map((a) => (a as HTMLAnchorElement).getAttribute("href")),
        );

      // Nothing beyond what this role expects: the sidebar is the server's
      // list, and the list here is the role's charter. A link outside it is a
      // section somebody widened without deciding to.
      const personal = ["/tickets", "/notifications", "/account"];
      for (const href of hrefs) {
        expect(
          [...role.expected, ...personal],
          `${role.name} is offered ${href}, which is outside its charter`,
        ).toContain(href);
      }
    });
  });
}
