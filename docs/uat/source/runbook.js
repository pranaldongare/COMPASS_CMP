// The runbook: what a first-time tester needs before the first test case.
// Plain data, rendered by build_docx.js (and summarised in the workbook).

const BUILD = { version: "1.3", date: "29 September 2026", commit: "3024848", branch: "refactor/frontend-architecture" };

const ACCOUNTS = [
  ["Priya Menon", "dpo@cmp.local", "DPO (Data Protection Officer)", "Staff console", "Runs the Privacy Office: purposes, notices, approvals, rights requests, audit, legal holds, restricted countries."],
  ["System Admin", "admin@cmp.local", "Administrator", "Staff console", "Creates staff accounts and sets roles; reviews grievances about the DPO."],
  ["Kavya Rao", "rnd@cmp.local", "R&D User", "Staff console", "Registers research projects, brings the notice, submits for approval."],
  ["Nikhil Bose", "dcoadmin@cmp.local", "DCO Admin", "Staff console", "Routes approved third-party projects: assigns data sources and a DCO."],
  ["Arun Shetty", "dco@cmp.local", "DCO (Data Collection Owner)", "Staff console", "Runs collection sites: consent links, exports, imports."],
  ["Meera Iyer", "rco@cmp.local", "RCO (R&D Collection Owner)", "Staff console", "Runs in-house collection; answers rights tickets addressed to in-house teams."],
  ["Anjali Verma", "subject@cmp.local / +91 90000 00001", "Data principal", "Portal", "A person whose data is collected: gives and withdraws consent, raises rights requests."],
];

const GLOSSARY = [
  ["Data principal", "The person the data is about (DPDP Act). Uses the portal."],
  ["Data fiduciary", "The organisation deciding why and how data is processed - here, the company running COMPASS."],
  ["Purpose", "A reason for processing, registered by the Privacy Office with its lawful basis, data categories, retention, whether it may go abroad and whether it may apply to a child."],
  ["Notice", "The document shown before consent is asked for (s.5). Versioned; once published it never changes - a correction is a new version."],
  ["Project", "A study that collects personal data. Moves from draft to submitted to approved; only an approved project can collect."],
  ["Processor", "An organisation that collects or handles data for us - a third party, or an in-house team. Has a country (new in this release)."],
  ["Site", "A place a project collects at, run by a processor, owned by a DCO or RCO."],
  ["Consent link", "A link for one site that a person opens to read the notice and record consent. Has an expiry."],
  ["Consent artefact", "The permanent record of one decision: which notice text was shown, what was granted or refused, when. Never edited; a withdrawal is a new artefact."],
  ["Export", "The CSV of people whose consent covers a project, handed to whoever collects. Every row is recorded as a disclosure."],
  ["Import / manifest", "A file from a data source listing the collected assets (recordings, images) and whose consent each is under."],
  ["Asset", "One collected item (a video, an image). A person's appearance in it is linked to their consent."],
  ["Rights request", "A request under ss.11-14: access, correction, erasure, grievance. Has a legal clock."],
  ["Holder / ticket", "A party that holds the person's data, and the instruction sent to it on a rights request. The holder returns the ticket with what it did."],
  ["Erasure scope", "One item per appearance of the person in an asset, each decided: erase, redact, retain or quarantine."],
  ["Legal hold", "A DPO record that stops erasure of an asset or a person until released (new)."],
  ["Restricted country", "A country the Government has notified under s.16 that personal data may not go to (new)."],
  ["Audit trail", "The tamper-evident log of everything done on the platform. Holds ids and facts, never personal words."],
  ["Command palette", "The search box Ctrl+K (⌘K) opens on the console: type part of a page's name and press Enter to go there."],
  ["Help manual", "The guide at /help on each site, open without signing in; the console's opens on the sections for your role."],
  ["One-time code", "A six-digit code sent by SMS or email to prove a contact. In this test environment it goes to the test outbox."],
];

