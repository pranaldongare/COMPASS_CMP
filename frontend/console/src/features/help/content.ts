/**
 * The staff console's help manual.
 *
 * Written against the screens as they are: every `[[Label]]` is the exact
 * words of a button, field or page, so a reader can match an instruction to
 * what they see. When a screen changes its words, the manual changes with it.
 */
import type { HelpSection, RoleOption } from "@/features/help/types";

export const ROLES: RoleOption[] = [
  { value: "dpo", label: "DPO" },
  { value: "admin", label: "Administrator" },
  { value: "rnd_user", label: "R&D User" },
  { value: "dco_admin", label: "DCO Admin" },
  { value: "dco", label: "DCO" },
  { value: "rco", label: "RCO" },
  { value: "breach_holder", label: "Temporary ticket holder" },
];

const COLLECTORS = ["dco_admin", "dco", "rco"];

export const INTRO =
  "How to use the staff console, task by task: signing in, registering projects and their notices, running collection, handling rights requests and personal data breaches, and reading the audit trail. Choose your role to see only the sections written for you, or search for what you want to do.";

export const SECTIONS: HelpSection[] = [
  {
    id: "introduction",
    title: "Introduction",
    summary: "What the platform is for, and who does what.",
    blocks: [
      {
        kind: "p",
        text: "COMPASS CMP records consent under the Digital Personal Data Protection Act 2023 and everything that follows from it: which studies may collect, what people were told, what they agreed to, who their data went to, and how their rights requests were answered. Everything anyone does is written to a tamper-evident audit trail.",
      },
      {
        kind: "terms",
        items: [
          {
            term: "DPO",
            meaning:
              "The Data Protection Officer. Keeps purposes and processors, writes and approves notices, approves projects, answers rights requests, handles incidents and personal data breaches, and reads the audit trail.",
          },
          {
            term: "Administrator",
            meaning:
              "Creates staff accounts and sets roles, keeps the wording of messages, and reviews grievances about the DPO.",
          },
          {
            term: "R&D User",
            meaning:
              "Registers research projects, brings their notice and approval, and submits them for review.",
          },
          {
            term: "DCO Admin",
            meaning:
              "Routes approved projects collected by third parties: adds their collection sites.",
          },
          {
            term: "DCO",
            meaning:
              "Data Collection Owner. Runs third-party collection sites: consent links, exports and imports.",
          },
          {
            term: "RCO",
            meaning:
              "R&D Collection Owner. Runs in-house collection, and answers rights tickets addressed to in-house teams.",
          },
          {
            term: "Temporary ticket holder",
            meaning:
              "Somebody inside the organisation without a console login whom the Privacy Office has asked to act on a breach, or to answer a rights ticket. Signs in like staff and sees only their own tickets, which they can still read once their part is over.",
          },
        ],
      },
      {
        kind: "note",
        text: "What you can see and do is decided by the server from your role. If a button in this manual is not on your screen, your role does not have it - it is not broken.",
      },
    ],
  },
  {
    id: "signing-in",
    title: "Signing in",
    summary: "Your password, then a six-digit code sent to your email.",
    blocks: [
      {
        kind: "steps",
        items: [
          "Open the console. On the [[Sign in]] page type your work email or username in [[Email or username]] and your password in [[Password]], then click [[Sign in]].",
          "The page changes to [[Verify it is you]]. A six-digit code is on its way to your registered email.",
          "Type the code in [[6-digit code]] and click [[Verify and continue]]. The code works for five minutes; [[Send a new code]] sends another.",
          "You land on your [[Dashboard]]. Your name and role are at the top right.",
        ],
      },
      {
        kind: "steps",
        title: "Your first sign-in",
        items: [
          "Your administrator creates your account; an email invites you to [[Set your password]].",
          "Open the link in the email, type the [[Code]] it contains, choose a [[New password]] of at least 12 characters, confirm it and click [[Set the new password]].",
          "Your account is now active. Sign in as above.",
        ],
      },
      {
        kind: "list",
        title: "Good to know",
        items: [
          "Five wrong passwords lock the account for 30 minutes. The message never says which part was wrong.",
          "[[Forgotten your password?]] on the sign-in page sends a code to reset it. Setting a new password signs you out everywhere else.",
          "A session lasts at most eight hours, and ends after 30 minutes without activity. A warning appears before it ends.",
          "[[Sign out]] is at the bottom of the sidebar.",
        ],
      },
    ],
  },
  {
    id: "finding-your-way",
    title: "Finding your way around",
    summary: "The sidebar, search, the command palette and your notifications.",
    blocks: [
      {
        kind: "list",
        items: [
          "The sidebar lists only the sections your role has, grouped under Overview, Governance, Consent, Registry, Data movement, Oversight and You. [[Collapse sidebar]] at its foot folds it to icons; your choice is remembered.",
          "The breadcrumb beside the logo shows where you are, for example [[Oversight › Rights requests]]. Click the second part to go back to the list.",
          "[[Jump to page…]] in the header - or ⌘K on a Mac, Ctrl+K elsewhere - opens the command palette. Type a few letters of a page and press Enter. It also offers your recent pages, the theme switch and [[Sign out]].",
          "The bell opens [[Notifications]]: events on the records you can see, each linking to the page it is about.",
          "Lists search as you type. Each filter you set shows as a chip under the toolbar; its × removes just that filter.",
        ],
      },
      {
        kind: "note",
        title: "“Not part of your account”",
        text: "If you follow a link to a section your role does not have, the console says so and offers [[Back to your dashboard]]. Nothing is wrong; that page belongs to another role.",
      },
    ],
  },
  {
    id: "dashboard",
    title: "Your dashboard",
    summary: "What needs you today, your work queues, and the position.",
    blocks: [
      {
        kind: "list",
        items: [
          "[[Needs attention]] lists only work you can act on, most urgent first - for example [[Requests awaiting verification]] or [[Projects pending approval]]. Each row opens the list that explains it, already filtered.",
          "Below it are your work queues; an empty queue is listed as clear rather than hidden.",
          "The DPO also sees [[Projects by stage]] and the [[Consent position]] across the platform.",
          "[[Recent activity]] shows the latest events on your records.",
        ],
      },
    ],
  },
  {
    id: "profile",
    title: "My profile and sessions",
    summary: "Contacts, a personal email, your active sessions and your password.",
    blocks: [
      {
        kind: "steps",
        title: "Add a personal email",
        items: [
          "Open the account menu (your name, top right) and click [[My profile]]. The [[Contacts]] card shows your work email (it cannot be changed here).",
          "In the [[Personal email]] row click [[Add]], type the address and click [[Save and send a code]].",
          "Type the code sent to that address in [[Six-digit code]] and click [[Confirm]]. It can now sign you in to the portal as a person.",
        ],
      },
      {
        kind: "list",
        items: [
          "[[Active sessions]] lists where you are signed in. [[End session]] signs out another device; this one is marked [[this device]].",
          "[[Change your password]] needs your current password and signs out your other sessions.",
        ],
      },
    ],
  },
  {
    id: "purposes",
    title: "Purposes",
    summary: "What data is collected for, on what basis, and for how long.",
    roles: ["dpo", "admin"],
    blocks: [
      {
        kind: "steps",
        title: "Create and activate a purpose",
        items: [
          "Click [[Purposes]] under Governance, then [[New purpose]].",
          "Fill in [[Code]], [[Name]], [[Description]], [[What this allows]], tick the [[Data collected]], and choose the [[Lawful basis]], [[Retention (days)]], [[Retention basis]] and [[Erasure trigger]].",
          "Tick [[Transfer outside India is permitted for this purpose]] only if it is; exports abroad are refused otherwise. Leave [[May be used for data of children]] unticked unless it truly applies.",
          "Click [[Create purpose]]. It starts as [[Draft]] and can be edited; the code cannot.",
          "Click [[Activate]] on its row. Only an active purpose can appear on a notice.",
        ],
      },
      {
        kind: "warning",
        text: "A purpose used by a published notice cannot be retired - people agreed to it. [[Retire]] is for purposes no notice carries any more.",
      },
    ],
  },
  {
    id: "processors",
    title: "Processors and restricted countries",
    summary:
      "Who collects or handles data for you, where they are, and where data may not go.",
    roles: ["dpo", "admin"],
    blocks: [
      {
        kind: "steps",
        title: "Register a processor",
        items: [
          "Click [[Processors]] under Registry, then [[Register processor]].",
          "Enter the [[Registered legal name]], [[Type]], [[Contract reference]], the two-letter [[Country]] (IN for India) and [[Security confirmed on]].",
          "Tick [[We collect this ourselves]] for an in-house team. Projects naming a third party go to the DCO Admin once approved; projects naming an in-house team come back to their author.",
          "Click [[Register processor]].",
        ],
      },
      {
        kind: "list",
        items: [
          "[[Respondents]] names the people at a processor who answer rights tickets.",
          "[[Edit]] changes the details, including the country; [[Suspend]] stops new work with the processor.",
        ],
      },
      {
        kind: "steps",
        title: "Restrict a country (DPO)",
        items: [
          "Below the processors, find [[Restricted countries (s.16)]].",
          "Type the [[Country]] and the Government's [[Notification]] reference, and click [[Restrict]].",
          "From then on an export is refused if any row would go to a processor there. [[Lift]] ends the restriction.",
        ],
      },
    ],
  },
  {
    id: "sources",
    title: "Data sources",
    summary:
      "The rigs and feeds a processor collects with, and who is accountable for each.",
    roles: ["dpo", ...COLLECTORS],
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[Data sources]] under Registry, then [[Register source]].",
          "Enter [[Code]], [[Name]], [[Role]], [[Exchange mode]], [[Identifier scheme]], choose [[Operated by]] and tick what it is [[Authoritative for]]. A DCO may choose only a third party; an RCO only an in-house team.",
          "Click [[Register source]]. Tick the filter [[Nobody accountable]] to find sources without an owner.",
          "Click [[Assign]] and choose who is accountable: a DCO for a third party's source, an RCO for an in-house one.",
        ],
      },
      {
        kind: "note",
        text: "[[Suspend]] refuses further imports from a source. Code, role, exchange mode and processor cannot be changed after registration.",
      },
    ],
  },
  {
    id: "projects",
    title: "Registering a project",
    summary: "Every collection begins with a project.",
    roles: ["rnd_user", "dpo"],
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[Projects]], then [[Register a project]].",
          "Enter the [[Project name]] (what a person would recognise it as), [[Description]], and optionally [[Internal name]] and [[Requesting team]].",
          "Under [[Who will collect]] tick every processor that will collect - a partner collecting for you and an in-house team can both be ticked. A note explains where the project will go once approved.",
          "Click [[Register project]]. It starts [[In Draft]].",
        ],
      },
      {
        kind: "p",
        text: "The project page leads with its progress (In Draft › Pending Approval › Approved) and a [[What happens next]] card - the one next move, or everything still missing - beside its [[Details]]. The rest is in tabs: [[Overview]], [[Setup]] (who is collecting, notices, approvals), [[Consent]] (sites and consent links), [[Collections & exchanges]] and [[Activity]] (history). Each button sits on the card it changes, and the [[At a glance]] figures open the records they count.",
      },
    ],
  },
  {
    id: "notices",
    title: "Bringing the notice",
    summary: "The notice people read before they consent.",
    roles: ["rnd_user", "dpo"],
    blocks: [
      {
        kind: "steps",
        title: "Upload the filled notice template (R&D User)",
        items: [
          "On the project, open [[Setup]] and in the [[Notices]] card click [[Upload a notice document]].",
          "Choose the filled DPDP notice template (.docx) and click [[Check the document]]. Nothing is written yet: you see the purposes and data categories it found, and any warnings.",
          "Click [[Create the notice]]. It is created as [[Draft]] with its purposes.",
        ],
      },
      {
        kind: "list",
        items: [
          "A template with placeholders still in it is refused.",
          "[[Copy an existing notice]] starts from any notice the Privacy Office has approved or published, on any project - it arrives as a draft, and each language must be approved again.",
          "Only the DPO writes or approves notice wording, purposes and translations.",
        ],
      },
      {
        kind: "steps",
        title: "Use a notice template (R&D User)",
        items: [
          "Ask the Privacy Office for the template ID, like TPL-0007.",
          "On the project, open [[Setup]] and in the [[Notices]] card click [[Use a notice template]].",
          "Enter the ID and click [[Look up]]. You see what it carries: its name, who it addresses, its purposes and languages.",
          "Click [[Make this project's notice from it]]. The project gets its own draft notice, which the DPO approves and publishes as usual.",
        ],
      },
      {
        kind: "steps",
        title: "Write a notice template (DPO)",
        items: [
          "Click [[New notice template]] - on your dashboard, or at the top of [[Notices]]. Your templates are listed in the [[Templates]] tab there.",
          "Give it a [[Template name]], the DPO contact and the three links, and paste the text if you have it. Click [[Create template]].",
          "On its page, add its purposes and the text in each language. Nothing on a template needs approving - each language is approved on the project's notice made from it.",
          "Give its ID to the study's R&D User; [[Copy ID]] puts it on the clipboard. [[Retire]] stops it being used; notices already made from it are unaffected.",
        ],
      },
    ],
  },
  {
    id: "approval",
    title: "Submission and approval",
    summary: "From draft to approved - which publishes and freezes the notice.",
    roles: ["rnd_user", "dpo"],
    blocks: [
      {
        kind: "steps",
        title: "Submit (R&D User)",
        items: [
          "Click [[Upload approval]]. Choose the [[Type]], enter the [[Reference number]] and [[Approved on]] date, attach the [[Proof document]] and click [[Upload approval]]. An approval without a proof file does not count.",
          "In [[What happens next]], click [[Pending Approval]]. The DPO is told.",
        ],
      },
      {
        kind: "steps",
        title: "Review and approve (DPO)",
        items: [
          "Open the project from [[Needs attention]] › [[Projects pending approval]].",
          "[[What happens next]] lists what still blocks approval, with links: activate each purpose the notice carries, and legally approve each language.",
          "On the notice, [[Edit English text]] (or the language shown) to correct the wording, [[Add language]] for another language, then [[Approve]] each language. The approved text is hashed; consent is matched against it.",
          "Back on the project click [[Approved]], add an optional note and [[Confirm]]. The notice is published and frozen.",
          "To send it back instead, click [[In Draft]] - a reason is required and kept in the history.",
        ],
      },
      {
        kind: "warning",
        text: "A published notice can never be edited. A correction is a new version of the notice, which supersedes the old one. Adding a site after publication adds a recipient, which also needs a new version. A project has one notice in force: publishing another supersedes it, and its consent links then show the new notice - consents already given keep the notice they were given under.",
      },
    ],
  },
  {
    id: "sites-and-links",
    title: "Collection sites and consent links",
    summary: "Where a project collects, and the link people open to consent.",
    roles: [...COLLECTORS, "rnd_user", "dpo"],
    blocks: [
      {
        kind: "steps",
        title: "Add a site",
        items: [
          "Third-party collection: the DCO Admin opens the approved project. In-house collection: the project's R&D User does.",
          "Open the project's [[Consent]] tab, click [[Add site]], choose the [[Data source]] (only sources under the project's processors are offered) and type the [[Location]].",
          "Click [[Add collection site]]. The source's owner runs the site; [[Who runs it]] changes that for this project only.",
        ],
      },
      {
        kind: "steps",
        title: "Create a consent link (DCO or RCO running the site)",
        items: [
          "On the project, click [[Create link]] on the site's row.",
          "Set when it expires - an expiry is required - and how many times it may be used, then click [[Create link]].",
          "Copy the link from [[Copy this now]]. It opens on the portal, not the console. Share it with the people you collect from.",
        ],
      },
      {
        kind: "list",
        items: [
          "[[Replace link]] issues a new link; the old one stops working at once.",
          "A revoked, expired or used-up link shows people [[This link is not valid]] and nothing else.",
        ],
      },
    ],
  },
  {
    id: "consents",
    title: "The consent register",
    summary: "Every decision people made, and the exact notice they were shown.",
    roles: ["dpo", ...COLLECTORS],
    blocks: [
      {
        kind: "list",
        items: [
          "[[Consents]] lists each person once, at their current decision: [[Consented]], [[Partial]], [[Declined]] or [[Withdrawn]]. A DCO or RCO sees only the sites they run.",
          "Withdrawn means a withdrawal left nothing agreed. Someone who withdrew one purpose of several is [[Partial]], and the rest still stands.",
          "Narrow the list with [[Project]], [[Site]] (once a project is chosen), [[Status]] - [[Full - every purpose]] or [[Partial - some purposes]], declined or withdrawn - and [[Given from]] and [[Given to]], the days the consent was given. [[Clear filters]] shows everything again; the address bar keeps the filters, so a view can be bookmarked.",
          "Open a person for the record: the purposes agreed and refused, the exact notice text served, and the assets they appear in. [[Audit trail]] opens the trail filtered to that record.",
        ],
      },
      {
        kind: "note",
        text: "A consent record is never edited. A withdrawal is a new record that supersedes the old one, which stays as evidence of what was agreed at the time.",
      },
    ],
  },
  {
    id: "exports",
    title: "Exports",
    summary:
      "The file of people whose consent covers a project, and the checks on where it goes.",
    roles: ["dpo", ...COLLECTORS],
    blocks: [
      {
        kind: "steps",
        items: [
          "On an approved project open [[Collections & exchanges]] and click [[Generate export]]. Read the warning: the file holds names and contacts, and each row is recorded as a disclosure.",
          "Click [[Generate the export]].",
          "Open [[Exports]] and click [[Download]]. Downloading again gives the same file and creates no new export.",
        ],
      },
      {
        kind: "warning",
        title: "When an export is refused",
        text: "Before writing anything, every row's destination - the processor running its site - is checked. The export is refused if a processor has no recorded country, is in a restricted country, or is abroad while a purpose the person agreed to does not permit transfer outside India. The message says which.",
      },
    ],
  },
  {
    id: "imports",
    title: "Imports, collections and assets",
    summary: "The manifest of what a site collected, under whose consent.",
    roles: ["dpo", ...COLLECTORS],
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[Imports]], then [[Import a manifest]]. [[Download the manifest template]] and fill it in; [[What the file must contain]] explains each column.",
          "Choose the [[Data source]] and the [[Project]], choose your file and click [[Check it — this writes nothing]]. Problems are listed by row and column.",
          "When it says [[Manifest is valid]], click [[Import]].",
          "The batch page shows what was accepted and rejected. [[Collections]] and each collection's assets follow from it.",
        ],
      },
      {
        kind: "list",
        items: [
          "Every row marked consented needs the consent it was collected under; a bystander is marked incidental with none.",
          "The same file is never imported twice.",
          "An asset holding someone with no consent is flagged on its collection.",
        ],
      },
    ],
  },
  {
    id: "rights-requests",
    title: "Rights requests",
    summary:
      "Access, erasure and grievances - sections 11 to 13 - on a legal clock, each about everything held about the person.",
    roles: ["dpo", "admin"],
    blocks: [
      {
        kind: "p",
        text: "[[Rights requests]] lists every request with its clock. Filter by [[Status]], [[Kind]], [[Clock]] and [[Tickets]]. A request that arrived by email is logged with [[Log a request received by email]]. A request opens on where it stands - when it is due, its current step, who has it and the next move or what blocks it. [[Clock and path]] opens the full checkpoints and steps. Work through the path below; [[What happens next]], under [[Next step]] straight after classification, always says what may be done now and what blocks the rest. Documents the person sent with the request are listed under the request text as [[Documents from the requester]]; each download is on the trail.",
      },
      {
        kind: "steps",
        title: "The path",
        items: [
          "Check identity: a request made signed in, or verified by code, is already verified.",
          "Classify it in [[A valid … request?]] and click [[Confirm classification]]. For an erasure, confirm [[They mean erasure]] - erasure is not withdrawal. Not a rights request, or one that cannot be met? Click [[Refuse this request]], write the reason and click [[Refuse and close]] - the person is told why, with the grievance route.",
          "Under [[Next step]], click [[In progress]].",
          "Holders and tickets: [[Find who holds the data]], then for each holder [[Confirm who answers]], then [[Send tickets]]. Click a holder to open its ticket: what it was asked, its answer and its messages. The main action is the button on its row; the rest are under [[More]].",
          "Before sending, open a holder to read or change [[What their ticket will ask]] - the standard words for the request, which you can make that holder's own. For an erasure the ticket also lists each item that holder holds and what to do with it.",
          "How each holder answers is settled as the ticket goes: a colleague with a console login answers in their [[My tasks]]; one inside the organisation without a login is given a temporary login; anyone outside - a vendor, a processor - is emailed a link, opens it with a code sent to the same address, and answers on the portal. Their row says which.",
          "When an answer comes, the holder shows [[Answered - review]]. [[Accept the answer]] to count it, or [[Send back]] with what is missing. Only an accepted answer counts toward closing the request.",
          "An overdue holder is reminded every day by itself; [[Send a reminder]] sends one now, and [[Send final reminder]] - only once it is overdue - lets the response go out partial, naming the gap. [[Withdraw]] a ticket sent in error, and [[Reopen]] it if needed; [[Remove]] a holder found by mistake before it is sent anything.",
          "Every holder needs an email address: whoever answers is emailed the ticket. A holder without one says [[No email - add one before sending]]; click [[Add their email]]. Until the ticket goes, [[Change who answers]] changes the person or address. After it goes, a mistyped address is fixed with [[Correct their email]] under [[More]]: the ticket is sent again to the right address, and nobody at the wrong one is written to.",
          "Moved to collating too soon - a holder still to ask, or more needed from one? Under [[What happens next]], choose [[Why]] and click [[Back to awaiting holders]] (or [[Back to in progress]] if no ticket was ever sent). The reason is kept on the audit trail; the clock does not pause.",
          "Erasure scope: [[Find what is held]]. For each asset choose [[Erase]], [[Redact]], [[Retain]] (a retention floor, with its date) or [[Quarantine]], give the basis and [[Record the decision]], then [[Apply]].",
          "Respond: write [[The response]], attach any files, choose the outcome and click [[Release and close]]. The person is told and downloads it from the portal.",
        ],
      },
      {
        kind: "list",
        title: "How erasure is carried out",
        items: [
          "Applying an erasure takes the item out of use at once ([[quarantined - being erased]]). It shows as erased only when the holder confirms its copy is gone and the platform's pointer is cleared; each store's status is listed. [[Try again now]] retries what failed.",
          "[[Place a legal hold]] stops the erasure of an asset or a person until [[Release hold]]; what it stopped then carries on.",
          "[[Complete]] is offered only when everything asked was carried out with evidence. Otherwise the response goes out [[Partial]] and says what remains.",
        ],
      },
      {
        kind: "note",
        title: "Grievances",
        text: "A dispute of a response is a grievance linked to the original. The DPO decides it as upheld or not upheld. A grievance about the DPO's own decision goes to the Administrator, who sees it as [[Grievances about the DPO]].",
      },
    ],
  },
  {
    id: "breaches",
    title: "Incidents and personal data breaches",
    summary:
      "From an incident's first minutes to closing it: validation, the duties and their clocks, the notices, the tickets.",
    roles: ["dpo"],
    blocks: [
      {
        kind: "p",
        text: "[[Breaches]] is the Privacy Office's alone; every other role is told it is not there. The platform logs, records, drafts and tracks every clock. It never reports to the organisation's board, the Data Protection Board or CERT-In: a person does, through their own channel, and you record it.",
      },
      {
        kind: "tip",
        title: "Finding an incident",
        text: "On [[Incidents and personal data breaches]], [[Search]] by either reference (INC- or BR-), the title or where it occurred. Narrow the list with [[Validation]], [[Duties]] (overdue, or due within 24 hours), [[Recent activity]] and [[Tickets]], and [[Sort]] by the most recent activity or by what is due soonest. [[Clear filters]] shows everything again.",
      },
      {
        kind: "tip",
        title: "Finding your way on a breach's page",
        text: "[[Close the breach]] sits at the top, with a list of what still stands in the way. Below it the work is in tabs, in the order it runs: [[Duties]], [[Validation]], [[People & notices]], [[Tickets]], [[Assessment]] and [[Activity]]. A red count on [[Duties]] or [[Tickets]] means something there is late.",
      },
      {
        kind: "steps",
        title: "From incident to close",
        items: [
          "[[Log an incident]] - from your dashboard or [[Breaches]] - with the time it was [[First noticed]], not now. Under [[What is known so far]] answer what you can: [[Is it a cyber attack?]] (Yes starts the CERT-In duty at once), where it started, how it was found, the systems, how much, countries, kinds of data, whose data, our entities and third parties - all optional. [[Attach a file]] for the email that reported it, a screenshot or a chat; more can go on the [[Attachments]] tab later. It gets an INC reference, and the [[Organisation's board]] duty starts: thirty minutes from first noticed.",
          "Tell the board now: [[Brief for the organisation's board]] drafts what to say and prints. Then [[Record the report]] on the duty, with when and to whom.",
          "If it may be a reportable cyber incident, [[Mark reportable to CERT-In]]: six hours from first noticed.",
          "Record the [[Validation]]: is it a personal data breach under s.2(u)? The first yes records it with a BR reference and starts the Board and principals duties. No sets them aside; the reasoning is kept.",
          "Derive [[Who it touched]], keep the assessment current, and draft the notice. [[Send version 1]] waits until the breach is recorded.",
          "People the records cannot show - not on the platform, or known only by their assets: on [[People & notices]] click [[Add people from a list]], choose what the list holds, [[Download the template]], fill it in and save it as CSV. [[Check the file]] shows what it would add and which rows it cannot read; then [[Add to the list]]. People with no account are sent the notice by email and SMS, and count toward [[Principals notified]] like everyone else.",
          "Ask the people who must act: [[Assign a ticket]] to a member of staff, or choose [[Someone without a console login]] and give their name and work email, with what you need and an optional [[Answer by]]. Read their answers on the ticket; [[Send back]] or [[Close the ticket]] once it is returned.",
          "Draft [[Documents for the Board]], submit through the Board's own channel, and [[Record submission]] on each duty with the reference returned.",
          "Close it once validated, every duty is done or not applicable, and no ticket is open. The page lists what is in the way.",
        ],
      },
      {
        kind: "note",
        title: "What a ticket holder sees",
        text: "The breach reference, your instruction, the thread and their ticket's state - nothing else from the register. Their email says only that a ticket from the Privacy Office is waiting; it names no breach.",
      },
      {
        kind: "list",
        title: "Temporary logins and colleagues",
        items: [
          "Somebody with no console login, on one of the organisation's own email domains, is given a login for this breach only. They are emailed a code to set a password, and sign in with an emailed code like all staff. The Tickets table marks it [[Temporary login]], and says whether they have signed in yet.",
          "A holder can [[Add a colleague]] while their ticket is open. The colleague gets their own ticket on the breach, opening with the holder's note rather than your instruction, and shows in the table under the person who added them. You can see every addition; you do not approve it.",
          "When you [[Withdraw]] that person's ticket or the breach closes, their part is over: they keep their login, read only, so they can still read their ticket. The table marks it [[Temporary login · read only]]. Reopening their ticket lets them answer again. Only an administrator's [[End temporary access]] removes the login.",
        ],
      },
    ],
  },
  {
    id: "temporary-holder",
    title: "If you were given a login for a ticket",
    summary:
      "The Privacy Office has asked for your help - with a personal data breach, or with a person's request about their data - and given you a login that lasts as long as the work does.",
    roles: ["breach_holder"],
    blocks: [
      {
        kind: "steps",
        title: "Signing in",
        items: [
          "Your email from the Privacy Office has a link and a code. Open the link, type the [[Code]], choose a [[New password]] of at least 12 characters, confirm it and click [[Set the new password]].",
          "Sign in with your work email and that password. A six-digit code is emailed to you: type it in [[6-digit code]] and click [[Verify and continue]].",
          "You land on [[My tasks]]. Your ticket is there: a breach ticket at the top, a ticket on a rights request under [[To do]].",
        ],
      },
      {
        kind: "list",
        title: "What you can see",
        items: [
          "A breach ticket: the breach reference, what you are asked, the date to answer by if there is one, and the conversation with the Privacy Office. Nothing else about the breach.",
          "A rights ticket: the request's reference, what you are asked, what the platform already holds about the person, for an erasure the items you hold and what to do with each, and the conversation. Click [[Answer]], then [[Submit your answer]] when your work is done; the Privacy Office reviews it.",
          "[[My tasks]], your notifications and your profile. Nothing else in the console is open to you.",
          "On a breach ticket, answer as anyone does: write, attach a file, and when you are done choose what was done and tick [[This is my return]].",
        ],
      },
      {
        kind: "steps",
        title: "Bringing in a colleague",
        items: [
          "While your ticket is open, click [[Add a colleague]] on it.",
          "Give their name, their work email (on one of the organisation's own domains), a mobile if you wish, and a note saying what you are asking them to do.",
          "Click [[Add]]. They get their own ticket, which opens with your note; if they have no console login they are given one for this breach, as you were. The Privacy Office can see that you added them.",
        ],
      },
      {
        kind: "note",
        title: "When your part is over",
        text: "When the Privacy Office closes the breach or withdraws your ticket, you can no longer write on it, but you keep your login and can still read it. If the Privacy Office reopens your ticket, you are emailed that a ticket is waiting. Only an administrator can end the login itself.",
      },
    ],
  },
  {
    id: "tickets",
    title: "My tasks",
    summary:
      "Answering the Privacy Office when a rights request needs your team's records, or a breach needs you to act.",
    blocks: [
      {
        kind: "steps",
        items: [
          "[[My tasks]] in the sidebar shows a count of tickets with something unread.",
          "Rights tickets are in three groups: [[To do]], [[Waiting on the Privacy Office]] and [[Done]].",
          "Click [[Answer]] on a ticket. It shows what the platform already knows and the messages so far.",
          "Ask a question in the message box, attach a file if needed, and [[Send]]. Your message is on the ticket and the window stays open.",
          "When your work is done, click [[Submit your answer]]: choose what was done, say what you hold and did, attach any proof, and click [[Send your answer]].",
          "The Privacy Office reviews it. Accepted, it moves to [[Done]]; sent back, it returns to [[To do]] with what is missing and a new date. While a ticket is overdue you are reminded by email every day.",
        ],
      },
      {
        kind: "list",
        title: "Breach tickets",
        items: [
          "A breach ticket is the Privacy Office asking for your help with a personal data breach. It shows the breach reference, what you are asked and the date to answer by, if there is one - nothing else about the breach.",
          "Answer the same way: write on the thread, attach a file, and when you are done choose what was done and tick [[This is my return]].",
          "Only the Privacy Office closes a breach ticket. They may [[Send back]] a return with a question; it comes back to you, and you are emailed that a ticket is waiting.",
        ],
      },
    ],
  },
  {
    id: "audit-trail",
    title: "The audit trail",
    summary: "The tamper-evident record of everything done on the platform.",
    roles: ["dpo", "admin"],
    blocks: [
      {
        kind: "list",
        items: [
          "[[Audit trail]] can be asked a question: filter by [[Area]], [[Event]], [[Actor role]], [[Record type]], a person ([[About]]) and a period. The address bar keeps the filters, so a question can be bookmarked or shared.",
          "The summary above the table counts entries by area, event, role and day.",
          "Click a row for its details; [[Show raw JSON]] shows exactly what was stored.",
          "[[Verify chain]] checks that no entry has been altered or removed. A [[Chain broken]] result must be reported at once.",
          "[[Export CSV]] downloads the filtered rows with names readable; the export is itself recorded.",
        ],
      },
      {
        kind: "note",
        text: "The trail holds facts and identifiers, never personal words: a reason is recorded as given, not quoted, and addresses are kept only as a keyed hash.",
      },
    ],
  },
  {
    id: "users",
    title: "Staff accounts",
    summary: "Provisioning accounts, invitations, roles and ending access.",
    roles: ["admin", "dpo"],
    blocks: [
      {
        kind: "steps",
        title: "Provision an account (Administrator)",
        items: [
          "Click [[Users]], then [[Provision account]].",
          "Enter [[Full name]] and [[Email]], choose the [[Role]] and [[Person type]]; for a DCO or RCO you may tick the [[Data sources]] they own.",
          "Click [[Create account]]. No password is set here: an email invites the person to choose one, and the account is [[Pending]] until they do.",
        ],
      },
      {
        kind: "list",
        items: [
          "[[Resend invitation]] sends a fresh code to a pending account.",
          "[[Role]] changes a role and signs the person out; [[Reset MFA]] clears their second factor.",
          "[[End staff access]] keeps the person as a data principal but removes every staff power.",
          "The DPO can read the register but not change it.",
        ],
      },
    ],
  },
  {
    id: "delegation",
    title: "Cover while you are away",
    summary: "Hand your work to a colleague in the same role for a period.",
    roles: ["dpo", "dco", "admin"],
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[Delegations]], then [[Delegate my work]].",
          "Choose [[Who takes over]] - colleagues in your role are listed - set [[Until]] and say [[Why]].",
          "Click [[Delegate]]. Your colleague sees it under [[Work delegated to me]] and can act on your records until the end date.",
          "[[End now]] ends it early.",
        ],
      },
      {
        kind: "note",
        text: "Cover applies to the DPO and DCO roles. The Administrator sees every arrangement and can arrange one on someone's behalf.",
      },
    ],
  },
  {
    id: "messages",
    title: "Message wording",
    summary: "The words of every email and SMS the platform sends.",
    roles: ["admin", "dpo"],
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[Message templates]]. They are grouped by what they are about: Sign-in, Accounts, Projects, Consent, Rights, Breach and Staff.",
          "Edit a message's [[Subject]] and [[Body]]. Click a variable chip, such as {full_name}, to insert it where the cursor is.",
          "Click [[Preview]] to see it with sample values, then [[Save]].",
          "[[Reset to default]] brings back the original words.",
          "To copy an email to a team mailbox, put up to five addresses in [[Copy to]] and click [[Save copies]]. Emails that carry a code or a link, or a person's own record, can never be copied, and say so.",
        ],
      },
      {
        kind: "warning",
        text: "A message that uses a variable it does not provide is refused, so no one receives a message with a gap in it.",
      },
    ],
  },
  {
    id: "notifications",
    title: "Notifications",
    summary: "What happened on the records you can see.",
    blocks: [
      {
        kind: "p",
        text: "The bell in the header opens [[Notifications]], which lists recent events on records your role can see - a notice published, a consent withdrawn, an export generated. Each links to the page it is about, and only where your role can open that page.",
      },
    ],
  },
  {
    id: "troubleshooting",
    title: "Troubleshooting",
    summary: "Common questions and what to do.",
    blocks: [
      {
        kind: "faq",
        items: [
          {
            q: "My sign-in code has not arrived.",
            a: "Codes go to your registered work email and last five minutes. Wait a minute, check your junk folder, then use [[Send a new code]].",
          },
          {
            q: "It says my account is locked.",
            a: "Five wrong passwords lock it for 30 minutes. Wait, or use [[Forgotten your password?]] to set a new one.",
          },
          {
            q: "I was sent back to the sign-in page.",
            a: "Sessions end after 30 minutes without activity and after eight hours in any case. Sign in again; the console returns you to the page you were on.",
          },
          {
            q: "A page says “Not part of your account”.",
            a: "That section belongs to another role. Your administrator can tell you whether your role should have it.",
          },
          {
            q: "An export was refused.",
            a: "Read the reason: a processor with no country, a restricted country, or a purpose that does not permit transfer abroad. Fix the processor's country or the purpose, or remove the site.",
          },
          {
            q: "[[Complete]] is greyed out on a rights request.",
            a: "Something asked for has not been carried out with evidence yet - a ticket not returned, or an erasure not confirmed. Finish it, or respond [[Partial]] saying what remains.",
          },
          {
            q: "I see text beginning “SE::” where a name should be.",
            a: "That is encrypted data that failed to open. Report it straight away with the page it appeared on.",
          },
        ],
      },
    ],
  },
  {
    id: "glossary",
    title: "Glossary",
    summary: "The words the platform uses.",
    blocks: [
      {
        kind: "terms",
        items: [
          {
            term: "Data principal",
            meaning: "The person the data is about. Uses the portal.",
          },
          {
            term: "Purpose",
            meaning:
              "A reason for processing, with its lawful basis, data categories, retention and transfer rules.",
          },
          {
            term: "Notice",
            meaning:
              "What people read before consenting. Versioned; frozen once published.",
          },
          {
            term: "Processor",
            meaning:
              "An organisation, or an in-house team, that collects or handles data for you.",
          },
          {
            term: "Site",
            meaning: "A place a project collects at, run by a processor's data source.",
          },
          {
            term: "Consent link",
            meaning: "The link a person opens to read the notice and decide. Expires.",
          },
          {
            term: "Consent record",
            meaning: "The permanent record of one decision, with the exact notice served.",
          },
          {
            term: "Export",
            meaning:
              "The file of people whose consent covers a project; every row is a recorded disclosure.",
          },
          {
            term: "Manifest",
            meaning:
              "A file listing the assets a site collected and whose consent each is under.",
          },
          {
            term: "Holder / ticket",
            meaning:
              "A party that holds a person's data, and the instruction sent to it for a rights request.",
          },
          {
            term: "Legal hold",
            meaning:
              "A DPO record that stops erasure of an asset or a person until released.",
          },
          {
            term: "Audit trail",
            meaning:
              "The append-only, hash-chained log of everything done on the platform.",
          },
        ],
      },
    ],
  },
];
