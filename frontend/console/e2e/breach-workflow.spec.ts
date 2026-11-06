/**
 * A breach from the public link to the last report (ADR 0037).
 *
 * One serial journey, against the real API and worker, with the dev outbox as
 * the witness of who was mailed what:
 *
 * - the administrator keeps the board's addresses and who is told of a report;
 * - a stranger's report, made on the public API with a code from the outbox,
 *   waits in the intake both offices share, with no clock running;
 * - the DPO claims it, which takes it off the Legal office's screen, and
 *   validates it: only then is the organisation's board owed, thirty minutes
 *   from that yes;
 * - Notify Organization Board mails the list, with the report as a PDF;
 * - the regulators' reports are drafted, finalised (which mails the board and
 *   nobody else) and recorded as sent with both proofs: the platform sends
 *   nothing to a regulator;
 * - the people affected are found by project and by an Excel list, and one
 *   button reaches them all;
 * - a ticket goes out with a document, and both sides move its date with a
 *   reason, on the thread and on the trail.
 *
 * It lists people from the dev database on purpose, so it takes the smallest
 * project and unticks all but one. What it adds to the board's list and the
 * role it ticks are taken off again through the API after the last test.
 *
 * Set E2E_SHOT_DIR to save each main screen at desktop and at phone width, with
 * a note beside them of any page that scrolls sideways or uses a word retired
 * from the screens.
 */