const SCOPE_IN = [
  ["Access and accounts", "Staff sign-in with password and a second-factor code; data principal sign-up and sign-in by one-time code; account page and contacts; staff using the portal as a data principal; the date-of-birth question.", "ACC"],
  ["Registry and administration", "Staff accounts and invitations; purposes; processors (now with a country); data sources; respondents; restricted countries; message wording; cover arrangements.", "REG"],
  ["Projects, notices and links", "A study from registration to a live consent link: projects, purposes, notices and their languages, submission and approval, routing, sites, consent links.", "PRJ"],
  ["Consent and data exchange", "Giving consent through a link; the principal's own consent records and withdrawal; exports (now checked for cross-border transfer); imports, collections and assets.", "CON"],
  ["Rights requests", "Access, correction and erasure requests; the public form; holders and tickets; erasure scope carried out store by store; legal holds; responses that are only as complete as the work done; grievances; nominees.", "RGT"],
  ["Oversight and audit", "Dashboards, the notification bell, what each role sees, the audit trail and its export, and that personal data is never shown scrambled.", "OVS"],
];

const NEW_IN_RELEASE = [
  ["S2-01", "Unknown age is not treated as adult", "A consent is refused until the person's date of birth is known, and a person under 18 is refused outright with no guardian route offered. The portal asks an account with no date of birth for one at its next sign-in; My consents and My requests stay open without answering. The consent link asks between the code and the notice."],
  ["S2-02", "A closed request never claims what did not happen", "An erasure or correction request can close as Complete only when the work is evidenced. Otherwise the Privacy Office must respond Partial, and the response says what remains. The console holds Complete back and says why."],
  ["S2-03", "Erasure that actually erases", "Applying an erasure quarantines the item at once; it is marked erased only when the holder confirms its copy is gone and the platform's pointer is cleared. Each store's status is shown; failures are retried and can be retried on demand. The DPO can place a legal hold on an asset or a person."],
  ["S2-04", "Cross-border control at export", "Every processor has a country. An export is refused if any row would go to a processor with no country, to a restricted country, or abroad for a purpose that does not permit it. The DPO keeps the restricted-country list."],
  ["UI", "Finding your way", "Ctrl+K (⌘K on a Mac) opens a search box that jumps to any page your role has. A breadcrumb shows where you are. Your name at the top right opens an account menu - profile, help manual, theme, sign out. Sidebar groups, a request's 'Clock and path' and a project's 'History' fold away. Lists search as you type (OVS-21)."],
  ["UI", "Your account in tabs", "'Your account' has tabs - Contacts, Active sessions, and on the console Password. Sessions are a table naming the device, with 'Show all' and 'End all other sessions' (ACC-08)."],
  ["HELP", "Help manual", "Both sites have a manual at /help, open without signing in: numbered sections with the screen's own words, a search, and on the console a choice of role (OVS-22)."],
  ["NTC", "Start a notice from any approved one", "'Use an existing notice' offers every approved or published notice, whichever project it is on and whoever wrote it. The copy is still a draft without the original's legal approval (PRJ-06)."],
  ["RGT", "Narrowing your requests", "On the portal, a person with six or more requests can show All, Open or Closed ones and search them (RGT-25)."],
  ["NTC", "One notice in force per project", "Publishing a notice supersedes whichever other is published on the project, whatever its code, so a project never has two. Consent links already handed out keep working and show the new notice; consents already given keep the notice they were given under. Another project's notice code is refused (PRJ-16, PRJ-22)."],
  ["UI", "Next steps at the foot of a project", "The moves in 'What happens next' and the header's buttons are repeated in a 'Next steps' card at the bottom of the project page, so you need not scroll back up (PRJ-08)."],
  ["NTC", "One button to attach purposes", "'Purposes on this notice' has a single 'Attach' button that keeps the dialog open for the next purpose; close it with its × (PRJ-16)."],
];

const SCOPE_OUT = [
  "Breach register, notification and Board reporting (planned for Sprint 3).",
  "Correction that changes the record itself (Sprint 3) - today a correction is a ticket and a response.",
  "Retention and purpose-cessation events driving erasure (Sprint 4).",
  "Legacy consent load and HR/R&D/SEED integration (Sprint 4).",
  "Guardian consent for children (deferred) - a child is refused.",
  "Backups, key escrow, production deployment, load and alerting (parked).",
  "Real email and SMS delivery - messages go to the test outbox.",
];

