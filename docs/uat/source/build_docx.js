const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType,
  WidthType, ShadingType, BorderStyle, PageBreak, TableOfContents, Footer, Header, PageNumber,
  LevelFormat, TabStopType,
} = require("docx");
const R = require("./runbook");

const HERE = __dirname;
const OUT = process.argv[2];
const AREAS = ["ACC", "REG", "PRJ", "CON", "RGT", "OVS"];
const cases = AREAS.flatMap((a) => {
  const f = path.join(HERE, `${a}.json`);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : [];
});

// ---------------------------------------------------------------- styling
const FONT = "Arial";
const INK = "1F2937", MUTED = "6B7280", ACCENT = "1F4E79", HEAD_FILL = "DCE6F1", SOFT = "F3F4F6", LINE = "BFBFBF";
const PAGE_W = 11906, MARGIN = 1134, CONTENT = PAGE_W - 2 * MARGIN; // A4, 2 cm margins
const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const pad = { top: 60, bottom: 60, left: 100, right: 100 };

const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 20, bold: o.bold, italics: o.italics, color: o.color || INK });
const p = (text, o = {}) =>
  new Paragraph({ spacing: { after: o.after ?? 120, before: o.before ?? 0 }, alignment: o.align, children: Array.isArray(text) ? text : [run(text, o)] });
const h1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] });
const h2 = (t, o = {}) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, pageBreakBefore: o.pageBreak, children: [new TextRun({ text: t, font: FONT })] });
const h3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (t) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: [run(t)] });
const numbered = (t, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: [run(t)] });

function cell(content, width, o = {}) {
  const paras = (Array.isArray(content) ? content : [content]).map((c) =>
    c instanceof Paragraph ? c : new Paragraph({ spacing: { after: 40 }, children: [run(String(c ?? ""), { bold: o.bold, size: o.size || 18, color: o.color })] }),
  );
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders,
    margins: pad,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: paras,
  });
}

function table(widths, header, rows, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const head = new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, widths[i], { bold: true, fill: HEAD_FILL })) });
  const body = rows.map((r, ri) => new TableRow({
    cantSplit: o.cantSplit,
    children: r.map((t, i) => cell(t, widths[i], { fill: o.zebra && ri % 2 ? SOFT : undefined, bold: o.boldFirst && i === 0 })),
  }));
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths, rows: [head, ...body] });
}

// Label/value table for a test case's facts.
function facts(pairs) {
  const w = [2100, CONTENT - 2100];
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: w,
    rows: pairs.map(([k, v]) => new TableRow({ children: [cell(k, w[0], { bold: true, fill: SOFT }), cell(v, w[1])] })),
  });
}

const listParas = (items) => (items && items.length ? items : ["None"]).map((t) => new Paragraph({ spacing: { after: 30 }, children: [run(`- ${t}`, { size: 18 })] }));

// ---------------------------------------------------------------- content
const children = [];

// Title page
children.push(
  new Paragraph({ spacing: { before: 2400, after: 200 }, children: [new TextRun({ text: "COMPASS CMP", font: FONT, size: 56, bold: true, color: ACCENT })] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "User Acceptance Testing", font: FONT, size: 40, color: INK })] }),
  new Paragraph({ spacing: { after: 600 }, children: [new TextRun({ text: "Runbook and test cases", font: FONT, size: 28, color: MUTED })] }),
  p(`For the business users testing the consent management platform for the first time, and the test coordinator who runs the session.`, { color: MUTED }),
  new Paragraph({ spacing: { before: 800 } }),
  facts([
    ["Version", R.BUILD.version],
    ["Date", R.BUILD.date],
    ["Build under test", `Branch ${R.BUILD.branch}, commit ${R.BUILD.commit}`],
    ["Test cases", `${cases.length} across ${AREAS.length} areas`],
    ["Companion workbook", "COMPASS-CMP-UAT-Test-Cases.xlsx - record results there, one row per test case, one per step"],
  ]),
);

// Contents
children.push(
  new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Contents", font: FONT })] }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  p("Right-click the table and choose Update Field if page numbers are missing.", { color: MUTED, size: 16 }),
);