import { expect, request, test, type Browser, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

import { entriesSince, freshCode, outboxMark, type OutboxEntry } from "./support/outbox";
import { statePath } from "./support/session";
import { workbook } from "./support/workbook";

test.describe.configure({ mode: "serial" });

const API = process.env.E2E_API_URL ?? "http://127.0.0.1:8000";
const SHOTS = process.env.E2E_SHOT_DIR;

/** Who the seed puts in each office's officer role, and the HR PoC we tick. */
const DPO = "dpo@cmp.local";
const LEGAL = "meera.nair@cmp.local";
const HR_POC = "rahul.desai@cmp.local";

const stamp = Date.now();
const world = {
  board: `board.${stamp}@example.org`,
  boardName: `Chair ${stamp}`,
  reporter: `reporter.${stamp}@example.org`,
  title: `E2E public report ${stamp}`,
  details: `Spreadsheet left on a shared drive ${stamp}`,
  incident: "",
  reference: "",
  url: "",
  report: "",
  ticket: "",
  office: "",
  holder: "",
  answerBy: "",
};

const PDF = Buffer.from("%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n");
const EML = Buffer.from("From: dpo@cmp.local\r\nTo: board@dpb.example\r\nSubject: Filing\r\n\r\nAttached.\r\n");

function minutesAgo(minutes: number): string {
  const at = new Date(Date.now() - minutes * 60_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** A date `days` from today, as a date input takes it. */
function daysAhead(days: number): string {
  const at = new Date(Date.now() + days * 86_400_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
}

/** A `YYYY-MM-DD` date as the server writes it on the thread. */
function spelled(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  const month = new Date(Date.UTC(y, m - 1, d)).toLocaleString("en-GB", { month: "long", timeZone: "UTC" });
  return `${d} ${month} ${y}`;
}

/** The breach page's sections are tabs; a tab's name carries its count. */
function openTab(page: Page, name: string) {
  return page.getByRole("tab", { name: new RegExp(`^${name}`) }).click();
}

async function signedIn(browser: Browser, role: string, run: (page: Page) => Promise<void>): Promise<void> {
  const context = await browser.newContext({ storageState: statePath(role) });
  try {
    await run(await context.newPage());
  } finally {
    await context.close();
  }
}

/** Wait for messages to arrive; the worker sends after the commit. */
async function arrivals(
  mark: number,
  wanted: (entries: OutboxEntry[]) => boolean,
  timeout = 60_000,
): Promise<OutboxEntry[]> {
  await expect.poll(() => wanted(entriesSince(mark)), { timeout, intervals: [500] }).toBe(true);
  return entriesSince(mark);
}

const about = (entries: OutboxEntry[], text: string) =>
  entries.filter((e) => e.subject.includes(text) || e.body.includes(text));

const RETIRED = /\btouch(ed|es|ing)?\b|\bderiv(e|ed|es|ing|ation)\b|\brevision|\btables?\b/i;

/** The screen as it stands, at both widths, with a note of what is wrong with it. */
async function snap(page: Page, name: string, { long = false } = {}): Promise<void> {
  if (!SHOTS) return;
  fs.mkdirSync(SHOTS, { recursive: true });
  const size = page.viewportSize() ?? { width: 1280, height: 720 };
  const dialog = (await page.getByRole("dialog").count()) > 0;
  const whole = !dialog && !long;
  const note = (line: string) => fs.appendFileSync(path.join(SHOTS, "notes.log"), `${name}: ${line}\n`);
  // A dialog takes a moment to fade in.
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SHOTS, `${name}-desktop.png`), fullPage: whole });
  const lines = await page.evaluate(() => document.body.innerText.split("\n"));
  for (const line of lines) if (RETIRED.test(line)) note(`word: ${line.trim()}`);
  // Tall enough that a dialog's foot is in the picture.
  await page.setViewportSize({ width: 390, height: dialog ? 1400 : 844 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(SHOTS, `${name}-phone.png`), fullPage: whole });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  if (overflow > 0) note(`scrolls sideways by ${overflow}px at 390`);
  await page.setViewportSize(size);
}

/** Everything the API needs to answer the staff member whose session this is. */
async function apiAs(role: string) {
  const state = JSON.parse(fs.readFileSync(statePath(role), "utf8")) as {
    cookies: Array<{ name: string; value: string }>;
  };
  const csrf = state.cookies.find((c) => c.name === "cmp_csrf")?.value ?? "";
  return request.newContext({
    baseURL: API,
    storageState: statePath(role),
    extraHTTPHeaders: { "X-CSRF-Token": csrf },
  });
}

/** The two public calls, as the portal makes them. */
async function report(email: string, title: string, details: string): Promise<string> {
  const api = await request.newContext({ baseURL: API });
  try {
    const asked = await api.post("/incident-reports/code", { data: { email } });
    expect(asked.status()).toBe(200);
    const code = await freshCode(email, null);
    const sent = await api.post("/incident-reports", {
      data: {
        name: "A Reporter",
        email,
        code,
        title,
        incident_details: details,
        origin: "The sales team's drive",
        cyber_attack: "unknown",
      },
    });
    expect(sent.status()).toBe(201);
    return ((await sent.json()) as { reference: string }).reference;
  } finally {
    await api.dispose();
  }
}

/** Open a report's editor by starting it, and write what the register could not. */
async function draft(page: Page, kind: string, fill: Array<[RegExp, string]>) {
  const row = page.getByTestId(`report-${kind}`);
  await row.getByRole("button", { name: "Draft it" }).click();
  const dialog = page.getByRole("dialog");
  for (const [label, text] of fill) await dialog.getByLabel(label).fill(text);
  return { row, dialog };
}

/** Finalise, which mails the board and nobody else, and prove both. */
async function finalise(page: Page, kind: string, title: string): Promise<void> {
  const row = page.getByTestId(`report-${kind}`);
  const dialog = page.getByRole("dialog");
  const mark = outboxMark();
  await dialog.getByRole("button", { name: "Finalise and tell the board" }).click();
  await expect(page.getByText("Nothing has gone to the regulator.")).toBeVisible();
  await expect(row.getByText(/^Finalised( · version \d+)?$/)).toBeVisible();
  // An earlier version keeps its own line, folded away.
  await expect(row.getByText(/Organisation's board: 1 delivered/).filter({ visible: true })).toBeVisible({ timeout: 30_000 });
  const mails = await arrivals(mark, (e) => about(e, `${title} finalised`).length > 0);
  const told = about(mails, `${title} finalised`);
  expect(told.map((m) => m.to)).toEqual([world.board]);
  expect(told[0].attached.join()).toMatch(/\.pdf \(application\/pdf, \d+ bytes\)/);
}

/** A person sent it; keep what proves it. */
async function recordSent(page: Page, kind: string, reference: string | null): Promise<void> {
  await page.getByTestId(`report-${kind}`).getByRole("button", { name: "Record as sent" }).click();
  const dialog = page.getByRole("dialog");
  const save = dialog.getByRole("button", { name: "Record as sent" });
  await expect(save).toBeDisabled();
  await dialog.getByLabel(/^Proof of internal approval/).setInputFiles({
    name: "approval.pdf",
    mimeType: "application/pdf",
    buffer: PDF,
  });
  // Not before it was finalised, a moment ago: the box takes whole minutes.
  await dialog.getByLabel(/^Sent at/).fill(minutesAgo(-1));
  if (reference) {
    await dialog.getByLabel(/^Reference returned/).fill(reference);
    await expect(save, "the mail sent is still missing").toBeDisabled();
  }
  await dialog.getByLabel(/^The mail sent to the regulator/).setInputFiles({
    name: "sent.eml",
    mimeType: "message/rfc822",
    buffer: EML,
  });
  await save.click();
  await expect(page.getByText("Recorded as sent")).toBeVisible();
  await expect(page.getByTestId(`report-${kind}`).getByText(/^Sent( · version \d+)?$/)).toBeVisible();
}

/** The settings as the run found them. Addresses come back sealed, so what was
 *  added is told from what was there by its uuid, not by its address. */
const found = { recipients: [] as string[], roles: [] as string[] };

interface Settings {
  intake_roles: string[];
  board_recipients: Array<{ recipient_uuid: string }>;
}

test.beforeAll(async () => {
  const api = await apiAs("admin");
  try {
    const settings = (await (await api.get("/breach-settings")).json()) as Settings;
    found.recipients = settings.board_recipients.map((r) => r.recipient_uuid);
    found.roles = settings.intake_roles;
  } finally {
    await api.dispose();
  }
});

test.afterAll(async () => {
  // Whatever became of the run, the settings are left as they were found.
  const api = await apiAs("admin");
  try {
    const now = (await (await api.get("/breach-settings")).json()) as Settings;
    for (const { recipient_uuid: uuid } of now.board_recipients) {
      if (!found.recipients.includes(uuid)) {
        expect((await api.delete(`/breach-settings/board-recipients/${uuid}`)).status()).toBe(200);
      }
    }
    expect((await api.put("/breach-settings/intake-roles", { data: { roles: found.roles } })).status()).toBe(200);
  } finally {
    await api.dispose();
  }
});

test.describe("breach settings", () => {
  test.use({ storageState: statePath("admin") });

  test("the administrator lists a board address and names one more role to be told", async ({ page }) => {
    await page.goto("/breach-settings");
    await expect(page.getByRole("heading", { name: "Breach settings", level: 1 })).toBeVisible();
    await expect(page.locator("code", { hasText: /\/report-incident$/ })).toBeVisible();

    await page.getByLabel(/^Name/).fill(world.boardName);
    await page.getByLabel(/^Mail ID/).fill(world.board);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(page.getByRole("cell", { name: world.board, exact: true })).toBeVisible();

    // The two officers are always told; anybody else is the office's choice.
    await expect(page.getByRole("checkbox", { name: "Data Protection Officer" })).toBeChecked();
    await expect(page.getByRole("checkbox", { name: "Data Protection Officer" })).toBeDisabled();
    await expect(page.getByRole("checkbox", { name: "Legal PoC" })).toBeDisabled();
    const hr = page.getByRole("checkbox", { name: "HR PoC" });
    await expect(hr).not.toBeChecked();
    // Not `check()`: the box shows the server's answer, a moment after the click.
    await hr.click();
    await expect(hr).toBeChecked();

    await page.reload();
    await expect(page.getByRole("cell", { name: world.board, exact: true })).toBeVisible();
    await expect(page.getByRole("checkbox", { name: "HR PoC" })).toBeChecked();
    await snap(page, "01-breach-settings");
  });

  test("the DPO and Legal may keep it too, and a collection owner may not", async ({ browser }) => {
    for (const role of ["dpo", "legal"]) {
      await signedIn(browser, role, async (page) => {
        await page.goto("/breach-settings");
        await expect(page.getByRole("cell", { name: world.board, exact: true })).toBeVisible();
        await expect(page.getByRole("button", { name: "Add", exact: true })).toBeVisible();
      });
    }
    await signedIn(browser, "dco", async (page) => {
      await page.goto("/breach-settings");
      await expect(page.getByText("Not part of your account")).toBeVisible();
    });
  });
});

test.describe("the public link", () => {
  test("a report waits in the shared intake, and everyone named is told that it came", async ({ browser }) => {
    test.setTimeout(120_000);
    const mark = outboxMark();
    world.incident = await report(world.reporter, world.title, world.details);
    expect(world.incident).toMatch(/^INC-\d{4}-\d+$/);

    const mails = await arrivals(mark, (e) => {
      const to = new Set(about(e, world.incident).map((m) => m.to));
      return [DPO, LEGAL, HR_POC, world.reporter].every((a) => to.has(a));
    });
    const sent = about(mails, world.incident);
    // Told that it came, and nothing of what it says.
    for (const mail of sent) {
      expect(`${mail.subject}\n${mail.body}`).not.toContain(world.details);
      expect(`${mail.subject}\n${mail.body}`).not.toContain(world.title);
    }
    // A collection owner's role was not named.
    expect(sent.map((m) => m.to)).not.toContain("dco@cmp.local");

    for (const role of ["dpo", "legal"]) {
      await signedIn(browser, role, async (page) => {
        await page.goto("/breaches");
        const intake = page.getByTestId("incident-intake");
        await expect(intake.getByText(world.title)).toBeVisible();
        await expect(intake.getByText(world.incident)).toBeVisible();
        if (role === "dpo") await snap(page, "02-intake", { long: true });
        await expect(page.getByRole("link", { name: "Breach settings" })).toBeAttached();
      });
    }
  });

  test("only the two officers can reach the intake", async () => {
    for (const role of ["admin", "dco"]) {
      const api = await apiAs(role);
      expect([403, 404], role).toContain((await api.get("/breaches/intake")).status());
      await api.dispose();
    }
    const api = await apiAs("dpo");
    const waiting = (await (await api.get("/breaches/intake?limit=200")).json()) as {
      items: Array<{ report_uuid: string; reference: string }>;
    };
    world.report = waiting.items.find((r) => r.reference === world.incident)?.report_uuid ?? "";
    expect(world.report).not.toBe("");
    await api.dispose();
  });

  test("the DPO reads it and claims it, and the other office no longer sees it", async ({ browser }) => {
    await signedIn(browser, "dpo", async (page) => {
      await page.goto("/breaches");
      const row = page.getByTestId("incident-intake").getByRole("listitem").filter({ hasText: world.title });
      await row.getByRole("button", { name: "Read it" }).click();
      const dialog = page.getByRole("dialog");
      await expect(dialog.getByText(`Reported incident ${world.incident}`)).toBeVisible();
      await expect(dialog.getByText(world.details)).toBeVisible();
      await expect(dialog.getByText(world.reporter)).toBeVisible();
      await expect(dialog.getByText("No clock has started", { exact: false })).toBeVisible();
      await snap(page, "03-read-report");
      await dialog.getByRole("button", { name: "Claim for my office" }).click();

      await page.waitForURL(/\/breaches\/[0-9a-f-]{36}/);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(world.incident);
      await expect(page.getByText("Incident, being validated", { exact: true })).toBeVisible();
      world.url = page.url().split("#")[0];
      await expect(page.getByText(world.reporter).filter({ visible: true })).toBeVisible();
      // Claimed, and still nothing runs.
      await expect(page.getByText(/^No duty yet\./)).toBeVisible();
      await expect(page.getByRole("button", { name: "Notify Organization Board" })).toHaveCount(0);
      await snap(page, "04-claimed-incident");
    });

    await signedIn(browser, "legal", async (page) => {
      await page.goto("/breaches");
      await expect(page.getByRole("heading", { name: "Incidents and personal data breaches", level: 1 })).toBeVisible();
      await expect(page.getByText(world.title)).toHaveCount(0);
      await page.goto(world.url);
      await expect(page.getByRole("heading", { level: 1, name: world.incident })).toHaveCount(0);
      await expect(page.getByText("Could not load this incident")).toBeVisible();
    });

    // It is one office's now: the other can neither claim it nor dismiss it.
    const legal = await apiAs("legal");
    const claim = await legal.post(`/breaches/intake/${world.report}/claim`);
    expect([404, 409]).toContain(claim.status());
    const dismiss = await legal.post(`/breaches/intake/${world.report}/dismiss`, { data: { reason: "Mine" } });
    expect([404, 409]).toContain(dismiss.status());
    await legal.dispose();
  });

  test("a report that is nothing is dismissed with a reason, and never reaches the register", async ({ browser }) => {
    const title = `E2E junk report ${stamp}`;
    const reference = await report(`junk.${stamp}@example.org`, title, "Somebody sent a joke");
    await signedIn(browser, "dpo", async (page) => {
      await page.goto("/breaches");
      const row = page.getByTestId("incident-intake").getByRole("listitem").filter({ hasText: title });
      await row.getByRole("button", { name: "Read it" }).click();
      const dialog = page.getByRole("dialog");
      await dialog.getByRole("button", { name: "Dismiss", exact: true }).click();
      const dismiss = dialog.getByRole("button", { name: "Dismiss the report" });
      await expect(dismiss).toBeDisabled();
      await dialog.getByLabel(/^Why is it being dismissed/).fill("A joke, not an incident");
      await dismiss.click();
      await expect(page.getByText("Report dismissed")).toBeVisible();
      await expect(page.getByText(title)).toHaveCount(0);
      await page.goto(`/breaches?status=all&q=${reference}`);
      await expect(page.getByRole("link", { name: reference })).toHaveCount(0);
    });
  });
});

test.describe("the DPO's office", () => {
  test.use({ storageState: statePath("dpo") });

  test("a validation of yes starts the organisation's board's thirty minutes", async ({ page }) => {
    await page.goto(world.url);
    await openTab(page, "Validation");
    // First noticed is when the report arrived, seconds ago, and awareness
    // cannot come before it: the box takes whole minutes, so the next one.
    await page.getByLabel(/^Became aware at/).fill(minutesAgo(-1));
    await page.getByLabel(/^Reasoning/).fill("Names and mail IDs were on the drive");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-\d{4}-\d{4}$/);
    world.reference = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").trim();

    await openTab(page, "Duties");
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await expect(orgBoard.getByText("Outstanding")).toBeVisible();
    await expect(orgBoard.getByText(/^(29|30) min left$/)).toBeVisible();
    await snap(page, "05-duties-after-yes");
  });

  test("Notify Organization Board drafts a report, and sending it mails the list and does the duty", async ({
    page,
  }) => {
    await page.goto(world.url);
    await page.getByRole("button", { name: "Notify Organization Board" }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: /^Report to the organisation's board · version 1$/ })).toBeVisible();
    // Started from what the incident holds.
    const what = dialog.getByLabel(/^What happened/);
    await expect(what).toHaveValue(world.details);
    await dialog.getByLabel(/^What happens next/).fill(`Containment under way ${stamp}`);
    await what.fill(`${world.details}, confirmed by the office`);
    await snap(page, "06-notify-board-popup");

    const mark = outboxMark();
    await dialog.getByRole("button", { name: "Send to the board" }).click();
    await expect(page.getByText("Sent to the organisation's board")).toBeVisible();

    const mails = await arrivals(mark, (e) => about(e, world.reference).some((m) => m.to === world.board));
    const mail = about(mails, world.reference).find((m) => m.to === world.board);
    expect(mail?.subject).toContain("Report to the organisation's board");
    expect(mail?.body).toContain(`${world.details}, confirmed by the office`);
    expect(mail?.body).toContain(`Containment under way ${stamp}`);
    expect(mail?.attached.join()).toMatch(/\.pdf \(application\/pdf, \d+ bytes\)/);
    expect(new Set(about(mails, world.reference).map((m) => m.to))).toEqual(new Set([world.board]));

    await page.reload();
    await openTab(page, "Duties");
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await expect(orgBoard.getByText("Done")).toBeVisible();
    await expect(orgBoard.getByText(new RegExp(`By email: ${world.boardName}`))).toBeVisible();
    await expect(page.getByRole("button", { name: "Notify Organization Board" })).toHaveCount(0);
  });

  test("the initial intimation: finalising mails the board and nobody else, and filing does the duty", async ({
    page,
  }) => {
    await page.goto(`${world.url}#duties`);
    await page.getByRole("row", { name: /Board - initial intimation/ }).getByRole("link", { name: "Open the report" }).click();
    await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
    await snap(page, "07-reports-tab");

    const { dialog } = await draft(page, "board_intimation", []);
    await expect(dialog.getByRole("button", { name: "Finalise and tell the board" })).toBeDisabled();
    await expect(dialog.getByText(/^Still to write: Its likely impact\.$/)).toBeVisible();
    await dialog.getByLabel(/^Its likely impact/).fill("Contact details may have been read by other staff.");
    await snap(page, "08-intimation-editor");
    await finalise(page, "board_intimation", "Initial intimation to the DPDP Board");

    // Still outstanding: finalising is not sending.
    await openTab(page, "Duties");
    const duty = page.getByRole("row", { name: /Board - initial intimation/ });
    await expect(duty.getByText("Outstanding")).toBeVisible();

    await openTab(page, "Reports");
    await page.getByTestId("report-board_intimation").getByRole("button", { name: "Record as sent" }).click();
    await snap(page, "09-record-as-sent");
    await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
    await recordSent(page, "board_intimation", `DPB-${stamp}`);

    await openTab(page, "Duties");
    await expect(duty.getByText("Done")).toBeVisible();
    await expect(duty.getByText(`DPB-${stamp}`)).toBeVisible();
  });

  test("the CERT-In report goes the same way, on its own mark", async ({ page }) => {
    await page.goto(`${world.url}#reports`);
    // Not until it is marked.
    await expect(page.getByTestId("report-cert_in").getByRole("button", { name: "Draft it" })).toBeDisabled();
    await openTab(page, "Duties");
    await page.getByRole("button", { name: "Mark reportable to CERT-In" }).click();
    await expect(page.getByRole("row", { name: /Report to CERT-In/ })).toBeVisible();

    await openTab(page, "Reports");
    await draft(page, "cert_in", [
      [/^Systems affected/, "The shared drive"],
      [/^Action taken so far/, "Access removed; the file taken down."],
    ]);
    await finalise(page, "cert_in", "Report to CERT-In");
    await recordSent(page, "cert_in", `CERT-${stamp}`);

    await openTab(page, "Duties");
    const duty = page.getByRole("row", { name: /Report to CERT-In/ });
    await expect(duty.getByText("Done")).toBeVisible();
    await expect(duty.getByText(`CERT-${stamp}`)).toBeVisible();
  });

  test("the 72-hour report goes the same way", async ({ page }) => {
    await page.goto(`${world.url}#reports`);
    await draft(page, "board_report", [
      [/^\(ii\) The events/, "A folder was shared wider than it should have been."],
      [/^\(iii\) Measures/, "Access removed and the share reviewed."],
      [/^\(iv\) Findings/, "No malice found."],
      [/^\(v\) Remedial/, "Quarterly review of shared folders."],
    ]);
    await finalise(page, "board_report", "72-hour report to the DPDP Board");
    await recordSent(page, "board_report", `DPB-72-${stamp}`);

    await openTab(page, "Duties");
    const duty = page.getByRole("row", { name: /Board - detailed report/ });
    await expect(duty.getByText("Done")).toBeVisible();
    await expect(duty.getByText(`DPB-72-${stamp}`)).toBeVisible();
    await openTab(page, "Reports");
    await snap(page, "10-reports-filed");
  });

  test("a report's PDF comes down, and a correction is a new version that mails the board again", async ({ page }) => {
    await page.goto(`${world.url}#reports`);
    const row = page.getByTestId("report-board_intimation");
    const [pdf] = await Promise.all([page.waitForEvent("download"), row.getByRole("button", { name: "PDF" }).click()]);
    expect(pdf.suggestedFilename()).toMatch(/\.pdf$/);
    const bytes = fs.readFileSync(await pdf.path());
    expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");

    await row.getByRole("button", { name: "New version" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: /· version 2$/ })).toBeVisible();
    // It starts from the last version's words.
    await expect(dialog.getByLabel(/^Its likely impact/)).toHaveValue("Contact details may have been read by other staff.");
    await finalise(page, "board_intimation", "Initial intimation to the DPDP Board");
    await expect(row.getByText("Finalised · version 2")).toBeVisible();

    // Nothing but filing it with both proofs records it as sent.
    const api = await apiAs("dpo");
    const uuid = world.url.split("/breaches/")[1];
    const reports = (await (await api.get(`/breaches/${uuid}/reports`)).json()) as {
      kinds: Array<{ kind: string; versions: Array<{ report_uuid: string }> }>;
    };
    const latest = reports.kinds.find((k) => k.kind === "board_intimation")?.versions[0].report_uuid;
    const refused = await api.post(`/breaches/${uuid}/reports/${latest}/file`, {
      data: { filed_at: new Date().toISOString(), reference: "NO-PROOF" },
    });
    expect(refused.status()).toBe(409);
    expect(((await refused.json()) as { error: { code: string } }).error.code).toBe("report_proof_missing");
    // The old by-hand route is gone.
    const byHand = await api.post(`/breaches/${uuid}/obligations/board_intimation/complete`, {
      data: { occurred_at: new Date().toISOString(), reference: "BY-HAND" },
    });
    expect([404, 405]).toContain(byHand.status());
    await api.dispose();

    await recordSent(page, "board_intimation", `DPB-2-${stamp}`);
    await expect(row.getByText("Earlier versions (1)")).toBeVisible();
    await expect(row.getByText("Sent · version 2")).toBeVisible();
  });

  test("people are found by project, in the words of the work, and reviewed before they are added", async ({
    page,
  }) => {
    await page.goto(`${world.url}#affected`);
    await expect(page.getByRole("heading", { name: "Affected people", exact: true })).toBeVisible();
    await expect(page.locator("#affected")).not.toContainText(RETIRED);
    await page.getByRole("button", { name: "Add people" }).click();
    const dialog = page.getByRole("dialog");
    for (const way of [
      /^From a project or activity/,
      /^From a vendor/,
      /^From a data source/,
      /^Upload an Excel list/,
      /^Add one person/,
    ]) {
      await expect(dialog.getByRole("button", { name: way })).toBeVisible();
    }
    await expect(dialog).not.toContainText(RETIRED);
    await snap(page, "11-add-people");

    await dialog.getByRole("button", { name: /^From a project or activity/ }).click();
    const project = dialog.getByLabel(/^Project or activity/);
    await expect(project.locator("option").nth(1)).toBeAttached();
    // The smallest, to reach as few of the dev database's people as it can.
    const options = (await project.locator("option").allTextContents()).slice(1);
    const size = (o: string) => Number(/ (\d+) (?:person|people)$/.exec(o)?.[1] ?? Infinity);
    const smallest = options.reduce((a, b) => (size(b) < size(a) ? b : a));
    await project.selectOption({ label: smallest });
    await snap(page, "12-add-from-project");
    await dialog.getByRole("button", { name: "Find the people" }).click();

    await expect(dialog.getByText(/^\d+ (person|people) found$/)).toBeVisible();
    const ticks = dialog.getByRole("checkbox");
    const total = await ticks.count();
    expect(total).toBeGreaterThan(0);
    for (let i = 1; i < total; i += 1) await ticks.nth(i).uncheck();
    await snap(page, "13-add-review");
    await dialog.getByRole("button", { name: "Add 1 person" }).click();
    await expect(page.getByText("1 person added to the list")).toBeVisible();
    await expect(page.locator("#affected").getByRole("cell", { name: "In a project or activity" })).toBeVisible();
    await expect(page.locator("#affected").getByText("How the list was built")).toBeVisible();

    // A vendor and a data source are looked in the same way. Looked, not added.
    await page.getByRole("button", { name: "Add people" }).click();
    for (const [way, label] of [
      [/^From a vendor/, /^Vendor/],
      [/^From a data source/, /^Data source/],
    ] as const) {
      await dialog.getByRole("button", { name: way }).click();
      const choice = dialog.getByLabel(label);
      await expect(choice.locator("option").nth(1)).toBeAttached();
      await choice.selectOption({ index: 1 });
      await dialog.getByRole("button", { name: "Find the people" }).click();
      await expect(dialog.getByText(/^\d+ (person|people) found$/)).toBeVisible();
      await dialog.getByRole("button", { name: "Back" }).click();
      await dialog.getByRole("button", { name: "Back" }).click();
    }
    await page.keyboard.press("Escape");
  });

  test("an Excel list is checked, added, and everyone listed is reached by one button", async ({ page }) => {
    test.setTimeout(120_000);
    const one = `asha.${stamp}@example.org`;
    const two = `ben.${stamp}@example.org`;
    const mobile = `+9190${String(stamp).slice(-8)}`;
    await page.goto(`${world.url}#affected`);
    await page.getByRole("button", { name: "Add people" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: /^Upload an Excel list/ }).click();
    const [template] = await Promise.all([
      page.waitForEvent("download"),
      dialog.getByRole("button", { name: "Download the template" }).click(),
    ]);
    expect(template.suggestedFilename()).toMatch(/\.xlsx$/);
    expect(fs.readFileSync(await template.path()).subarray(0, 2).toString()).toBe("PK");
    await dialog.getByLabel("The filled-in list").setInputFiles({
      name: "affected.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: workbook([
        ["Name", "Mail ID", "Mobile number"],
        [`Asha ${stamp}`, one, mobile],
        [`Ben ${stamp}`, two, ""],
        ["Nobody to reach", "", ""],
      ]),
    });
    await dialog.getByRole("button", { name: "Check the file" }).click();
    await expect(dialog.getByRole("definition").first()).toHaveText("3");
    await expect(dialog.getByText("Rows that could not be read (1)")).toBeVisible();
    await snap(page, "14-excel-checked");
    await dialog.getByRole("button", { name: "Add 2 to the list" }).click();
    await expect(page.getByText("2 people added to the list")).toBeVisible();
    await expect(page.locator("#affected").getByText("3 people")).toBeVisible();
    await expect(page.locator("#affected").getByText(one)).toBeVisible();
    await snap(page, "15-affected-listed");

    await page.getByRole("button", { name: "Draft the notice" }).click();
    const words: Array<[RegExp, string]> = [
      [/^What happened/, `A folder was shared wider than it should have been ${stamp}.`],
      [/^The consequences likely/, "Someone may have seen your name and mail ID."],
      [/^What has been done/, "Access was removed the same day."],
      [/^What she can do/, "Be wary of messages that mention the study."],
      [/^Who to contact/, "The Privacy Office, privacy@cmp.local"],
    ];
    for (const [label, text] of words) await page.getByLabel(label).fill(text);
    await page.getByRole("button", { name: "Save draft" }).click();
    await expect(page.getByText("Draft saved")).toBeVisible();
    await page.getByRole("button", { name: "Approve", exact: true }).click();
    await expect(page.getByText("Notice approved")).toBeVisible();

    const send = page.getByRole("button", { name: "Send to all 3 affected people" });
    await expect(send).toHaveCount(1);
    await snap(page, "16-notice-approved");
    await send.click();
    await snap(page, "17-send-confirm");
    const mark = outboxMark();
    await page.getByRole("dialog").getByRole("button", { name: "Send to all 3 affected people" }).click();
    await expect(page.getByText("Version 1 sent")).toBeVisible();

    const mails = await arrivals(mark, (e) => {
      const got = about(e, `shared wider than it should have been ${stamp}`).map((m) => `${m.channel}:${m.to}`);
      return got.includes(`email:${one}`) && got.includes(`email:${two}`) && got.some((g) => g.startsWith("sms:"));
    });
    const reached = about(mails, `shared wider than it should have been ${stamp}`);
    expect(reached.filter((m) => m.to === one)).toHaveLength(1);

    await expect(page.getByText(/^3 of 3 listed people have been notified on every channel\./)).toBeVisible({
      timeout: 60_000,
    });
    await snap(page, "18-notice-sent");
    await page.reload();
    await openTab(page, "Duties");
    await expect(page.getByRole("row", { name: /Principals notified/ }).getByText("Done")).toBeVisible();
  });

  test("a ticket is raised with a document, and the mail about it names no breach", async ({ page }) => {
    world.answerBy = daysAhead(10);
    await page.goto(`${world.url}#tickets`);
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^Find them/).fill("dco@cmp.local");
    const who = dialog.getByLabel(/^Who/);
    await expect(who.locator("option", { hasText: "dco@cmp.local" })).toHaveCount(1);
    await who.selectOption({ label: (await who.locator("option", { hasText: "dco@cmp.local" }).textContent()) ?? "" });
    await dialog.getByLabel(/^What you are asking them to do/).fill("Keep the drive's access log");
    await dialog.getByLabel(/^Resolve by/).fill(world.answerBy);
    await dialog.getByLabel(/^Attach a document/).setInputFiles({
      name: "drive-scope.pdf",
      mimeType: "application/pdf",
      buffer: PDF,
    });
    await snap(page, "19-assign-ticket");
    const mark = outboxMark();
    await dialog.getByRole("button", { name: "Assign", exact: true }).click();
    await expect(page.getByText("Ticket assigned", { exact: true })).toBeVisible();

    const mails = await arrivals(mark, (e) => e.some((m) => m.to === "dco@cmp.local"));
    for (const mail of mails.filter((m) => m.to === "dco@cmp.local")) {
      expect(`${mail.subject}\n${mail.body}`).not.toContain(world.reference);
      expect(`${mail.subject}\n${mail.body}`).not.toContain(world.title);
    }

    const row = page.locator("#tickets").getByRole("row", { name: /Waiting on the holder/ });
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Open" }).click();
    const thread = page.getByRole("dialog").getByRole("list", { name: "Messages" });
    await expect(thread.getByText("Document attached when this ticket was raised.")).toBeVisible();
    await expect(thread.getByText(/File: drive-scope\.pdf/)).toBeVisible();
    const link = await thread.getByRole("link", { name: "download" }).getAttribute("href");
    const file = await page.request.get(link ?? "");
    expect(file.status()).toBe(200);
    expect(Buffer.from(await file.body()).subarray(0, 5).toString()).toBe("%PDF-");
  });

  test("the office moves the date, saying why, and the thread keeps it", async ({ page }) => {
    world.office = daysAhead(14);
    await page.goto(`${world.url}#tickets`);
    await page.locator("#tickets").getByRole("button", { name: "Open" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Change the date" }).click();
    const save = dialog.getByRole("button", { name: "Change the date" });
    await dialog.getByLabel(/^New date/).fill(world.office);
    await expect(save, "a reason is required").toBeDisabled();
    await dialog.getByLabel(/^Why is it changing/).fill(`Waiting on IT ${stamp}`);
    await snap(page, "20-office-change-date");
    const mark = outboxMark();
    await save.click();
    await expect(page.getByText("Date changed")).toBeVisible();
    const line = `Resolve by changed from ${spelled(world.answerBy)} to ${spelled(world.office)}: Waiting on IT ${stamp}`;
    await expect(dialog.getByRole("list", { name: "Messages" }).getByText(line)).toBeVisible();

    const mails = await arrivals(mark, (e) => e.some((m) => m.to === "dco@cmp.local"));
    const told = mails.find((m) => m.to === "dco@cmp.local");
    expect(`${told?.subject}\n${told?.body}`).not.toContain(world.reference);
    expect(`${told?.subject}\n${told?.body}`).not.toContain(`Waiting on IT ${stamp}`);
  });
});

test.describe("the holder", () => {
  test.use({ storageState: statePath("dco") });

  test("reads the document, moves the date with a reason, and the office is told", async ({ page }) => {
    world.holder = daysAhead(20);
    await page.goto("/tickets");
    const card = page.getByTestId("breach-ticket").filter({ hasText: world.reference });
    await expect(card).toBeVisible();
    await expect(page.getByText(world.title)).toHaveCount(0);
    await card.getByRole("button", { name: "Respond" }).click();
    const dialog = page.getByRole("dialog");
    const thread = dialog.getByRole("list", { name: "Messages" });
    await expect(thread.getByText(/File: drive-scope\.pdf/)).toBeVisible();
    await expect(thread.getByText(`Waiting on IT ${stamp}`, { exact: false })).toBeVisible();
    const link = await thread.getByRole("link", { name: "download" }).getAttribute("href");
    const file = await page.request.get(link ?? "");
    expect(file.status()).toBe(200);

    await dialog.getByRole("button", { name: "Change the date" }).click();
    const save = dialog.getByRole("button", { name: "Change the date" });
    await dialog.getByLabel(/^New date/).fill(world.holder);
    await expect(save, "a reason is required").toBeDisabled();
    await dialog.getByLabel(/^Why is it changing/).fill(`Log arrives Friday ${stamp}`);
    await snap(page, "21-holder-change-date");
    const mark = outboxMark();
    await save.click();
    await expect(page.getByText("Date changed")).toBeVisible();
    const line = `Resolve by changed from ${spelled(world.office)} to ${spelled(world.holder)}: Log arrives Friday ${stamp}`;
    await expect(thread.getByText(line)).toBeVisible();
    await snap(page, "22-holder-thread");

    const mails = await arrivals(mark, (e) => e.some((m) => m.to === DPO && /date/i.test(m.subject)));
    const told = mails.find((m) => m.to === DPO && /date/i.test(m.subject));
    expect(`${told?.subject}\n${told?.body}`).not.toContain(world.reference);
    expect(`${told?.subject}\n${told?.body}`).not.toContain(`Log arrives Friday ${stamp}`);
  });
});

test.describe("the trail and the close", () => {
  test.use({ storageState: statePath("dpo") });

  test("both moves are on the thread and on the audit trail, with the dates and never the words", async ({ page }) => {
    await page.goto(`${world.url}#tickets`);
    await page.locator("#tickets").getByRole("button", { name: "Open" }).click();
    const thread = page.getByRole("dialog").getByRole("list", { name: "Messages" });
    await expect(
      thread.getByText(`Resolve by changed from ${spelled(world.answerBy)} to ${spelled(world.office)}: Waiting on IT ${stamp}`),
    ).toBeVisible();
    await expect(
      thread.getByText(`Resolve by changed from ${spelled(world.office)} to ${spelled(world.holder)}: Log arrives Friday ${stamp}`),
    ).toBeVisible();
    await snap(page, "23-office-thread");

    const uuid = page.url().split("/breaches/")[1].split(/[#?]/)[0];
    const tickets = await page.request.get(`/api/breaches/${uuid}/tickets`);
    expect(tickets.status()).toBe(200);
    world.ticket = ((await tickets.json()) as Array<{ ticket_uuid: string }>)[0].ticket_uuid;

    await page.goto(`/audit?entity_type=breach_ticket&entity=${world.ticket}&label=Ticket`);
    const entries = page.getByRole("table", { name: "Audit entries, most recent first" });
    const moved = entries.getByRole("button", { name: /date changed/i });
    await expect(moved).toHaveCount(2);
    await expect(entries).not.toContainText(`Waiting on IT ${stamp}`);
    await expect(entries).not.toContainText(`Log arrives Friday ${stamp}`);
    await snap(page, "24-audit-trail");
    await moved.first().click();
    const detail = page.getByRole("dialog");
    await expect(detail).toContainText(world.office);
    await expect(detail).toContainText(world.holder);
    await expect(detail).not.toContainText(`Log arrives Friday ${stamp}`);
    await snap(page, "25-audit-entry");
  });

  test("the other office cannot reach any of it, by any route", async ({ page }) => {
    const uuid = world.url.split("/breaches/")[1];
    const dpo = await apiAs("dpo");
    const docs = (await (await dpo.get(`/breaches/${uuid}/reports`)).json()) as {
      kinds: Array<{ kind: string; versions: Array<{ report_uuid: string }> }>;
    };
    const report = docs.kinds[0].versions[0].report_uuid;
    const detail = (await (await dpo.get(`/breaches/${uuid}`)).json()) as {
      attachments: Array<{ attachment_uuid: string }>;
    };
    const thread = (await (await dpo.get(`/breaches/${uuid}/tickets/${world.ticket}`)).json()) as {
      messages: Array<{ message_uuid: string; evidence_hash: string | null }>;
    };
    const file = thread.messages.find((m) => m.evidence_hash)?.message_uuid;
    const notices = (await (await dpo.get(`/breaches/${uuid}/notices`)).json()) as {
      versions: Array<{ notice_uuid: string }>;
    };
    const options = (await (await dpo.get(`/breaches/${uuid}/affected/options`)).json()) as {
      projects: Array<{ project_uuid: string }>;
    };
    await dpo.dispose();

    const base = `/breaches/${uuid}`;
    const reads = [
      base,
      `${base}/assessments`,
      `${base}/transitions`,
      `${base}/affected`,
      `${base}/affected/options`,
      `${base}/affected/contacts`,
      `${base}/affected/upload/template?kind=contacts`,
      `${base}/notices`,
      `${base}/board/intimation`,
      `${base}/board/report`,
      `${base}/org-board/brief`,
      `${base}/reports`,
      `${base}/reports/${report}/pdf`,
      `${base}/tickets`,
      `${base}/tickets/${world.ticket}`,
      `${base}/tickets/${world.ticket}/messages/${file}/evidence`,
      `${base}/attachments/${detail.attachments[0].attachment_uuid}`,
    ];
    const writes: Array<[string, Record<string, unknown>]> = [
      [`${base}/determinations`, { outcome: "no", reasoning: "Not mine", became_aware_at: null }],
      [`${base}/cert-in`, {}],
      [`${base}/assessments`, {}],
      [`${base}/transition`, { to: "closed", reason: "Not mine" }],
      [
        `${base}/affected/preview`,
        { scopes: [{ kind: "project", project_uuid: options.projects[0].project_uuid, since: null, until: null }] },
      ],
      [`${base}/affected`, { scopes: [], exclude: [], add: [], note: null }],
      [
        `${base}/notices`,
        { what_happened: "x", consequences: "x", measures: "x", protective_steps: "x", contact: "x" },
      ],
      [`${base}/notices/${notices.versions[0].notice_uuid}/approve`, {}],
      [`${base}/notices/send`, {}],
      [`${base}/reports`, { kind: "closure" }],
      [`${base}/reports/${report}/finalise`, {}],
      [`${base}/reports/${report}/resend`, {}],
      [`${base}/reports/${report}/file`, { filed_at: new Date().toISOString(), reference: "X" }],
      [`${base}/tickets`, { instruction: "Mine now", user_uuid: uuid }],
      [`${base}/tickets/${world.ticket}/resolve-by`, { answer_by: daysAhead(30), reason: "Not mine" }],
      [`${base}/tickets/${world.ticket}/close`, {}],
      [`${base}/tickets/${world.ticket}/withdraw`, { reason: "Not mine" }],
    ];
    const legal = await apiAs("legal");
    const answers: string[] = [];
    for (const route of reads) answers.push(`${(await legal.get(route)).status()} GET ${route.replace(uuid, "…")}`);
    for (const [route, data] of writes) {
      answers.push(`${(await legal.post(route, { data })).status()} POST ${route.replace(uuid, "…")}`);
    }
    await legal.dispose();
    expect(answers.filter((a) => !a.startsWith("404"))).toEqual([]);

    // Nor does the holder's own route answer them.
    await page.goto(world.url);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(world.reference);
  });

  test("a closure report is optional: nothing waits for it, and it files with no reference", async ({ page }) => {
    await page.goto(`${world.url}#tickets`);
    const row = page.locator("#tickets").getByRole("row", { name: /Waiting on the holder/ });
    await row.getByRole("button", { name: "Open" }).click();
    const dialog = page.getByRole("dialog");
    // Nothing back from the holder yet: the office withdraws its ask.
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await dialog.getByLabel(/Why is it withdrawn/).fill("The log arrived by another route");
    await dialog.getByRole("button", { name: "Withdraw" }).click();
    await expect(page.getByText("Ticket withdrawn")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);

    // Every duty done and the ticket gone: it may close with no closure report.
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });

    await openTab(page, "Reports");
    await expect(page.getByTestId("report-closure").getByText(/optional/)).toBeVisible();
    await draft(page, "closure", [
      [/^Summary of the incident/, "A folder was shared too widely."],
      [/^Root cause/, "A permission inherited from its parent."],
      [/^Measures taken/, "Access removed."],
      [/^Measures to prevent recurrence/, "Quarterly review."],
      [/^Data Principals notified/, "All three listed."],
      [/^Conclusion/, "Concluded with no further harm."],
    ]);
    await finalise(page, "closure", "Closure report");
    await recordSent(page, "closure", null);
    await snap(page, "26-closure-sent");

    await close.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Breach closed")).toBeVisible();
    await expect(page.getByTestId("report-closure").getByRole("button", { name: "New version" })).toHaveCount(0);
  });

  test("the proofs are kept with the breach, named for what they are", async ({ page }) => {
    await page.goto(`${world.url}#attachments`);
    const files = page.locator("#attachments");
    await expect(files.getByText("approval.pdf").first()).toBeVisible();
    await expect(files.getByText("sent.eml").first()).toBeVisible();
    await expect(files.getByText("Internal approval").first()).toBeVisible();
    await expect(files.getByText("Mail to the regulator").first()).toBeVisible();
    await snap(page, "27-attachments");
    await openTab(page, "Validation");
    await snap(page, "28-validation");
    await openTab(page, "Assessment");
    await snap(page, "29-assessment");
    await openTab(page, "Activity");
    await snap(page, "30-activity");
    await openTab(page, "Tickets");
    await snap(page, "31-tickets-tab");
    await page.goto("/dashboard");
    await expect(page.getByRole("button", { name: "Log an incident" })).toBeVisible();
    await snap(page, "32-dashboard");
  });

  test("the trail keeps the reports and the settings, and no address", async ({ page }) => {
    await page.goto("/audit?event_group=incident_report");
    const entries = page.getByRole("table", { name: "Audit entries, most recent first" });
    await expect(entries.getByRole("button", { name: /Incident report received/i }).first()).toBeVisible();
    await expect(entries.getByRole("button", { name: /Incident report claimed/i }).first()).toBeVisible();
    await expect(entries.getByRole("button", { name: /Incident report dismissed/i }).first()).toBeVisible();
    await expect(entries).not.toContainText(world.reporter);
    await page.goto("/audit?event_group=breach_settings");
    const settings = page.getByRole("table", { name: "Audit entries, most recent first" });
    await expect(settings.getByRole("button", { name: /settings changed/i }).first()).toBeVisible();
    await expect(settings).not.toContainText(world.board);
    await snap(page, "36-audit-settings");
  });
});

test.describe("what a validation does to the board's duty", () => {
  test.use({ storageState: statePath("dpo") });

  async function logged(page: Page, title: string): Promise<void> {
    await page.goto("/breaches");
    await page.getByRole("button", { name: "Log an incident" }).click();
    await page.getByLabel(/^Title/).fill(title);
    await page.getByLabel(/^First noticed/).fill(minutesAgo(20));
    await page.getByRole("button", { name: "Log the incident" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^INC-/);
  }

  async function validate(page: Page, outcome: "yes" | "no"): Promise<void> {
    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption(outcome);
    if (outcome === "yes") await page.getByLabel(/^Became aware at/).fill(minutesAgo(10));
    await page.getByLabel(/^Reasoning/).fill(`Reasoned ${outcome}`);
    await page.getByRole("button", { name: "Record the validation" }).click();
  }

  test("a no on a new incident owes the board nothing, and it closes", async ({ page }) => {
    await logged(page, `E2E junk incident ${stamp}`);
    await validate(page, "no");
    await expect(page.getByText("Validation recorded")).toBeVisible();
    await openTab(page, "Duties");
    await expect(page.getByRole("row", { name: /Organisation's board/ })).toHaveCount(0);
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
  });

  test("a later no sets the board's duty aside, and a later yes gives it a fresh thirty minutes", async ({ page }) => {
    await logged(page, `E2E changed mind ${stamp}`);
    await validate(page, "yes");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-/);
    await openTab(page, "Duties");
    const orgBoard = page.getByRole("row", { name: /Organisation's board/ });
    await expect(orgBoard.getByText(/^(29|30) min left$/)).toBeVisible();

    await validate(page, "no");
    await expect(page.getByText("Validation recorded")).toBeVisible();
    await openTab(page, "Duties");
    await expect(orgBoard.getByText("Not applicable")).toBeVisible();
    await expect(page.getByRole("button", { name: "Notify Organization Board" })).toHaveCount(0);

    await validate(page, "yes");
    await openTab(page, "Duties");
    await expect(orgBoard.getByText("Outstanding")).toBeVisible();
    await expect(orgBoard.getByText(/^(29|30) min left$/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Notify Organization Board" }).first()).toBeVisible();
  });
});

test.describe("the Legal office's own breach", () => {
  test.use({ storageState: statePath("legal") });

  const own = { title: `E2E legal report ${stamp}`, incident: "", url: "" };

  test("claims a report, which the DPO's office then cannot see", async ({ browser, page }) => {
    own.incident = await report(`legal.reporter.${stamp}@example.org`, own.title, "A payslip went astray");
    await page.goto("/breaches");
    const row = page.getByTestId("incident-intake").getByRole("listitem").filter({ hasText: own.title });
    await row.getByRole("button", { name: "Read it" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Claim for my office" }).click();
    await page.waitForURL(/\/breaches\/[0-9a-f-]{36}/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(own.incident);
    own.url = page.url().split("#")[0];

    await signedIn(browser, "dpo", async (other) => {
      await other.goto(own.url);
      await expect(other.getByText("Could not load this incident")).toBeVisible();
      await other.goto(`/breaches?status=all&q=${own.incident}`);
      await expect(other.getByRole("heading", { name: "Incidents and personal data breaches", level: 1 })).toBeVisible();
      await expect(other.getByText(own.title)).toHaveCount(0);
    });
  });

  test("tells the board, and finds people in the office's own work only", async ({ page }) => {
    await page.goto(`${own.url}#validation`);
    await page.getByLabel(/^Became aware at/).fill(minutesAgo(-1));
    await page.getByLabel(/^Reasoning/).fill("Pay details went to the wrong person");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^BR-/);

    await page.getByRole("button", { name: "Notify Organization Board" }).first().click();
    const report = page.getByRole("dialog");
    await expect(report.getByLabel(/^What happened/)).toHaveValue("A payslip went astray");
    const mark = outboxMark();
    await report.getByRole("button", { name: "Send to the board" }).click();
    await expect(page.getByText("Sent to the organisation's board")).toBeVisible();
    await arrivals(mark, (e) => e.some((m) => m.to === world.board && m.subject.includes("Report to the organisation's board")));

    await openTab(page, "People & notices");
    await page.getByRole("button", { name: "Add people" }).click();
    const dialog = page.getByRole("dialog");
    // The Legal PoC has no data sources to choose from.
    await expect(dialog.getByRole("button", { name: /^From a data source/ })).toHaveCount(0);
    await snap(page, "33-legal-add-people");
    await dialog.getByRole("button", { name: /^From a vendor/ }).click();
    const vendor = dialog.getByLabel(/^Vendor/);
    await expect(vendor).toBeVisible();
    await expect(dialog.getByText(/could not|not part of|refused/i)).toHaveCount(0);
    await snap(page, "34-legal-add-from-vendor");
    await dialog.getByRole("button", { name: "Back" }).click();
    await dialog.getByRole("button", { name: /^From a project or activity/ }).click();
    await snap(page, "35-legal-add-from-activity");
  });

  test("can reach only its own office's project from the people search", async () => {
    const dpo = await apiAs("dpo");
    const uuid = world.url.split("/breaches/")[1];
    const theirs = (await (await dpo.get(`/breaches/${uuid}/affected/options`)).json()) as {
      projects: Array<{ project_uuid: string }>;
    };
    await dpo.dispose();
    expect(theirs.projects.length).toBeGreaterThan(0);

    const legal = await apiAs("legal");
    const mine = own.url.split("/breaches/")[1];
    const options = (await (await legal.get(`/breaches/${mine}/affected/options`)).json()) as {
      projects: Array<{ project_uuid: string }>;
    };
    const held = options.projects.map((p) => p.project_uuid);
    expect(held.filter((p) => theirs.projects.some((t) => t.project_uuid === p))).toEqual([]);
    const preview = await legal.post(`/breaches/${mine}/affected/preview`, {
      data: { scopes: [{ kind: "project", project_uuid: theirs.projects[0].project_uuid, since: null, until: null }] },
    });
    // Refused, or nobody: never the other office's people.
    if (preview.ok()) {
      const found = (await preview.json()) as { derived: number };
      expect(found.derived).toBe(0);
    } else {
      expect([404, 422]).toContain(preview.status());
    }
    await legal.dispose();
  });

  test("raises a ticket with somebody in its office, and closes on a no", async ({ page }) => {
    await page.goto(`${own.url}#tickets`);
    await page.getByRole("button", { name: "Assign a ticket" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^Find them/).fill(HR_POC);
    const who = dialog.getByLabel(/^Who/);
    await expect(who.locator("option", { hasText: HR_POC })).toHaveCount(1);
    await who.selectOption({ label: (await who.locator("option", { hasText: HR_POC }).textContent()) ?? "" });
    await dialog.getByLabel(/^What you are asking them to do/).fill("Confirm who received it");
    await dialog.getByRole("button", { name: "Assign", exact: true }).click();
    await expect(page.getByText("Ticket assigned", { exact: true })).toBeVisible();
    const row = page.locator("#tickets").getByRole("row", { name: /Waiting on the holder/ });
    await row.getByRole("button", { name: "Open" }).click();
    const opened = page.getByRole("dialog");
    await opened.getByRole("button", { name: "Withdraw" }).click();
    await opened.getByLabel(/Why is it withdrawn/).fill("Answered by phone");
    await opened.getByRole("button", { name: "Withdraw" }).click();
    await expect(page.getByText("Ticket withdrawn")).toBeVisible();
    await page.keyboard.press("Escape");

    await openTab(page, "Validation");
    await page.getByRole("combobox", { name: /^Validation/ }).selectOption("no");
    await page.getByLabel(/^Reasoning/).fill("It stayed inside the team");
    await page.getByRole("button", { name: "Record the validation" }).click();
    await expect(page.getByText("Validation recorded")).toBeVisible();
    const close = page.getByRole("button", { name: "Close the breach" });
    await expect(close).toBeEnabled({ timeout: 15_000 });
    await close.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Breach closed")).toBeVisible();
  });
});

/**
 * Last, because a failure here must not stop the journey above. Run against an
 * API started before `dashboard.py` last changed, this one fails and the rest
 * do not: the running process does not know the count.
 */
test.describe("both officers' dashboards", () => {
  test("count what waits, until somebody takes it up", async ({ browser }) => {
    const title = `E2E waiting report ${stamp}`;
    const reference = await report(`waiting.${stamp}@example.org`, title, "Waiting for an office");
    try {
      for (const role of ["dpo", "legal"]) {
        await signedIn(browser, role, async (page) => {
          await page.goto("/dashboard");
          await expect(page.getByRole("link", { name: /Reported incidents waiting for an office/ })).toBeVisible();
        });
      }
    } finally {
      const api = await apiAs("dpo");
      const waiting = (await (await api.get("/breaches/intake?limit=200")).json()) as {
        items: Array<{ report_uuid: string; reference: string }>;
      };
      const left = waiting.items.find((r) => r.reference === reference);
      if (left) await api.post(`/breaches/intake/${left.report_uuid}/dismiss`, { data: { reason: "End-to-end run" } });
      await api.dispose();
    }
  });
});