const KNOWN_LIMITS = [
  "The restricted-country list starts empty. Which countries belong on it is for Legal to confirm; testers add a made-up code such as XZ to test the behaviour.",
  "A holder's confirmation can only be recorded while the request is open. If a holder replies after the response has gone out, the item stays visibly waiting.",
  "Erasure does not yet say anything about backups (a Legal decision is pending; there are no backups in this environment).",
  "If the scheduler (Celery beat) is not running, a consent link past its expiry still shows Active in the console until the next scheduled run, although the portal already refuses it; daily sweeps (erasure retries, closing unverified requests) do not run by themselves.",
  "Audit trail entries written before 21 September 2026 still carry the raw client address in their detail; entries from then on carry only a keyed hash (ADR 0015). Older rows cannot be rewritten without breaking the chain, so this is by design - filter from 21 September when checking what the trail holds.",
  "Staff accounts have no date of birth until their owner gives one, so a member of staff signing in on the portal is asked for one - this is expected.",
  "Cards and sidebar groups that fold are remembered in each browser. If a card or a sidebar entry a step names seems to be missing, click its heading (it has a ⌄ arrow) to open it.",
  "An earlier manual test created an account whose name reads \"Could not reach the server...\". If you meet it, it is test data, not a defect in this release; tell the coordinator.",
];

const STATUS = [
  ["Pass", "Every step behaved as the expected result says."],
  ["Fail", "At least one step did not. Log a defect and write its ID against the case."],
  ["Blocked", "The case could not be run because something before it failed or is missing (for example a precondition). Say what blocked it."],
  ["Not run", "Not attempted in this cycle."],
];

const SEVERITY = [
  ["Critical", "Data is exposed to the wrong person, evidence is lost or changed, or a legal duty is not met (for example a child's consent is recorded, an erasure claims to be done when it is not)."],
  ["High", "A main task cannot be completed and there is no workaround."],
  ["Medium", "A task can be completed but something is wrong or confusing; a workaround exists."],
  ["Low", "Cosmetic: wording, layout, spelling."],
];

const ORDER = [
  ["Day 1 - morning", "Runbook walk-through with the coordinator; everyone signs in once (ACC).", "ACC"],
  ["Day 1 - afternoon", "Registry and administration (REG). Creates the processors and people later cases use.", "REG"],
  ["Day 2", "Projects, notices and links (PRJ) - one study taken from registration to a live consent link.", "PRJ"],
  ["Day 3", "Consent and data exchange (CON) using that link; exports and imports.", "CON"],
  ["Day 4", "Rights requests (RGT), including an erasure carried out end to end.", "RGT"],
  ["Day 5", "Oversight and audit (OVS); re-test of fixed defects; sign-off.", "OVS"],
];

