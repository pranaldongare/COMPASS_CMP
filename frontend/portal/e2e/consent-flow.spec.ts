/**
 * End-to-end: the public consent flow.
 *
 * These run in a real browser because the things being tested only exist in one:
 * the HttpOnly session cookie the client cannot read, the double-submit CSRF
 * header, and the multi-step state of the consent journey.
 *
 * They need a running API and a seeded consent link:
 *
 *   E2E_CONSENT_TOKEN=<token from scripts/seed.py> npx playwright test
 *
 * Without the token the link-dependent tests skip rather than fail — a suite
 * that goes red because a fixture is missing trains people to ignore red.
 */
import { expect, test } from "@playwright/test";

import { freshCode, latestCodeFor } from "./support/outbox";

const TOKEN = process.env.E2E_CONSENT_TOKEN;

test.describe("invalid consent link", () => {
  // Same reason as the consent journey below: this hits the rate-limited public
  // surface, so it does not run alongside the tests that hammer it.
  test.describe.configure({ mode: "serial" });
  test("renders no notice content and does not say why", async ({ page }) => {
    await page.goto("/c/thisisnotarealtokenatall12345678");

    await expect(page.getByRole("heading", { name: /not valid/i })).toBeVisible();

    // Assert against the rendered main region, not `textContent("body")`: the
    // body also contains Next's RSC payload script, which mentions every route
    // in the app and makes a negative match meaningless.
    const main = page.locator("main");

    // The reason is deliberately *not* narrowed down. The page offers every
    // possibility at once - expired, withdrawn, mistyped - which helps a
    // legitimate visitor without telling a token-guesser which of their guesses
    // was structurally valid. Naming one would be the disclosure.
    await expect(main).toContainText(/expired.*withdrawn.*mistyped/is);

    // What it must never do is state a definite cause.
    await expect(main).not.toContainText(/has expired|was revoked|no such link/i);

    // And nothing from a real notice leaks onto the page.
    await expect(main).not.toContainText(/retention|data categories|purpose/i);
  });
});

/**
 * A contact nobody has used before.
 *
 * Registration is rate limited per contact - five an hour - and this journey
 * runs in three projects, twice each. A fixed number was therefore registered
 * six times a run; the sixth was refused, the form stayed on its first step,
 * and the test waited for a button that never came. Unique per call, so no
 * test shares a contact with another, or with a previous run.
 */