// ---------------- Part A: runbook
children.push(h1("Part A - Runbook"));
children.push(h2("1. About this document"));
children.push(
  p("This document prepares you to test COMPASS CMP and then takes you through every test case, step by step. You do not need to know the system beforehand. Read Part A once before you start; keep it open while you test."),
  p("Each test case says who performs it, what must already be true, what data to use, and for every step exactly what to click or type and what you should see. If what you see differs from the expected result, the step fails - even if the difference seems small. That is what we want to find."),
  p("Record results in the companion workbook, COMPASS-CMP-UAT-Test-Cases.xlsx. This document is the reference; the workbook is where results go."),
);

children.push(h2("2. What COMPASS CMP does"));
children.push(
  p("COMPASS CMP is a consent management platform built for India's Digital Personal Data Protection Act, 2023 (DPDP Act). It lets the organisation collect personal data for research only with valid consent, shows each person exactly what they are agreeing to, keeps permanent evidence of every decision, and lets people exercise their rights over their data."),
  p("There are two websites:"),
  bullet("The staff console (http://localhost:3000) - for the Privacy Office, researchers, collection owners and administrators."),
  bullet("The data principal portal (http://localhost:3001) - for the people whose data is collected: giving and withdrawing consent, and making rights requests."),
  p("A typical study flows like this: an R&D user registers a project and its notice; the Privacy Office approves it; a collection owner creates a consent link for a site; people open the link, read the notice and consent; the collection owner exports the list of consenting people and later imports what was collected; people can see and withdraw their consent and ask for access, correction or erasure; every step is recorded in the audit trail.", { before: 60 }),
);
children.push(h3("Words you will meet"));
children.push(table([2300, CONTENT - 2300], ["Term", "Meaning"], R.GLOSSARY, { zebra: true, boldFirst: true }));

children.push(h2("3. Scope of this test cycle", { pageBreak: true }));
children.push(p("Everything built so far is in scope. The test cases are grouped into six areas:"));
children.push(table([2400, CONTENT - 2400 - 900, 900], ["Area", "What it covers", "Case IDs"], R.SCOPE_IN.map(([a, b, c]) => [a, b, `${c}-..`]), { zebra: true, boldFirst: true }));
children.push(h3("New in this release (Sprint 2)"));
children.push(p("These four changes are new since the last demonstration. Test cases that exercise them name the item in their Reference field."));
children.push(table([900, 2400, CONTENT - 3300], ["Item", "Change", "What you should notice"], R.NEW_IN_RELEASE, { zebra: true, boldFirst: true }));
children.push(h3("Not in scope"));
R.SCOPE_OUT.forEach((t) => children.push(bullet(t)));
children.push(h3("Known limits - not defects"));
R.KNOWN_LIMITS.forEach((t) => children.push(bullet(t)));

children.push(h2("4. Test accounts and roles", { pageBreak: true }));
children.push(
  p("Every staff account uses the same password: SeedPassw0rd!2026. Staff sign in with the password and then a six-digit code (second factor). The data principal has no password; she signs in with a one-time code."),
);
children.push(table([1500, 2500, 1800, 1200, CONTENT - 7000], ["Person", "Sign in as", "Role", "Where", "What they do"], R.ACCOUNTS, { zebra: true }));
children.push(
  p("Use these accounts only in this test environment. Never enter real personal data: use the made-up names, mobiles and email addresses your coordinator gives you.", { before: 120 }),
);

children.push(h2("5. The test environment"));
children.push(table([2600, CONTENT - 2600], ["What", "Where / how"], [
  ["Staff console", "http://localhost:3000"],
  ["Data principal portal", "http://localhost:3001"],
  ["Browser", "Latest Google Chrome or Microsoft Edge. Use a private (incognito) window when a case asks you to be a different person, so sessions do not mix."],
  ["One-time codes", "No real email or SMS is sent. Every message - sign-in codes, second-factor codes, invitations, receipts - is written to the test outbox. When a step says \"ask the coordinator for the code\", tell them the contact it was sent to."],
  ["Codes expire", "A code lasts 10 minutes and allows 5 attempts. If it expires, request a new one."],
  ["Sessions", "A session ends after 30 minutes idle or 8 hours. A warning appears before it ends."],
  ["Getting around", "On the console, Ctrl+K (⌘K on a Mac) jumps to any page. Your name at the top right opens the account menu: Your profile, Help manual, theme, Sign out ('Sign out' is also at the bottom of the sidebar). The help manual at /help explains every screen."],
  ["Test data", "Make names unique with your tester number: \"UAT Study 07\", \"UAT Lab 07\", tester07@example.org, +91 98707 00001."],
], { zebra: true, boldFirst: true }));

