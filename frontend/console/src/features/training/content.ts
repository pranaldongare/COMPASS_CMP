/**
 * Training: each role's work, step by step (2026-11-24).
 *
 * Help answers "how do I…?" for whoever asks, signed in or not. Training is
 * the other half: a short course per role, taken once signed in, that walks
 * through the work in the order it runs and ends with a few questions. The
 * words follow the Help manual's - the same buttons, in [[double brackets]] -
 * so the two cannot teach different things; when a screen changes, both move.
 *
 * A module names the roles it is for. `ALL_STAFF` modules are everyone's.
 * A step may name the console page it happens on (`where`, a nav key); the
 * page shows an "Open" link only when the reader's role reaches that page.
 */
import type { NavKey } from "@/lib/permissions";
import type { Role } from "@/types";

export interface TrainingStep {
  title: string;
  /** What to do, in the Help manual's words; `[[Label]]` is a button or field. */
  body: string;
  /** Things to do, in order, when the step has several. */
  actions?: string[];
  /** The console page this happens on. */
  where?: NavKey;
  /** A point people get wrong. */
  tip?: string;
}

export interface CheckQuestion {
  question: string;
  options: string[];
  /** Index into `options`. */
  answer: number;
  /** Shown once answered, right or wrong. */
  why: string;
}

export interface TrainingModule {
  id: string;
  title: string;
  summary: string;
  roles: readonly Role[];
  minutes: number;
  steps: TrainingStep[];
  check: CheckQuestion[];
}

export const ALL_STAFF: readonly Role[] = [
  "dpo",
  "legal",
  "admin",
  "rnd_user",
  "dco_admin",
  "dco",
  "rco",
  "hr_user",
  "management",
  "breach_holder",
];

const COLLECTORS: readonly Role[] = ["dco_admin", "dco", "rco"];

