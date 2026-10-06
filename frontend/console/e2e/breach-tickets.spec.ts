/**
 * Breach tickets, end to end (S3-08).
 *
 * The DPO logs an incident, validates it a breach, and asks the DCO to act;
 * the DCO finds the ticket on Tickets - the breach reference and the ask,
 * nothing else from the register - writes and returns it; the DPO closes the
 * ticket, and only then does the breach close.
 *
 * Then a temporary holder (S3-09): the DPO asks somebody with no console
 * login by email; they set a password from the emailed code, sign in with the
 * second factor, land on Tickets, bring in a colleague and return their
 * ticket; when the breach closes their login stays, read only. The codes are
 * read from the dev outbox: the dev popup shows only the codes its own tab
 * caused, and the invitation is caused by the DPO's.
 */
import { expect, test, type Page } from "@playwright/test";

import { freshCode } from "./support/outbox";
import { STATE_DIR, statePath } from "./support/session";

test.describe.configure({ mode: "serial" });

function minutesAgo(minutes: number): string {
  const at = new Date(Date.now() - minutes * 60_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

const shared: { url: string; reference: string; title: string } = { url: "", reference: "", title: "" };

/** The breach page's sections are tabs; a tab's name carries its count. */
function openTab(page: Page, name: string) {
  return page.getByRole("tab", { name: new RegExp(`^${name}`) }).click();
}
/** The breach page without a tab in its address. */
const bare = (url: string) => url.split("#")[0];

test.describe("the DPO asks", () => {
  test.use({ storageState: statePath("dpo") });

  test("logs, records the breach, tells the board and assigns a ticket to the DCO", async ({ page }) => {
    shared.title = `E2E ticket breach ${Date.now()}`;
    await page.goto("/breaches");
    await page.getByRole("button", { name: "Log an incident" }).click();
    await page.getByLabel(/^Title/).fill(shared.title);
    await page.getByLabel(/^First noticed/).fill(minutesAgo(20));
    await page.getByRole("button", { name: "Log the incident" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-/);

    // Before the yes, nobody can be asked.
    await openTab(page, "Tickets");
    await expect(page.getByText("Tickets wait for the breach to be recorded")).toBeVisible();

    await openTab(page, "Validation");
    await page.getByLabel(/^Became aware at/).fill(minutesAgo(10));
    await page.getByLabel(/^Reasoning/).fill("Contact details were on the drive");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    shared.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();
    shared.url = bare(page.url());

    await openTab(page, "Duties");
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await orgBoard.getByRole("button", { name: "Record the report" }).click();
    await page.getByLabel(/^Reported at/).fill(minutesAgo(5));
    await page.getByLabel(/^Reported to/).fill("The chair, by phone");
    await page.getByRole("dialog").getByRole("button", { name: "Record", exact: true }).click();
    await expect(orgBoard.getByText("Done")).toBeVisible();

    await openTab(page, "Tickets");
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^Find them/).fill("dco@cmp.local");
    const who = dialog.getByLabel(/^Who/);
    await expect(who.locator("option", { hasText: "dco@cmp.local" })).toHaveCount(1);
    await who.selectOption({ label: (await who.locator("option", { hasText: "dco@cmp.local" }).textContent()) ?? "" });
    await dialog.getByLabel(/^What you are asking them to do/).fill("Export the drive's access log and keep it");
    await dialog.getByRole("button", { name: "Assign", exact: true }).click();
    const tickets = page.locator("#tickets");
    await expect(tickets.getByRole("row", { name: /Waiting on the holder/ })).toBeVisible();
  });
});

test.describe("the DCO answers", () => {
  test.use({ storageState: statePath("dco") });

  test("finds the ticket with the reference and the ask, writes and returns it", async ({ page }) => {
    await page.goto("/tickets");
    const card = page.getByTestId("breach-ticket").filter({ hasText: shared.reference });
    await expect(card).toBeVisible();
    await expect(card.getByText("Export the drive's access log and keep it")).toBeVisible();
    // Nothing else from the register reaches the holder.
    await expect(page.getByText(shared.title)).toHaveCount(0);

    await card.getByRole("button", { name: "Respond" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^When you return the ticket/).selectOption("done");
    await dialog.getByLabel("Message", { exact: true }).fill("Exported to the evidence share; nothing deleted.");
    await dialog.getByText("This is my return").click();
    await dialog.getByTestId("composer-send").click();
    await expect(page.getByText("Ticket returned")).toBeVisible();

    // The register is still not theirs.
    await page.goto(shared.url);
    await expect(page.getByText("Not part of your account")).toBeVisible();
  });
});

test.describe("the DPO closes", () => {
  test.use({ storageState: statePath("dpo") });

  test("closes the ticket, and only then can the breach close", async ({ page }) => {
    await page.goto(`${shared.url}#tickets`);
    // The open ticket is what stands in the way, among the rest.
    await expect(page.getByText("1 breach ticket is still open")).toBeVisible();
    const tickets = page.locator("#tickets");
    const row = tickets.getByRole("row", { name: /Returned/ });
    await expect(row).toBeVisible();
    // On a phone the table scrolls sideways inside its card, and the pointer's
    // hit-test lands on the card's header; the keyboard presses the same button.
    await row.getByRole("button", { name: "Open" }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Exported to the evidence share; nothing deleted.")).toBeVisible();
    await dialog.getByRole("button", { name: "Close the ticket" }).click();
    await expect(page.getByText("Ticket closed")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(tickets.getByRole("row", { name: /Closed/ })).toBeVisible();

    // Validated no after all: the DPDP duties set aside, nothing left open.
    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("The drive held test accounts only");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByText("Validation recorded")).toBeVisible();
    await expect(page.getByText("1 breach ticket is still open")).toHaveCount(0);
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
    // On a phone the toasts sit over the foot of the page until they fade.
    await expect(page.getByRole("region", { name: "Notifications" }).locator("p")).toHaveCount(0, {
      timeout: 15_000,
    });
    // At the foot of a phone's viewport the pointer's hit-test lands on the
    // card around it; the keyboard presses the same button.
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Breach closed")).toBeVisible();
  });
});

const temp: { url: string; reference: string; title: string; stamp: string; email: string; password: string } = {
  url: "",
  reference: "",
  title: "",
  stamp: "",
  email: "",
  password: "",
};
const holderState = (project: string) => `${STATE_DIR}/temporary-holder-${project}.json`;

async function signInAsHolder(page: Page): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel(/email or username/i).fill(temp.email);
  await page.getByLabel(/^password/i).fill(temp.password);
  await page.getByRole("button", { name: /^sign in$/i }).click();
}

test.describe("a temporary holder", () => {
  test("the DPO asks somebody without a console login, by email", async ({ browser }, info) => {
    const context = await browser.newContext({ storageState: statePath("dpo") });
    const page = await context.newPage();
    temp.stamp = `${Date.now()}-${info.project.name}`;
    temp.title = `E2E temporary holder ${temp.stamp}`;
    temp.email = `holder.${temp.stamp}@cmp.local`.toLowerCase();
    temp.password = `Holder-${temp.stamp}-Passw0rd!`;
    await page.goto("/breaches");
    await page.getByRole("button", { name: "Log an incident" }).click();
    await page.getByLabel(/^Title/).fill(temp.title);
    await page.getByLabel(/^First noticed/).fill(minutesAgo(20));
    await page.getByRole("button", { name: "Log the incident" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-/);
    await openTab(page, "Validation");
    await page.getByLabel(/^Became aware at/).fill(minutesAgo(10));
    await page.getByLabel(/^Reasoning/).fill("Contact details were on the drive");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    temp.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();
    temp.url = bare(page.url());

    await openTab(page, "Duties");
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await orgBoard.getByRole("button", { name: "Record the report" }).click();
    await page.getByLabel(/^Reported at/).fill(minutesAgo(5));
    await page.getByLabel(/^Reported to/).fill("The chair, by phone");
    await page.getByRole("dialog").getByRole("button", { name: "Record", exact: true }).click();
    await expect(orgBoard.getByText("Done")).toBeVisible();

    await openTab(page, "Tickets");
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Someone without a console login").check();
    await dialog.getByLabel(/^Their name/).fill(`Holder ${temp.stamp}`);
    await dialog.getByLabel(/^Their work email/).fill(temp.email);
    await dialog.getByLabel(/^What you are asking them to do/).fill("Pull the badge log for the server room");
    // On a phone the tall dialog's own body takes the pointer's hit-test at
    // the foot of the viewport; the keyboard presses the same button.
    await dialog.getByRole("button", { name: "Assign", exact: true }).focus();
    await page.keyboard.press("Enter");
    const row = page.locator("#tickets").getByRole("row", { name: new RegExp(`^Holder ${temp.stamp}`) });
    await expect(row.getByText("Temporary login · not yet signed in")).toBeVisible();
    await context.close();
  });

  test("sets a password, signs in with the second factor, adds a colleague and returns the ticket", async ({
    browser,
  }, info) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    // The invitation: the reset page, with the emailed code.
    await page.goto(`/sign-in/reset?email=${encodeURIComponent(temp.email)}`);
    await page.getByLabel(/^code/i).fill(await freshCode(temp.email, null));
    await page.getByLabel(/^New password/).fill(temp.password);
    await page.getByLabel(/^Confirm new password/).fill(temp.password);
    await page.getByRole("button", { name: "Set the new password" }).click();
    await page.waitForURL(/\/sign-in$/, { timeout: 15_000 });

    // Signs in like all staff: a password, then a code.
    await signInAsHolder(page);
    await page.waitForURL(/verify/, { timeout: 20_000 });
    await page.getByLabel(/digit code/i).fill(await freshCode(temp.email, null));
    await page.getByRole("button", { name: /verify and continue/i }).click();
    // Lands on its tickets: it has no dashboard.
    await page.waitForURL(/\/tickets/, { timeout: 20_000 });

    const card = page.getByTestId("breach-ticket").filter({ hasText: temp.reference });
    await expect(card.getByText("Pull the badge log for the server room")).toBeVisible();
    await expect(page.getByText(temp.title)).toHaveCount(0);

    await card.getByRole("button", { name: "Add a colleague" }).click();
    const add = page.getByRole("dialog");
    await add.getByLabel(/^Their name/).fill(`Colleague ${temp.stamp}`);
    await add.getByLabel(/^Their work email/).fill(`colleague.${temp.stamp}@cmp.local`.toLowerCase());
    await add.getByLabel(/^What you are asking them to do/).fill("Check the door controller's own log");
    await add.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByText("Colleague added")).toBeVisible();

    await card.getByRole("button", { name: "Respond" }).click();
    const respond = page.getByRole("dialog");
    await respond.getByLabel(/^When you return the ticket/).selectOption("done");
    await respond.getByLabel("Message", { exact: true }).fill("Badge log exported to the evidence share.");
    await respond.getByText("This is my return").click();
    await respond.getByTestId("composer-send").click();
    await expect(page.getByText("Ticket returned")).toBeVisible();

    // Nothing else in the console is theirs.
    await page.goto(temp.url);
    await expect(page.getByText("Not part of your account")).toBeVisible();
    await context.storageState({ path: holderState(info.project.name) });
    await context.close();
  });

  test("the DPO sees who added whom, closes the breach, and the login stays read only", async ({
    browser,
  }, info) => {
    const context = await browser.newContext({ storageState: statePath("dpo") });
    const page = await context.newPage();
    await page.goto(`${temp.url}#tickets`);
    const tickets = page.locator("#tickets");
    const holder = tickets.getByRole("row", { name: new RegExp(`^Holder ${temp.stamp}`) });
    const colleague = tickets.getByRole("row", { name: new RegExp(`^Colleague ${temp.stamp}`) });
    await expect(holder.getByText("Temporary login", { exact: true })).toBeVisible();
    await expect(colleague.getByText(`added by Holder ${temp.stamp}`)).toBeVisible();

    await colleague.getByRole("button", { name: "Open" }).focus();
    await page.keyboard.press("Enter");
    let dialog = page.getByRole("dialog");
    await expect(dialog.getByText("Check the door controller's own log")).toBeVisible();
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await dialog.getByLabel(/Why is it withdrawn/).fill("Covered by the first return");
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await expect(page.getByText("Ticket withdrawn")).toBeVisible();
    await expect(dialog.getByText("Temporary login · read only")).toBeVisible();
    // The reason is saved with the move, so closing does not ask about it.
    await page.keyboard.press("Escape");
    await expect(page.getByText(/not saved/i)).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(colleague.getByText("Temporary login · read only")).toBeVisible();

    await holder.getByRole("button", { name: "Open" }).focus();
    await page.keyboard.press("Enter");
    dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Close the ticket" }).click();
    await expect(page.getByText("Ticket closed")).toBeVisible();
    await page.keyboard.press("Escape");

    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("The drive held test accounts only");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByText("Validation recorded")).toBeVisible();
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
    await expect(page.getByRole("region", { name: "Notifications" }).locator("p")).toHaveCount(0, {
      timeout: 15_000,
    });
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Breach closed")).toBeVisible();
    await openTab(page, "Tickets");
    await expect(holder.getByText("Temporary login · read only")).toBeVisible();
    await context.close();

    // Their login stays, to read the ticket; nothing on it can be written.
    const gone = await browser.newContext({ storageState: holderState(info.project.name) });
    const after = await gone.newPage();
    await after.goto("/tickets");
    const card = after.getByTestId("breach-ticket").filter({ hasText: temp.reference });
    await expect(card.getByText("Closed")).toBeVisible();
    await expect(card.getByRole("button", { name: "Add a colleague" })).toHaveCount(0);
    await card.getByRole("button", { name: "Open" }).click();
    await expect(after.getByRole("dialog").getByText(/nothing further is needed from you/i)).toBeVisible();
    await gone.close();
  });
});