children.push(h2("6. Before you start"));
children.push(h3("Every tester"));
[
  "Read sections 1-5 and 7.",
  "Open the workbook and write your name in the Tester column of the cases assigned to you.",
  "Sign in once to the console as your assigned role (case ACC-01) to confirm your access works.",
  "Keep a screenshot tool ready (Windows: Win+Shift+S; Mac: Cmd+Shift+4).",
].forEach((t) => children.push(numbered(t, "start")));
children.push(h3("The test coordinator"));
R.COORDINATOR.forEach((t) => children.push(numbered(t, "coord")));
children.push(h3("The coordinator's commands, on a Mac and on Windows"));
children.push(p("Run them from the backend/api folder (backend\\api on Windows) with its Python environment active - the first row does both."));
{
  const mono = (t) => t.split("\n").map((line) => new Paragraph({ spacing: { after: 20 }, children: [new TextRun({ text: line, font: "Consolas", size: 16, color: INK })] }));
  const w = [2600, (CONTENT - 2600) / 2, (CONTENT - 2600) / 2];
  const head = new TableRow({ tableHeader: true, children: ["Task", "Mac or Linux (Terminal)", "Windows (PowerShell)"].map((t, i) => cell(t, w[i], { bold: true, fill: HEAD_FILL })) });
  const rows = R.COMMANDS.map(([task, mac, win], ri) => new TableRow({
    cantSplit: true,
    children: [cell(task, w[0], { fill: ri % 2 ? SOFT : undefined }), cell(mono(mac), w[1], { fill: ri % 2 ? SOFT : undefined }), cell(mono(win), w[2], { fill: ri % 2 ? SOFT : undefined })],
  }));
  children.push(new Table({ width: { size: CONTENT, type: WidthType.DXA }, columnWidths: w, rows: [head, ...rows] }));
}
children.push(p("", { after: 60 }));
R.COMMANDS_NOTES.forEach((t) => children.push(bullet(t)));

children.push(h2("7. How to run a test case", { pageBreak: true }));
[
  "Check the preconditions. If one is not met, do not start: mark the case Blocked and say which precondition failed.",
  "Do each step exactly as written, in order. Use the test data given.",
  "After each step compare the screen with the expected result. Wording matters: a different button name or message is a finding.",
  "If a step fails, take a screenshot, note what you saw, and carry on only if the rest of the case still makes sense; otherwise stop.",
  "Record the result in the workbook: Status (Pass, Fail, Blocked, Not run), date, actual result for any failed step, and the defect ID.",
  "Log each failure once in the Defect Log sheet, with the steps to reproduce and the screenshot file name.",
].forEach((t) => children.push(numbered(t, "howto")));
children.push(h3("Result status"));
children.push(table([1500, CONTENT - 1500], ["Status", "Use it when"], R.STATUS, { boldFirst: true }));
children.push(h3("Defect severity"));
children.push(table([1500, CONTENT - 1500], ["Severity", "Meaning"], R.SEVERITY, { boldFirst: true }));
children.push(h3("What makes a good defect report"));
[
  "A title that says what went wrong, not where: \"Withdrawal leaves the purpose shown as granted\".",
  "The test case and step number, the account used, and the time.",
  "What you did, what you expected, what you saw - copy the exact message.",
  "A screenshot, named with the defect ID.",
].forEach((t) => children.push(bullet(t)));

children.push(h2("8. Suggested order"));
children.push(p("Some areas create the data later areas use, so run them in this order. Within an area, run cases in number order unless the coordinator says otherwise."));
children.push(table([1800, CONTENT - 1800 - 900, 900], ["When", "What", "Cases"], R.ORDER, { zebra: true, boldFirst: true }));