const COORDINATOR = [
  "Start the stack in this order: databases, key service, API, worker, then both portals (see docs/operations/local-development.md). The API answers \"ready\" at http://127.0.0.1:8000/ready when the database, Redis, migrations and key service are all reachable.",
  "Start exactly one scheduler (Celery beat; the command is in the table below) if the cycle should see scheduled work - a link's status turning Expired, the daily rights sweep that retries erasures and closes unverified requests. Without it the portal still refuses an expired link, but the console keeps showing it as Active.",
  "Run the seed once (the command is in the table below). Since 25 September it creates only the administrator (admin@cmp.local) and the reference data: processors SEED, SRIB and Pune Motion Lab with their data sources (CIT, VIT, SE, Voice, the Pune rig), two purposes, and the approved Gait Identification Study 2026 with its published notice NTC-GAIT-2026. It is safe to run again. Do not run scripts/seed_demo.py on the UAT database: it adds a dozen more people and changes what the cases see.",
  "Make sure the test accounts exist - the current test database already has them; check 'Users' first. On a freshly built database, sign in as the Administrator and use 'Provision account' for Priya Menon dpo@cmp.local (DPO), Kavya Rao rnd@cmp.local (R&D User), Nikhil Bose dcoadmin@cmp.local (DCO Admin), Arun Shetty dco@cmp.local (DCO) and Meera Iyer rco@cmp.local (RCO), then set each password to SeedPassw0rd!2026 with the code in its invitation (REG-01 and REG-02 show how). In 'Data sources' use 'Assign' to make Arun Shetty accountable for CIT, VIT and the Pune rig, and Meera Iyer for SE and Voice. Finally sign Anjali Verma up on the portal ('Create an account'): mobile +91 90000 00001, email subject@cmp.local, date of birth 12 March 1994.",
  "Keep the test outbox open: var/outbox.log in the backend/api folder (backend\\api\\var\\outbox.log on Windows). Every email and SMS is appended there. To find a tester's code, search it for their contact - the table below gives the command on a Mac and on Windows. Use the command rather than opening the file in an editor: the outbox grows to tens of megabytes, and an editor's search finds the oldest code, not the latest.",
  "Give each tester a unique made-up mobile (+91 98xxx xxxxx) and email (testerNN@example.org) for sign-up cases, so tests do not collide.",
  "Hand out a live consent link for the CIT site of Gait Identification Study 2026. On the current test database it is valid until 8 October 2026; on a freshly built one, sign in as Arun Shetty, open the project and use 'Create link' on the CIT row (PRJ-18 shows how) - the link the seed prints is for the Pune site.",
  "Codes are limited to 20 per consent link per hour and 5 per contact per hour. With several testers on one link, mint one link per tester or pair (a DCO can, see the PRJ cases), or space the consent cases out.",
  "For the export-with-no-country case (CON-17), prepare an approved project whose site is run by a processor with no country and has at least one consent: the processor edit dialog cannot clear a country once set.",
  "For the under-18 cases, have the Administrator create throwaway accounts (REG-01) rather than using seeded ones: a date of birth, once given, cannot be changed from the portal. Keep admin@cmp.local without a date of birth; CON-11 relies on it.",
  "Have the filled notice template ready for notice-upload cases (tests/fixtures/notice_filled.docx is a filled example).",
  "After cross-border cases, check every processor changed during testing is back to country IN and any test restriction (XZ) is lifted.",
];

// The coordinator's commands on each system. Run from the backend/api folder with
// its Python environment active (the first row).
const COMMANDS = [
  ["Open the API folder and its Python environment", "cd backend/api\n. .venv/bin/activate", "cd backend\\api\n.venv\\Scripts\\Activate.ps1"],
  ["Check the API is ready", "curl http://127.0.0.1:8000/ready", "curl.exe http://127.0.0.1:8000/ready"],
  ["Run the seed", "python scripts/seed.py", "python scripts\\seed.py"],
  ["Start the worker (without it no code is ever delivered)", "celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo", "celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo"],
  ["Start the scheduler (exactly one)", "celery -A cmp.tasks.app beat -l info", "celery -A cmp.tasks.app beat -l info"],
  ["Watch the outbox as messages arrive", "tail -f var/outbox.log", "Get-Content var\\outbox.log -Wait -Tail 20"],
  ["Find the latest code sent to a contact (here dpo@cmp.local)", "grep -A6 \"to: dpo@cmp.local\" var/outbox.log | tail -7", "Select-String -Path var\\outbox.log -Pattern \"to: dpo@cmp.local\" -Context 0,6 | Select-Object -Last 1"],
  ["Stop a running command", "Ctrl+C", "Ctrl+C"],
];

const COMMANDS_NOTES = [
  "Mac or Linux: use the Terminal app. Windows: use PowerShell (Start menu, type PowerShell), not the older Command Prompt - the Windows commands here are PowerShell commands.",
  "On Windows, if PowerShell refuses to run Activate.ps1 because running scripts is disabled, first run Set-ExecutionPolicy -Scope Process Bypass. It applies to that PowerShell window only and ends when the window closes.",
  "On Windows type curl.exe, not curl: in Windows PowerShell 5, curl is another command with different output. Or open http://127.0.0.1:8000/ready in the browser.",
  "Keep each long-running command (worker, scheduler, outbox watch) in its own window.",
];

module.exports = { BUILD, COMMANDS, COMMANDS_NOTES, ACCOUNTS, GLOSSARY, SCOPE_IN, NEW_IN_RELEASE, SCOPE_OUT, KNOWN_LIMITS, STATUS, SEVERITY, ORDER, COORDINATOR };