function freshContact() {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 1000)}`.slice(-9);
  return {
    email: `e2e.${stamp}@example.org`,
    mobile: `+9155${stamp.padStart(9, "0").slice(-8)}`,
  };
}

test.describe("consent journey", () => {
  test.skip(!TOKEN, "set E2E_CONSENT_TOKEN to a seeded link token");

  // Serial, and deliberately so. The public consent surface is rate limited per
  // address (60/min on the link, 5/hour per contact for codes), and parallel
  // workers share one address from the API's point of view. Running these
  // concurrently makes them contend with a control that is working correctly,
  // which produces failures that look like application bugs and are not.
  test.describe.configure({ mode: "serial" });

  test("asks for one contact, mobile by default, and never for a name", async ({
    page,
  }) => {
    await page.goto(`/c/${TOKEN}`);

    // Step 1: the link resolves and names the project and site.
    await expect(page.getByText(/your details/i).first()).toBeVisible();

    // The mobile is the default because a collection site is a place people
    // stand with a phone - and because a data principal may hold a mobile and
    // no email at all, which the register allows.
    await expect(page.getByRole("radio", { name: /^mobile$/i })).toBeChecked();
    await expect(page.getByLabel(/mobile number/i)).toBeVisible();

    // A name is not asked for. The artefact is bound to an account that already
    // carries one, and asking again would be collecting personal data with no
    // purpose - the thing this system exists to prevent.
    await expect(page.getByLabel(/full name/i)).toHaveCount(0);

    // Email is the alternative, not a second field to fill in as well.
    await page.getByRole("radio", { name: /^email$/i }).check();
    await expect(page.getByLabel(/email address/i)).toBeVisible();
    await expect(page.getByLabel(/mobile number/i)).toHaveCount(0);
  });

  test("offers a way to create an account that comes back here", async ({ page }) => {
    // Somebody without an account has to be able to get one without losing the
    // link: at a collection site, finding it again means asking a member of
    // staff to re-open it.
    await page.goto(`/c/${TOKEN}`);

    const create = page.getByRole("link", { name: /create one/i });
    await expect(create).toBeVisible();
    await expect(create).toHaveAttribute(
      "href",
      new RegExp(
        `/sign-up\\?next=${encodeURIComponent(`/c/${TOKEN}`).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`,
      ),
    );
  });

  test("advances to the code step without saying whether the contact is known", async ({
    page,
  }) => {
    await page.goto(`/c/${TOKEN}`);

    // A number nobody has registered. The server sends nothing and answers the
    // same as it would for a real one, so the screen must advance identically -
    // a flow that stopped here would answer "is this number on the register?"
    // to anybody who typed one in.
    const { mobile } = freshContact();
    await page.getByLabel(/mobile number/i).fill(mobile);
    await page.getByRole("button", { name: /send the code/i }).click();

    await expect(page.getByText(/confirm your mobile/i)).toBeVisible();
    await expect(page.getByLabel(/six-digit code/i)).toBeVisible();
  });

  test("a wrong code is refused without advancing", async ({ page }) => {
    await page.goto(`/c/${TOKEN}`);

    const { mobile } = freshContact();
    await page.getByLabel(/mobile number/i).fill(mobile);
    await page.getByRole("button", { name: /send the code/i }).click();

    await page.getByLabel(/six-digit code/i).fill("000000");
    await page.getByRole("button", { name: /confirm and read the notice/i }).click();

    // Scoped to main: Next appends its own role="alert" route announcer to the
    // body, so an unscoped getByRole("alert") matches two elements and fails
    // strict mode for a reason that has nothing to do with the app.
    await expect(page.locator("main").getByRole("alert")).toContainText(
      /invalid or expired/i,
    );
    // Still on the verification step: a rejected code must not let anyone past.
    await expect(page.getByLabel(/six-digit code/i)).toBeVisible();
  });

  test("an unknown age is asked for before the notice is served", async ({ page }) => {
    // S2-01. The server records no consent from an account whose age it does
    // not know, so the page asks between the code and the notice rather than
    // letting her read it and then refusing. A seeded staff account has no date
    // of birth until its owner gives one - every account may act as a data
    // principal - so the first run meets the question and answers it; later
    // runs find it answered and go straight to the notice.
    const contact = "rco@cmp.local";
    await page.goto(`/c/${TOKEN}`);
    await page.getByRole("radio", { name: /^email$/i }).check();
    const before = latestCodeFor(contact);
    await page.getByLabel(/email address/i).fill(contact);
    await page.getByRole("button", { name: /send the code/i }).click();
    await page.getByLabel(/six-digit code/i).fill(await freshCode(contact, before));
    await page.getByRole("button", { name: /confirm and read the notice/i }).click();

    const prompt = page.getByRole("heading", { name: /your date of birth/i });
    const notice = page.getByRole("button", { name: /decline everything/i });
    await expect(prompt.or(notice)).toBeVisible({ timeout: 15_000 });
    if (await prompt.isVisible()) {
      await expect(page.locator("main")).not.toContainText(/guardian|parent/i);
      await page.getByLabel(/date of birth/i).fill("1982-02-14");
      await page.getByRole("button", { name: /save and continue/i }).click();
    }
    await expect(notice).toBeVisible();
  });
});

test.describe("sign-in", () => {
  test("asks a data principal for a contact, never a password", async ({ page }) => {
    await page.goto("/sign-in");

    // The h1 names the task, not the product. The product name is a lockup
    // beside it - making it the heading would leave the page's only h1 saying
    // nothing about what the page is for.
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/sign in/i);
    // Two lockups exist - the brand panel's and the compact one - and which is
    // visible depends on the viewport. Filtering on visibility asserts "the user
    // can see the product name here" rather than which breakpoint drew it.
    await expect(
      page
        .getByText(/consent portal/i)
        .filter({ visible: true })
        .first(),
    ).toBeVisible();

    // A data subject has no password - `password_hash` is nullable for exactly
    // that reason - so this portal must never ask for one. Staff have their
    // own console, linked from the footer.
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await expect(page.getByRole("tab")).toHaveCount(0);
    await expect(page.getByRole("radio", { name: /^mobile$/i })).toBeChecked();
    await expect(page.getByRole("link", { name: /sign in to the console/i })).toBeVisible();
  });

  test("does not reveal whether a contact is registered", async ({ page }) => {
    await page.goto("/sign-in");
    await page.getByRole("radio", { name: /^email$/i }).check();
    await page.getByLabel(/email address/i).fill("definitely-not-a-user@example.org");
    await page.getByRole("button", { name: /send me a code/i }).click();

    // The same screen whether or not the contact exists. Anything more
    // specific turns the form into an oracle for who consented to a project.
    // An informational notice, not an error: role="status", because nothing
    // went wrong from the visitor's point of view whichever way it went.
    const notice = page.locator("main").getByRole("status").first();
    await expect(notice).toBeVisible();
    await expect(notice).toContainText(/if .* is registered/i);
    await expect(notice).not.toContainText(/no such|not found|does not exist|unknown/i);
  });
});

test.describe("rights page", () => {
  test("is public and states the Board route alongside ours", async ({ page }) => {
    await page.goto("/rights");

    await expect(page.getByRole("heading", { name: /your rights/i })).toBeVisible();

    // The content arrives from the API after first paint, so these must be
    // auto-retrying locator assertions rather than a one-shot text snapshot.
    const main = page.locator("main");

    // Rule 9 / Rule 14(1): telling someone only about the internal grievance
    // process misstates the remedy available to them.
    await expect(main).toContainText(/Data Protection Board/i, { timeout: 10_000 });
    await expect(main).toContainText(/withdraw/i);
    await expect(main).toContainText(/erasure|correction/i);
  });
});

test.describe("access control", () => {
  test("an unauthenticated visitor is sent to sign-in, not shown the page", async ({
    page,
  }) => {
    await page.goto("/projects");
    await page.waitForURL(/\/sign-in/);

    // The page must never flash its contents before redirecting - a flash of a
    // project list is a disclosure, however brief.
    await expect(page.locator("main")).not.toContainText(/Data Collection Owner/i);
  });

  test("the return path is preserved", async ({ page }) => {
    await page.goto("/projects");
    // The redirect carries the intended destination so the user lands where they
    // were going, not on a generic dashboard.
    await page.waitForURL(/\/sign-in\?next=/);
  });
});

test.describe("accessibility basics", () => {
  test("every page starts with a skip link and a single h1", async ({ page }) => {
    for (const path of ["/sign-in", "/rights"]) {
      await page.goto(path);

      const skip = page.getByRole("link", { name: /skip to content/i });
      await expect(skip).toBeAttached();

      // Exactly one h1: a page with none is unnavigable by heading, and a page
      // with several has no single answer to "what is this page".
      await expect(page.locator("h1")).toHaveCount(1);
    }
  });

  test("the consent form is reachable by keyboard alone", async ({ page }) => {
    await page.goto("/sign-in");

    // Skip link, then the first tab, then into the form.
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    const focused = await page.evaluate(() => document.activeElement?.tagName);
    expect(["INPUT", "BUTTON", "A"]).toContain(focused);
  });
});
