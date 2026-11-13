/**
 * Breach tickets, end to end (S3-08).
 *
 * The DPO logs an incident, validates it a breach, and asks the DCO to act
 * (the organisation's board is `breach-workflow.spec.ts`: a no sets its duty
 * aside here, as it does the rest);
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

/** Asked first (2026-11-12): whatever mails the board or a requester, or
 *  cannot be undone, raises a pop-up titled as a question. This says yes to
 *  it - its last button - and is a no-op where nothing was asked. */
async function yes(page: Page): Promise<void> {
  const question = page.getByRole("dialog").filter({ has: page.getByRole("heading", { name: /\?$/ }) });
  try {
    await question.waitFor({ state: "visible", timeout: 3_000 });
  } catch {
    return;
  }
  await question.getByRole("button").last().click();
  await question.waitFor({ state: "hidden" });
}

test.describe.configure({ mode: "serial" });

function minutesAgo(minutes: number): string {
  const at = new Date(Date.now() - minutes * 60_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** A day ahead of today, as a date input takes it, in the browser's own calendar. */
function daysAhead(days: number): string {
  const at = new Date(Date.now() + days * 86_400_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
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

  test("logs, records the breach and assigns a ticket to the DCO", async ({ page }) => {
    shared.title = `E2E ticket breach ${Date.now()}`;
    await page.goto("/breaches");
    await page.getByRole("button", { name: "Log an incident" }).click();
    await page.getByLabel(/^Title/).fill(shared.title);
    await page.getByLabel(/^First noticed/).fill(minutesAgo(20));
    await page.getByRole("button", { name: "Log the incident" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-/);

    // Before the yes, nobody can be asked.
    await openTab(page, "Tickets");
    await expect(page.getByText("Tickets are available once the breach is recorded")).toBeVisible();

    await openTab(page, "Validation");
    await page.getByLabel(/^Became aware at/).fill(minutesAgo(10));
    await page.getByLabel(/^Reasoning/).fill("Contact details were on the drive");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await yes(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    shared.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();
    shared.url = bare(page.url());

    await openTab(page, "Tickets");
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    // Found by typing: the matches are listed under the box as it is typed.
    await dialog.getByRole("combobox", { name: /^Assign to/ }).fill("dco@cmp.local");
    await dialog.getByRole("option").filter({ hasText: "dco@cmp.local" }).click();
    await dialog.getByLabel(/^Instruction/).fill("Export the drive's access log and keep it");
    await dialog.getByRole("button", { name: "Assign ticket" }).click();
    const tickets = page.locator("#tickets");
    const row = tickets.getByRole("row", { name: /Waiting on the holder/ });
    await expect(row).toBeVisible();

    // The date is given afterwards, with the reason - the control a rights
    // ticket has (2026-11-12) - and the window does not then ask about
    // unsaved changes. The keyboard presses the row's button, as on a phone.
    await row.getByRole("button", { name: "Open" }).focus();
    await page.keyboard.press("Enter");
    const opened = page.getByRole("dialog");
    await opened.getByRole("button", { name: "Change the date" }).click();
    await opened.getByLabel(/^New resolve by date/).fill(daysAhead(3));
    await opened.getByLabel(/^Reason/).fill("The log rotates on Friday");
    await opened.getByRole("button", { name: "Change the date" }).click();
    // The toast, not the line the ticket keeps of it.
    await expect(page.getByRole("region", { name: "Notifications" }).getByText("Date changed")).toBeVisible();
    await expect(opened.getByText(/Resolve by changed/).first()).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByText(/not saved/i)).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
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

    // The window opens on the answer, as a rights ticket's does (2026-11-12).
    await card.getByRole("button", { name: "Answer" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Did all of it").check();
    await dialog.getByLabel(/What you did, and how/).fill("Exported to the evidence share; nothing deleted.");
    await dialog.getByRole("button", { name: "Submit answer" }).click();
    await expect(page.getByText("Answer submitted")).toBeVisible();

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
    const row = tickets.getByRole("row", { name: /Answered - review/ });
    await expect(row).toBeVisible();
    // On a phone the table scrolls sideways inside its card, and the pointer's
    // hit-test lands on the card's header; the keyboard presses the same button.
    await row.getByRole("button", { name: "Review the answer" }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    // Their answer stands at the top of the window, and again among the messages.
    await expect(dialog.getByText("Exported to the evidence share; nothing deleted.").first()).toBeVisible();
    await dialog.getByRole("button", { name: "Close the ticket" }).click();
    await expect(page.getByText("Ticket closed")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(tickets.getByRole("row", { name: /Closed/ })).toBeVisible();

    // Validated no after all: the DPDP duties set aside, nothing left open.
    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("The drive held test accounts only");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await yes(page);
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
    await yes(page);
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
    await yes(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    temp.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();
    temp.url = bare(page.url());

    await openTab(page, "Tickets");
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Person without a console account").check();
    await dialog.getByLabel(/^Name/).fill(`Holder ${temp.stamp}`);
    await dialog.getByLabel(/^Work email/).fill(temp.email);
    await dialog.getByLabel(/^Instruction/).fill("Pull the badge log for the server room");
    // On a phone the tall dialog's own body takes the pointer's hit-test at
    // the foot of the viewport; the keyboard presses the same button.
    await dialog.getByRole("button", { name: "Assign ticket" }).focus();
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
    await add.getByLabel(/^Name/).fill(`Colleague ${temp.stamp}`);
    await add.getByLabel(/^Work email/).fill(`colleague.${temp.stamp}@cmp.local`.toLowerCase());
    await add.getByLabel(/^Instruction/).fill("Check the door controller's own log");
    await add.getByRole("button", { name: "Add colleague" }).click();
    await expect(page.getByText("Colleague added")).toBeVisible();

    await card.getByRole("button", { name: "Answer" }).click();
    const respond = page.getByRole("dialog");
    await respond.getByLabel("Did all of it").check();
    await respond.getByLabel(/What you did, and how/).fill("Badge log exported to the evidence share.");
    await respond.getByRole("button", { name: "Submit answer" }).click();
    await expect(page.getByText("Answer submitted")).toBeVisible();

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
    // What they were asked, and the same words as the first message.
    await expect(dialog.getByText("Check the door controller's own log").first()).toBeVisible();
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await dialog.getByLabel(/^Reason for withdrawing/).fill("Covered by the first return");
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await expect(page.getByText("Ticket withdrawn")).toBeVisible();
    await expect(dialog.getByText("Temporary login · read only")).toBeVisible();
    // The reason is saved with the move, so closing does not ask about it.
    await page.keyboard.press("Escape");
    await expect(page.getByText(/not saved/i)).toHaveCount(0);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(colleague.getByText("Temporary login · read only")).toBeVisible();

    await holder.getByRole("button", { name: "Review the answer" }).focus();
    await page.keyboard.press("Enter");
    dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Close the ticket" }).click();
    await expect(page.getByText("Ticket closed")).toBeVisible();
    await page.keyboard.press("Escape");

    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("The drive held test accounts only");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await yes(page);
    await expect(page.getByText("Validation recorded")).toBeVisible();
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
    await expect(page.getByRole("region", { name: "Notifications" }).locator("p")).toHaveCount(0, {
      timeout: 15_000,
    });
    await close.focus();
    await page.keyboard.press("Enter");
    await yes(page);
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