export const MODULES: TrainingModule[] = [
  /* ============================================================ everyone */
  {
    id: "getting-started",
    title: "Getting started",
    summary:
      "Signing in with a second factor, finding your work, and where your tasks arrive.",
    roles: ALL_STAFF,
    minutes: 5,
    steps: [
      {
        title: "Sign in with two steps",
        body: "Type your work email or username and your password, then [[Sign in]]. A six-digit code is emailed to you: type it in [[6-digit code]] and click [[Verify and continue]].",
        tip: "A code works for five minutes. If it went wrong, [[Send a new code]] - or [[Forgotten your password?]] on the same page if the password is the problem.",
      },
      {
        title: "Find your daily work",
        body: "The first group in the sidebar is your role's daily work, in the order it runs. Everything else your role may open follows in its usual group. Pages you cannot open are not shown at all.",
      },
      {
        title: "Your tasks",
        body: "[[My tasks]] holds the tickets addressed to you: a rights request's holder that is one of our own teams is answered here, by whoever that team named, whatever their role. The sidebar shows a count of tickets with something unread.",
        where: "tickets",
      },
      {
        title: "Notifications and your profile",
        body: "The bell at the top right shows what happened to your work. Your name, top right, opens [[My profile]]: your contacts and the sessions signed in as you, any of which you can end.",
        where: "profile",
      },
      {
        title: "Help is always there",
        body: "[[Need help?]] opens the manual for your role, task by task. Training is the course; Help is the reference you come back to.",
      },
    ],
    check: [
      {
        question: "Your sign-in code has expired. What do you do?",
        options: [
          "Ask the administrator to reset your account",
          "Click [[Send a new code]] on the same page",
          "Sign in again from another browser",
        ],
        answer: 1,
        why: "A new code is one click away; the old one stops working the moment the new one is sent.",
      },
      {
        question: "Where do tickets addressed to you arrive?",
        options: ["In your email only", "In [[My tasks]]", "On the dashboard's chart"],
        answer: 1,
        why: "Every member of staff has [[My tasks]]; an email tells you something arrived, the ticket itself is answered in the console.",
      },
    ],
  },
  {
    id: "handling-personal-data",
    title: "Handling personal data safely",
    summary: "What the platform protects for you, and what only you can protect.",
    roles: ALL_STAFF,
    minutes: 4,
    steps: [
      {
        title: "Everything is on the trail",
        body: "Every record opened, every download and every change is written to a tamper-evident audit trail, with who did it and when. Work as if your actions will be read - they can be.",
      },
      {
        title: "Downloads are disclosures",
        body: "An export holds names and contacts, and each row is recorded as a disclosure. Download only what the task needs, keep it on approved storage, and delete it when the task is done.",
        tip: "Downloading the same export again gives the same file and creates no new export.",
      },
      {
        title: "Never share a code or a link",
        body: "A sign-in code proves it is you; a consent link or a holder's link is a key to somebody's record. Nobody from the Privacy Office will ever ask you for one.",
      },
      {
        title: "Small numbers stay hidden",
        body: "Figures about fewer people than the threshold show as [[< 5]], never as a number. Do not work out who they are from other figures; that is the point of hiding them.",
      },
    ],
    check: [
      {
        question:
          "A colleague asks you to email them an export so they can 'take a look'. What is right?",
        options: [
          "Email it - they are staff",
          "Send only what their task needs, through approved storage, and only if their role allows it",
          "Paste the rows into a chat",
        ],
        answer: 1,
        why: "Each row of an export is a disclosure on the record. Passing it on widens it, so only what the task needs, and only to someone entitled.",
      },
    ],
  },
  {
    id: "answering-a-ticket",
    title: "Answering a ticket",
    summary: "When the Privacy Office asks your team what it holds, or asks you to act.",
    roles: ALL_STAFF,
    minutes: 4,
    steps: [
      {
        title: "Open it from My tasks",
        body: "Rights tickets are in three groups: [[To do]], [[Waiting on the Privacy Office]] and [[Done]]. Click [[Answer]] on a ticket; it shows what the platform already knows and opens on [[Answer the ticket]].",
        where: "tickets",
      },
      {
        title: "Ask before you answer, if you must",
        body: "Open [[Messages]], write your question, attach a file if needed and click [[Send message]]. A message does not answer the ticket.",
      },
      {
        title: "Submit the answer",
        body: "When the work is done, choose what was done, say what you hold and did, attach any proof, and click [[Submit answer]]. That is what answers the ticket.",
        tip: "Need longer? [[Change the date]] beside [[Answer by]] with a reason; the Privacy Office is told.",
      },
      {
        title: "Review",
        body: "The Privacy Office reads it. Accepted, it moves to [[Done]]; sent back, it returns to [[To do]] with what is missing and a new date. While a ticket is overdue you are reminded by email every day.",
      },
    ],
    check: [
      {
        question: "You sent a message on a ticket. Is the ticket answered?",
        options: ["Yes", "No - only [[Submit answer]] answers it"],
        answer: 1,
        why: "Messages are for questions; the answer is a separate act, with what was done and any proof.",
      },
    ],
  },

  /* ======================================================== R&D User */
  {
    id: "register-a-project",
    title: "Registering a project and its notice",
    summary: "From an idea to a project the DPO can approve.",
    roles: ["rnd_user", "dpo"],
    minutes: 8,
    steps: [
      {
        title: "Register the project",
        body: "Click [[Projects]], then [[Register a project]]. Enter the [[Project name]] - what a person would recognise it as - and its [[Description]]. Under [[Who will collect]] tick every processor that will collect. Click [[Register project]]; it starts [[In Draft]].",
        where: "projects",
      },
      {
        title: "Bring the notice",
        body: "On the project open [[Setup]]. In the [[Notices]] card either [[Upload a notice document]] - the filled DPDP template, checked before anything is written - or [[Use a notice template]] with the template ID the Privacy Office gives you.",
        tip: "[[Check the document]] writes nothing: it shows the purposes and data it found, and any warnings, first.",
      },
      {
        title: "Upload the approvals",
        body: "Click [[Upload approval]]: choose the [[Type]] (security, legal, Knox or other), the [[Reference number]], the [[Approved on]] date and attach the [[Proof document]].",
        tip: "An approval without a proof file does not count.",
      },
      {
        title: "Submit",
        body: "In [[What happens next]], click [[Pending Approval]]. The DPO is told. The card always says the one next move, or everything still missing.",
      },
      {
        title: "After approval",
        body: "A published notice is frozen. A correction, or a new collection site after publication, is a new version of the notice. Consents already given keep the notice they were given under.",
      },
    ],
    check: [
      {
        question:
          "The DPO approved your project, and you need to fix a typo in the notice. What happens?",
        options: [
          "Edit the published notice",
          "Make a new version, which supersedes the old one",
          "Delete the project and start again",
        ],
        answer: 1,
        why: "A published notice can never be edited: consent is matched to the exact text people saw.",
      },
      {
        question: "Which approval counts toward submission?",
        options: ["One with a reference number", "One with a proof document attached"],
        answer: 1,
        why: "The proof file is what makes an approval count.",
      },
    ],
  },

  /* ============================================================== DPO */
  {
    id: "approve-a-project",
    title: "Reviewing and approving a project",
    summary: "Purposes active, each language approved, then publish.",
    roles: ["dpo"],
    minutes: 6,
    steps: [
      {
        title: "Open what is waiting",
        body: "Open the project from [[Needs attention]] › [[Projects pending approval]] on your dashboard, or from [[Approvals]].",
        where: "approvals",
      },
      {
        title: "Clear what blocks it",
        body: "[[What happens next]] lists what still blocks approval, with links: activate each purpose the notice carries, and legally approve each language.",
        where: "purposes",
      },
      {
        title: "Approve each language",
        body: "On the notice, [[Edit English text]] to correct the wording, [[Add language]] for another, then [[Approve]] each. The approved text is hashed; consent is matched against it.",
      },
      {
        title: "Approve, or send back",
        body: "Back on the project click [[Approved]], add an optional note and [[Confirm]]: the notice is published and frozen. To send it back click [[In Draft]] - a reason is required and kept in the history.",
      },
    ],
    check: [
      {
        question: "Can a draft purpose appear on a published notice?",
        options: ["Yes", "No - only an active purpose can"],
        answer: 1,
        why: "Activate each purpose first; [[What happens next]] links to every one still in draft.",
      },
    ],
  },
  {
    id: "rights-requests",
    title: "Answering a rights request",
    summary: "Verify, classify, ask the holders, review, respond - on the clock.",
    roles: ["dpo", "legal"],
    minutes: 10,
    steps: [
      {
        title: "Take it, if it is in the shared intake",
        body: "On [[Rights requests]] choose [[In the shared intake]] under [[Office]], verify who it is, then [[Claim]]. Work cannot start until one office has claimed it; one that belongs to the other office goes with [[Transfer to the Legal office]] (or the DPO office) and a reason.",
        where: "requests",
      },
      {
        title: "Classify",
        body: "Answer [[A valid … request?]] and click [[Confirm classification]]. For an erasure confirm [[They mean erasure]] - erasure is not withdrawal. Not a rights request? [[Refuse this request]] with the reason; the person is told why, with the grievance route.",
      },
      {
        title: "Start, and ask the holders",
        body: "Under [[Next step]] click [[In progress]]: the platform finds who holds the person's data by itself. For each holder [[Confirm who answers]], then [[Send tickets]].",
        tip: "Every holder needs an email address - [[Add their email]] where it says [[No email - add one before sending]].",
      },
      {
        title: "Review each answer",
        body: "An answered holder shows [[Answered - review]]. Read it, then [[Accept the answer]] or [[Send back]] with what is missing. Only accepted answers count toward closing.",
      },
      {
        title: "Erasure, if asked",
        body: "On the [[DataVault]] card click [[Check in DataVault]], then [[Erase in DataVault]]; a pop-up says how many assets go first. [[Check status]] asks again later; nothing asks by itself.",
      },
      {
        title: "Respond and close",
        body: "Write [[The response]], [[Attach files]] if needed, choose the outcome and click [[Release and close]]. The person reads it on the portal.",
      },
    ],
    check: [
      {
        question:
          "A person asks to 'remove my data'. Before erasing, what must you confirm?",
        options: [
          "That they mean erasure, not withdrawal of consent",
          "That their consent has expired",
          "Nothing - erase at once",
        ],
        answer: 0,
        why: "Erasure and withdrawal are different rights with different results; [[They mean erasure]] records which one this is.",
      },
      {
        question: "A holder sent a message but no answer. Does it count toward closing?",
        options: ["Yes", "No - only an accepted answer counts"],
        answer: 1,
        why: "Accept or send back each answer; messages are conversation, not answers.",
      },
    ],
  },
  {
    id: "breach-response",
    title: "Responding to a personal data breach",
    summary:
      "Incident to close: validation, every duty's clock, the reports and the people affected.",
    roles: ["dpo", "legal"],
    minutes: 12,
    steps: [
      {
        title: "Log the incident",
        body: "[[Log an incident]] from your dashboard or [[Breaches]], with the time it was [[First noticed]] - not now. Answer what is known so far; [[Is it a cyber attack?]] Yes starts the CERT-In duty at once.",
        where: "breaches",
      },
      {
        title: "CERT-In, if it may be reportable",
        body: "[[Mark reportable to CERT-In]]: six hours from first noticed. A mistake? [[Not reportable to CERT-In]] with a reason sets the duty aside.",
      },
      {
        title: "Validate",
        body: "Record the [[Validation]]: is it a personal data breach under s.2(u)? The first yes gives it a BR reference, starts the DPDP Board and principals duties, and gives you 30 minutes to tell the organisation's board.",
      },
      {
        title: "Tell the organisation's board",
        body: "Click [[Notify Organization Board]], change the drafted report as needed, check [[Who it goes to]] and [[Send to the board]]. The duty is done once the mail lands with at least one address.",
      },
      {
        title: "Draft, finalise and record each report",
        body: "On [[Reports]], [[Draft it]] for each report that applies, then [[Finalise and tell the board]]. Send it yourself through the regulator's own channel, then [[Record as sent]] with the proof - that completes the duty.",
        tip: "The platform never sends anything to the DPDP Board or CERT-In. A person does, and keeps the proof here.",
      },
      {
        title: "Tell the people affected",
        body: "On [[People & notices]] [[Add people]], [[Draft the notice]], [[Approve]] it, then send it to all of them in one click.",
      },
      {
        title: "Close",
        body: "Close it once it is validated, every duty is done or not applicable and no ticket is open. The page lists what is still in the way.",
      },
    ],
    check: [
      {
        question: "Who sends the initial intimation to the DPDP Board?",
        options: [
          "The platform, automatically",
          "A person, through the regulator's own channel, then records it as sent here",
        ],
        answer: 1,
        why: "The platform drafts and tracks; it never writes to a regulator.",
      },
      {
        question: "When does the 30-minute clock to tell the organisation's board start?",
        options: ["When the incident is logged", "At the first yes on validation"],
        answer: 1,
        why: "Validation is what makes it a breach; the duties start there.",
      },
    ],
  },
  {
    id: "registry-and-wording",
    title: "Purposes, processors and message wording",
    summary:
      "The registry every notice and export rests on, and the words the platform sends.",
    roles: ["dpo", "admin", "legal"],
    minutes: 6,
    steps: [
      {
        title: "Create and activate a purpose",
        body: "[[Purposes]] › [[New purpose]]: name, description, data collected, lawful basis, retention and erasure trigger. [[Create purpose]] makes a [[Draft]]; [[Activate]] makes it usable on a notice.",
        where: "purposes",
        tip: "Tick [[Transfer outside India is permitted for this purpose]] only if it is - exports abroad are refused otherwise.",
      },
      {
        title: "Register a processor",
        body: "[[Processors]] › [[Register processor]]: legal name, type, contract reference, country and when security was confirmed. Tick [[We collect this ourselves]] for an in-house team.",
        where: "processors",
      },
      {
        title: "Restrict a country (DPO)",
        body: "Under [[Restricted countries (s.16)]] give the country and the Government's notification, then [[Restrict]]. Exports to a processor there are refused from then on.",
      },
      {
        title: "Edit what the platform sends",
        body: "[[Message templates]]: find a message, edit its [[Subject]] and [[Body]] - click a variable chip to insert it - [[Preview]] and [[Save]]. [[Reset to default]] brings the original back.",
        where: "messages",
      },
    ],
    check: [
      {
        question: "A purpose is created but not activated. Can a notice use it?",
        options: ["Yes", "No"],
        answer: 1,
        why: "Only an active purpose can appear on a notice.",
      },
    ],
  },

  /* ===================================================== collection */
  {
    id: "sites-and-links",
    title: "Collection sites and consent links",
    summary: "Where a project collects, and the link people open to consent.",
    roles: [...COLLECTORS, "rnd_user"],
    minutes: 6,
    steps: [
      {
        title: "Add a site",
        body: "Third-party collection: the DCO Admin opens the approved project; in-house: the project's R&D User. On the project's [[Consent]] tab click [[Add site]], choose the [[Data source]] and type the [[Location]], then [[Add collection site]].",
        where: "sites",
      },
      {
        title: "Create a consent link",
        body: "The DCO or RCO running the site clicks [[Create link]] on its row, sets when it expires - required - and how many times it may be used, and clicks [[Create link]].",
        where: "links",
      },
      {
        title: "Share it",
        body: "Copy the link from [[Copy this now]]. It opens on the portal, not the console. Share it with the people you collect from.",
        tip: "[[Replace link]] issues a new link; the old one stops working at once.",
      },
      {
        title: "Watch the consents",
        body: "[[Consents]] lists each person once, at their current decision: [[Consented]], [[Partial]], [[Declined]] or [[Withdrawn]]. You see only the sites you run.",
        where: "consents",
      },
    ],
    check: [
      {
        question: "A link was shared by mistake with the wrong group. What do you do?",
        options: [
          "Nothing - it expires eventually",
          "[[Replace link]] - the old one stops at once",
        ],
        answer: 1,
        why: "Replacing is immediate; an expiry date is no protection against a link already out.",
      },
    ],
  },
  {
    id: "imports-and-exports",
    title: "Imports and exports",
    summary:
      "Bringing collected data in against consent, and sending lists out as disclosures.",
    roles: [...COLLECTORS, "dpo"],
    minutes: 6,
    steps: [
      {
        title: "Import a manifest",
        body: "[[Imports]] › [[Import a manifest]]. [[Download the manifest template]] and fill it in; [[What the file must contain]] explains each column.",
        where: "imports",
      },
      {
        title: "Validate first",
        body: "Choose the [[Data source]] and [[Project]], choose the file and click [[Validate only]]: it saves nothing, and lists problems by row and column. When it says [[Manifest is valid]], click [[Import]].",
      },
      {
        title: "Generate an export",
        body: "On an approved project open [[Collections & exchanges]] and [[Generate export]]. Read the warning - each row is a disclosure - then [[Generate the export]] and download it from [[Exports]].",
        where: "exports",
      },
    ],
    check: [
      {
        question: "What does [[Validate only]] write to the record?",
        options: ["The valid rows", "Nothing"],
        answer: 1,
        why: "It checks the whole file and saves nothing; [[Import]] is the step that writes.",
      },
    ],
  },
  {
    id: "routing-third-party-work",
    title: "Routing third-party work (DCO Admin)",
    summary:
      "Sources with an owner, sites on approved projects, and your tickets with DataVault.",
    roles: ["dco_admin"],
    minutes: 5,
    steps: [
      {
        title: "Give every source an owner",
        body: "[[Data sources]]: tick [[Nobody accountable]] to find sources without one, then the row's [[⋯]] › [[Assign]] - a DCO for a third party's source.",
        where: "sources",
      },
      {
        title: "Add sites to approved projects",
        body: "Projects naming a third party come to you once approved. Add each site on the project's [[Consent]] tab; the source's owner runs it.",
        where: "projects",
      },
      {
        title: "Answer rights tickets with DataVault",
        body: "On a ticket for a project, [[Held in DataVault for this project]] lists the person's assets and where each is kept. Say what you hold and did, then [[Submit answer]].",
        where: "tickets",
      },
    ],
    check: [
      {
        question: "Who runs a collection site once you add it?",
        options: ["You", "The owner of the data source it uses"],
        answer: 1,
        why: "[[Who runs it]] changes that for one project only.",
      },
    ],
  },

  /* ============================================================ admin */
  {
    id: "staff-accounts",
    title: "Staff accounts and cover",
    summary: "Provisioning, roles and offices, and arranging cover for somebody away.",
    roles: ["admin"],
    minutes: 6,
    steps: [
      {
        title: "Provision an account",
        body: "[[Users]] › [[Provision account]]: full name, email, [[Role]] and [[Person type]]. A DCO or RCO also gets the processors they collect for. [[Create account]] sends an invitation; the account is [[Pending]] until they set a password.",
        where: "users",
      },
      {
        title: "Choose the office",
        body: "Every role but the administrator and management works in one office and sees only its records. Leave the office empty for an administrator or management - the server refuses one.",
      },
      {
        title: "Change a role",
        body: "Changing a role ends every session the person holds: a session carrying the old role's permissions must not survive. Give a reason; it is on the trail.",
      },
      {
        title: "Arrange cover",
        body: "[[Delegations]] › [[Arrange cover for someone]]: whose work, who takes over, until when and why. Both are emailed.",
        where: "delegate",
      },
    ],
    check: [
      {
        question: "You provision a Management account. Which office do you choose?",
        options: ["The R&D office", "The HR office", "None - management works across both"],
        answer: 2,
        why: "Management reads both offices combined or one at a time; the server refuses an office for it.",
      },
    ],
  },
  {
    id: "platform-settings-and-health",
    title: "Settings, health and the audit trail",
    summary: "Where the platform is configured, and how you know it is working.",
    roles: ["admin"],
    minutes: 6,
    steps: [
      {
        title: "Grievances about the DPO",
        body: "[[Grievances about the DPO]] holds the disputes of the DPO's own decisions, which the DPO must not review. Decide each as upheld or not upheld.",
        where: "requests",
      },
      {
        title: "Breach settings",
        body: "[[Breach settings]] keeps the organisation's board list, who is told of a public report, and escalation to management. A [[Mandatory]] address cannot be left out of a report.",
        where: "breach-settings",
      },
      {
        title: "Who may sign in: the employee check",
        body: "[[Employee check]]: VerifyEmail's address and key, the organisation's email domains, and the switch. Staff on those domains are checked at console sign-in - a former employee is refused, and so is everyone on them while VerifyEmail cannot be reached; you never are. [[Check an address]] tries the connection.",
        where: "employee-check",
        tip: "[[Let staff on other domains sign in to the console]] is for testing. Switch it off before production.",
      },
      {
        title: "DataVault and the portal address",
        body: "[[DataVault connection]] is where DataVault is reached; [[Portal address]] is what every link to the portal starts with.",
        where: "datavault",
      },
      {
        title: "Health and audit reports",
        body: "On [[Analytics]], the health tab shows sign-in codes, failed sign-ins, the queues and integrity checks; the audit reports are the trail's own rows in seven ready-made sets.",
        where: "analytics",
      },
      {
        title: "Targets and the small-number threshold",
        body: "Under Analytics › Settings you set each figure's target and amber line, and the threshold below which counts of people are withheld.",
        tip: "The threshold starts at 1 for testing. Set it (5 is usual) before figures about small groups are shared.",
      },
    ],
    check: [
      {
        question: "VerifyEmail cannot be reached. Who can still sign in to the console?",
        options: [
          "Nobody",
          "The administrator, and staff on domains that are not the organisation's while that is allowed",
          "Everybody - the check is skipped",
        ],
        answer: 1,
        why: "Staff on the organisation's domains are refused without an answer; the administrator is never checked, so the platform can always be put right.",
      },
      {
        question: "A grievance disputes the DPO's own decision. Who decides it?",
        options: ["The DPO", "The administrator"],
        answer: 1,
        why: "Nobody reviews their own decision.",
      },
    ],
  },

  /* ======================================================= Legal / HR */
  {
    id: "hr-registry",
    title: "The Legal office's HR registry",
    summary: "Categories, their processors, and the notice templates activities use.",
    roles: ["legal"],
    minutes: 7,
    steps: [
      {
        title: "Create a category",
        body: "[[HR categories]] › [[New HR category]]: a code, a name, a description, and [[Who its links reach]] - employees, candidates, vendors or visitors.",
        where: "hr-categories",
      },
      {
        title: "Name its processors",
        body: "On the category, [[Add a processor]] for each system or vendor that holds its data, with what it is to the category and who answers for it, then [[Save processors]]. A rights request finds them as holders.",
      },
      {
        title: "Write the template",
        body: "On [[Notice templates]], under the category: [[Open version 1]], write the [[Locked text]] with its two slots, add the [[Purposes an activity may choose]] (tick [[Mandatory]] where every activity must ask), [[Preview]], then [[Approve]].",
        where: "templates",
        tip: "An approved version never changes; [[Retire]] stops new activities using it.",
      },
    ],
    check: [
      {
        question: "Can an HR PoC untick a mandatory purpose on their activity?",
        options: ["Yes", "No"],
        answer: 1,
        why: "Mandatory purposes are ticked and fixed: Legal decided every activity must ask them.",
      },
    ],
  },
  {
    id: "hr-activity",
    title: "Running an HR activity",
    summary: "An activity, its link, and the consents it gathers.",
    roles: ["hr_user"],
    minutes: 5,
    steps: [
      {
        title: "Create the activity",
        body: "[[New activity]] on your dashboard or on [[HR activities]]. Choose the [[Category]] and [[Template version]]; its mandatory purposes are already ticked. Tick any others you need.",
        where: "hr-activities",
      },
      {
        title: "Describe it and set the link",
        body: "Give the [[Activity name]] and [[Description]] within the length Legal set. Choose [[Who signs in through the link]] and the date [[The link works until]], then [[Create the activity]].",
      },
      {
        title: "Share the link",
        body: "[[The activity is live]] shows its link. People sign in with a one-time code by text or email and give or refuse consent on the portal.",
        where: "links",
      },
      {
        title: "Follow the consents",
        body: "[[Open the activity]] for its consents, or [[Consents]] for all of yours.",
        where: "consents",
      },
    ],
    check: [
      {
        question: "Where do people give consent to your activity?",
        options: ["In the console", "On the portal, through the activity's link"],
        answer: 1,
        why: "The console is staff only; people consent on the portal.",
      },
    ],
  },

  /* ======================================================= management */
  {
    id: "reading-the-scorecard",
    title: "Reading the scorecard",
    summary: "Periods, offices, targets and what a figure means.",
    roles: ["management", "dpo", "legal"],
    minutes: 5,
    steps: [
      {
        title: "Choose the period and the office",
        body: "On [[Analytics]] choose a period - a month, a quarter or the financial year (April-March) - and both offices, or one. Each figure compares with the period before.",
        where: "analytics",
      },
      {
        title: "Read the status",
        body: "Each figure with a target says [[On target]], [[Watch]] (between the amber line and the target) or [[Off target]], with an icon as well as a colour.",
      },
      {
        title: "Know what a figure counts",
        body: "Every figure has its definition: what is counted, out of what, and how. Figures are counted live from the record, so last month's may change if a request is closed late.",
      },
      {
        title: "Small numbers",
        body: "A count of fewer people than the threshold shows as [[< 5]]: it is withheld, not zero.",
      },
    ],
    check: [
      {
        question: "A figure shows [[< 5]]. What does it mean?",
        options: [
          "Nothing happened",
          "Some, but too few to show without risk of identifying people",
        ],
        answer: 1,
        why: "Withheld is not zero; the platform never shows a small group as a number.",
      },
    ],
  },
  {
    id: "reports-and-schedules",
    title: "Reports and board packs",
    summary: "Making a report, keeping it, and having it mailed on a schedule.",
    roles: ["management", "dpo", "legal", "admin"],
    minutes: 4,
    steps: [
      {
        title: "Make a report",
        body: "On [[Analytics]] › [[Reports]], [[New report]]: choose the kind, the period and PDF, Excel or CSV. It shows [[Being made]] until it is ready.",
        where: "analytics",
      },
      {
        title: "Download or delete",
        body: "Every report is kept until somebody deletes it. Each download and deletion is on the audit trail.",
      },
      {
        title: "Schedule it",
        body: "[[New schedule]] makes a report weekly, monthly or quarterly at 06:00 India time, for the period just ended, and emails it to the roles you choose.",
      },
    ],
    check: [
      {
        question: "Does a report change if the record changes after it was made?",
        options: ["Yes", "No - its file is frozen, with its hash"],
        answer: 1,
        why: "A report records what was counted when it was made; make a new one for today's figures.",
      },
    ],
  },

  /* ================================================== temporary login */
  {
    id: "temporary-holder",
    title: "Answering as a temporary ticket holder",
    summary: "You were given a login for one breach or request. Here is all of it.",
    roles: ["breach_holder"],
    minutes: 4,
    steps: [
      {
        title: "Set your password and sign in",
        body: "Open the link in the Privacy Office's email, type the [[Code]], choose a [[New password]] of at least 12 characters and [[Set the new password]]. Sign in with your work email; a six-digit code follows.",
      },
      {
        title: "Find your ticket",
        body: "You land on [[My tasks]]: a breach ticket at the top, a ticket on a rights request under [[To do]].",
        where: "tickets",
      },
      {
        title: "Bring in a colleague",
        body: "While your ticket is open, [[Add a colleague]]: their name, work email on one of the organisation's domains and a note of what you ask of them. They get their own ticket.",
      },
      {
        title: "Answer",
        body: "Say what you did and attach proof, then submit. The Privacy Office closes it, or sends it back with what is missing.",
      },
    ],
    check: [
      {
        question: "Your colleague also holds some of the data. What do you do?",
        options: ["Forward them your login", "[[Add a colleague]] on the ticket"],
        answer: 1,
        why: "A login is yours alone; your colleague gets their own ticket, and the Privacy Office sees that you added them.",
      },
    ],
  },
  /* ========================================================== retention */
  {
    id: "retention-reviews",
    title: "Retention reviews",
    summary:
      "Consents that run out and data that must go: asking the ones responsible, accepting their answers, and the certificate.",
    roles: ["dpo", "legal"],
    minutes: 8,
    steps: [
      {
        title: "Read the register",
        body: "[[Retention]] holds two kinds of review: [[Consent validity]] - consents about to run out - and [[Data retention]] - data whose time to be kept has passed since the consent ended. One review per project, purpose and month, with its people counted. The tiles filter the list.",
        where: "retention",
        tip: "A review is not a rights request or a breach: it has its own register and its own answers.",
      },
      {
        title: "Who is asked",
        body: "Once a review falls due, its owner (the DCO Admin, or the HR PoC for an HR activity) and every processor holding the data are asked. A processor with no console login gets an emailed link that opens with a code.",
        where: "retention",
      },
      {
        title: "Accept, or send back",
        body: "Open the review. For each answer, [[Accept]] it or [[Send back]] saying what is missing. Anonymising instead of erasing, and keeping, each come with a reason; keeping comes with a date to look again.",
        actions: [
          "Read the answer and its reason.",
          "[[Accept]] it, or [[Send back]] with what is missing.",
          "[[Not needed]] sets aside an action nobody need answer.",
        ],
        where: "retention",
        tip: "Accepting a validity owner's yes sends every person in the review the project's consent link at once.",
      },
      {
        title: "Close it, and keep the certificate",
        body: "[[Close the review]] once every answer is accepted or set aside. The [[Certificate]] - PDF or CSV - shows the consents by number, every answer with its reason, who accepted it and who closed it.",
        where: "retention",
      },
      {
        title: "The settings",
        body: "Under [[Settings]] on the same page: when owners are reminded, how many hours before an erasure people are told, how long the ones asked have to answer, and when a late answer reaches you.",
        where: "retention",
      },
    ],
    check: [
      {
        question: "When does the time to keep data start?",
        options: [
          "When the consent was given",
          "When the consent ended: withdrawn, or run out",
          "When the project closed",
        ],
        answer: 1,
        why: "Retention is counted from the consent's end, whether it was withdrawn or ran out.",
      },
      {
        question: "A processor answers that it kept the data. What must the answer carry?",
        options: [
          "Nothing more",
          "A reason, and a date it will be looked at again",
          "The names of the people",
        ],
        answer: 1,
        why: "Keeping data past its retention needs a reason and a date; people are never named.",
      },
      {
        question: "When can a review be closed?",
        options: [
          "Any time",
          "When every answer is accepted or set aside",
          "Only after the night has run",
        ],
        answer: 1,
        why: "A review closes only when nothing is left waiting.",
      },
    ],
  },
  {
    id: "retention-answering",
    title: "Answering a retention review",
    summary:
      "What to do when the Privacy Office asks about data whose consent or retention has run out.",
    roles: ["dco_admin", "hr_user", "rnd_user", "dco", "rco"],
    minutes: 4,
    steps: [
      {
        title: "Find what you are asked",
        body: "[[Retention actions]] lists each review you are asked about, with the date to answer by. An email tells you when one arrives.",
        where: "retention-actions",
      },
      {
        title: "Consents running out",
        body: "A [[Consent validity]] review asks whether the people should be asked to consent again. Choose [[Yes, invite them]] only if the project still needs their data, and [[Send the answer]].",
        where: "retention-actions",
      },
      {
        title: "Data that must go",
        body: "A [[Data retention]] review asks what was done with the data wherever you hold it: [[Erased]], [[Anonymised]], [[Kept]] or [[Not held]]. Anonymising and keeping each need a reason; keeping needs a date to look again.",
        where: "retention-actions",
        tip: "Attach proof in [[Proof (optional)]] if you have it - a deletion log, a screenshot, a letter. If your answer is sent back, the reason is shown above the form: answer again.",
      },
    ],
    check: [
      {
        question: "You anonymised the data instead of erasing it. What else must you give?",
        options: ["Nothing", "The reason it was not erased", "The people's names"],
        answer: 1,
        why: "Anonymising instead of erasing needs its reason on the record.",
      },
    ],
  },
];

/** The modules a role takes, everyone's first. */
export function modulesFor(role: Role | undefined): TrainingModule[] {
  if (!role) return [];
  return MODULES.filter((m) => m.roles.includes(role));
}

export function moduleById(id: string): TrainingModule | undefined {
  return MODULES.find((m) => m.id === id);
}