children.push(h2("9. When something goes wrong"));
children.push(table([3000, CONTENT - 3000], ["You see", "Do this"], [
  ["A code never arrives", "Ask the coordinator to check the test outbox for your contact. Check you typed the contact exactly."],
  ["\"Invalid or expired\" on a code", "Request a new code; the old one is spent or past 10 minutes."],
  ["Text like SE::... where a name should be", "Stop and report it as Critical - personal data should always read normally."],
  ["\"Not part of your account\"", "Your role cannot use that page. If the test case says you should be able to, report it."],
  ["\"This export cannot go: ...\"", "Expected when a processor has no country or is in a restricted country - read the message, it names what to fix."],
  ["Your session ended", "Sign in again and repeat the step you were on."],
  ["A card or sidebar entry a step names is missing", "It may be folded: click its heading (the one with a ⌄ arrow) to open it. Folding is remembered in your browser."],
  ["The page does not load at all", "Tell the coordinator; the environment may need restarting. Mark the case Blocked, not Fail."],
], { zebra: true, boldFirst: true }));

children.push(h2("10. Sign-off"));
children.push(p("At the end of the cycle the coordinator summarises the results from the workbook's Summary sheet. The build is accepted when every High-priority case passes and no Critical or High defect is open."));
children.push(table([2600, 2600, 2000, CONTENT - 7200], ["Role", "Name", "Date", "Signature"], [
  ["Business owner", "", "", ""], ["Data Protection Officer", "", "", ""], ["Test coordinator", "", "", ""], ["Delivery lead", "", "", ""],
]));

// ---------------- Part B: index
children.push(h1("Part B - Test cases"));
children.push(p(`${cases.length} test cases. The index lists them all; each case follows on its own page with its steps.`));
children.push(table([1100, CONTENT - 1100 - 2300 - 900 - 900, 2300, 900, 900], ["ID", "Title", "Performed by", "Priority", "Ref"],
  cases.map((c) => [c.id, c.title, c.role, c.priority, c.ref]), { zebra: true }));

// ---------------- Part B: the cases - one per page; an area heading opens the
// page its first case is on.
children.push(new Paragraph({ children: [new PageBreak()] }));
let area = null;
cases.forEach((c, index) => {
  if (c.area !== area) {
    area = c.area;
    children.push(h2(area));
  }
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, spacing: { before: 120 }, children: [new TextRun({ text: `${c.id}  ${c.title}`, font: FONT })] }));
  children.push(facts([
    ["Feature", c.feature],
    ["Performed by", c.role],
    ["Priority / type", `${c.priority} / ${c.type}`],
    ["Reference", c.ref],
    ["Preconditions", listParas(c.preconditions)],
    ["Test data", listParas(c.test_data)],
  ]));
  children.push(p("", { after: 80 }));
  const w = [500, Math.round((CONTENT - 500 - 1000) * 0.5), 0, 1000];
  w[2] = CONTENT - w[0] - w[1] - w[3];
  children.push(table(w, ["#", "Action", "Expected result", "Pass / Fail"], c.steps.map((s, i) => [String(i + 1), s.action, s.expected, ""]), { cantSplit: true }));
  children.push(p([run("Pass criteria: ", { bold: true, size: 18 }), run(c.pass_criteria, { size: 18 })], { before: 100 }));
  children.push(facts([["Tester / date", ""], ["Status", "Pass  /  Fail  /  Blocked  /  Not run"], ["Defect IDs / notes", ""]]));
  if (index < cases.length - 1) children.push(new Paragraph({ children: [new PageBreak()] }));
});

// ---------------------------------------------------------------- document
const doc = new Document({
  creator: "COMPASS CMP delivery team",
  title: "COMPASS CMP - User Acceptance Testing: Runbook and Test Cases",
  styles: {
    default: { document: { run: { font: FONT, size: 20, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 36, bold: true, font: FONT, color: ACCENT }, paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: ACCENT }, paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 22, bold: true, font: FONT, color: INK }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
      ...["start", "coord", "howto"].map((ref) => ({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [run("COMPASS CMP - UAT runbook and test cases", { size: 16, color: MUTED })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: CONTENT }], children: [run(`Version ${R.BUILD.version} - ${R.BUILD.date} - build ${R.BUILD.commit}`, { size: 16, color: MUTED }), new TextRun({ text: "\tPage ", font: FONT, size: 16, color: MUTED }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: MUTED })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT}: ${cases.length} cases`);
});
