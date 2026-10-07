/**
 * The consent portal's help manual, for the people whose data is collected.
 *
 * Written against the screens as they are: every `[[Label]]` is the exact
 * words of a button, field or page. When a screen changes its words, the
 * manual changes with it.
 */
import type { HelpSection } from "@/features/help/types";

export const INTRO =
  "How to give, review and withdraw your consent, how to ask what we hold about you and have it corrected or erased, and how to name someone to act for you. It is free, and you can do all of it here.";

export const SECTIONS: HelpSection[] = [
  {
    id: "introduction",
    title: "Introduction",
    summary: "What this portal is for, and your rights.",
    blocks: [
      {
        kind: "p",
        text: "This portal is where you see and manage your consent for the studies that collect data about you, under the Digital Personal Data Protection Act 2023. Every choice you make here is recorded, with the exact notice you were shown.",
      },
      {
        kind: "list",
        title: "Your rights",
        items: [
          "Withdraw your consent at any time - as easily as you gave it.",
          "Ask for a summary of your data, what is done with it and who it was shared with (section 11).",
          "Ask for your data to be corrected, completed or erased (section 12).",
          "Raise a complaint (a grievance, section 13) if you are not satisfied with how we handled something.",
          "Name someone to act for you if you die or cannot act yourself (section 14).",
        ],
      },
    ],
  },
  {
    id: "creating-an-account",
    title: "Creating an account",
    summary: "Your name, a mobile number and your date of birth - confirmed with codes.",
    blocks: [
      {
        kind: "steps",
        items: [
          "On the [[Sign in]] page click [[Create an account]].",
          "Fill in [[Full name]], [[Mobile number]], [[Email address]] (optional) and [[Date of birth]], then click [[Create account]].",
          "On [[Confirm your contacts]], type the code sent to your mobile and, if you gave one, the code sent to your email.",
          "Click [[Confirm and sign in]]. You land on [[My consents]].",
        ],
      },
      {
        kind: "note",
        title: "Why we ask your date of birth",
        text: "The law protects people under 18 differently. We cannot open an account for, or record consent from, anyone under 18.",
      },
      {
        kind: "tip",
        text: "A mobile number or email already registered cannot be used again; sign in with it instead.",
      },
    ],
  },
  {
    id: "signing-in",
    title: "Signing in",
    summary: "No password - a one-time code to your mobile or email.",
    blocks: [
      {
        kind: "steps",
        items: [
          "On the [[Sign in]] page choose [[Mobile]] or [[Email]] under [[Sign in with]].",
          "Type the number or address you registered with and click [[Send me a code]].",
          "Type the six-digit code in [[Six-digit code]] and click [[Verify]].",
        ],
      },
      {
        kind: "list",
        items: [
          "A code works for ten minutes. For your safety we say the same thing whether or not a contact is registered.",
          "You are signed out after 30 minutes without activity. [[Sign out]] is at the bottom of the menu.",
          "If we do not yet have your date of birth, we ask for it before you give a new consent. You can still withdraw a consent or make a request without it.",
        ],
      },
    ],
  },
  {
    id: "consent-link",
    title: "Giving consent through a link",
    summary: "Read the notice, then agree or not to each purpose.",
    blocks: [
      {
        kind: "steps",
        items: [
          "Open the link you were given. The page names the study and the place, with four steps: [[Your details]], [[Confirm]], [[The notice]], [[Done]].",
          "Choose where to send your code under [[Send my code to]], type your mobile or email and click [[Send the code]]. New here? Use [[Create one]] and come back to the link.",
          "Type the code and click [[Verify and continue]].",
          "Read the notice. [[Read this in]] changes the language when there is a choice.",
          "Under [[What are you agreeing to?]], choose [[I agree]] or [[I do not agree]] for every purpose. Nothing is chosen for you.",
          "Click [[Record my choices]] - or [[Decline everything]] to say no to all of it.",
          "[[Your choices are recorded]] shows your reference, and a receipt is sent to you. [[Review your consents]] takes you to them.",
        ],
      },
      {
        kind: "note",
        title: "“This link is not valid”",
        text: "A link that has expired, been replaced or been mistyped shows only this. Ask the person who gave it to you for a current one.",
      },
    ],
  },
  {
    id: "your-consents",
    title: "My consents",
    summary: "What you agreed to, the exact notice you were shown, and the record.",
    blocks: [
      {
        kind: "p",
        text: "[[My consents]] shows one card per study, with its status: [[Consented]] (everything agreed), [[Partial]] (some agreed), [[Declined]] (nothing agreed) or [[Withdrawn]] (you withdrew everything).",
      },
      {
        kind: "list",
        items: [
          "[[See what you agreed to]] lists each purpose, what data it uses and how long it is kept.",
          "[[Show the exact notice I was given]] shows the text as it was when you decided. [[Integrity verified]] means it has not changed since.",
          "[[What was recorded]] lists every change to this consent, oldest first - the same record the Privacy Office sees.",
        ],
      },
    ],
  },
  {
    id: "withdrawing",
    title: "Withdrawing consent",
    summary: "One purpose, or everything - at any time.",
    blocks: [
      {
        kind: "steps",
        items: [
          "On the study's card click [[See what you agreed to]].",
          "Click [[Withdraw just this one]] under a purpose - or [[Withdraw everything]] on the card.",
          "Confirm with [[Withdraw]], or change your mind with [[Keep my consent]].",
          "[[Withdrawal recorded]] confirms it, and a confirmation is sent to you. Anything you still agree to stays in place and can be withdrawn later.",
        ],
      },
      {
        kind: "warning",
        title: "Withdrawing is not erasing",
        text: "Withdrawal stops future processing. It does not by itself delete data already collected - to have that erased, make an erasure request.",
      },
    ],
  },
  {
    id: "shared-with",
    title: "Who your data has been shared with",
    summary: "Every organisation your data went to, and when.",
    blocks: [
      {
        kind: "p",
        text: "On [[My consents]], [[Who your data has been shared with]] lists each organisation that received your data in an export, with the study and the date. It is answered from the record of every disclosure, not from memory.",
      },
    ],
  },
  {
    id: "requests",
    title: "Making a request",
    summary: "Access, erasure or a grievance - with a deadline you can see.",
    blocks: [
      {
        kind: "steps",
        items: [
          "Click [[My requests]], then [[Make a request]].",
          "Choose [[What are you asking for]]: [[Access (s.11)]], [[Erasure (s.12(3))]] or [[Grievance (s.13)]]. A request is about everything we hold about you - every project and every consent.",
          "Say what you want in [[Your request]]. To send documents with it - a proof of who you are, a letter, a screenshot - click [[Add documents]]: PDF, image, text or Word, up to 10 files of 25 MB each.",
          "Click [[Send the request]]. Your documents are sent once the request is recorded; if one is not accepted you are told which, and the request stands.",
          "You are given a reference, [[RR-…]], and the date you will hear by. Signed in, your request counts as verified and the clock starts at once.",
        ],
      },
      {
        kind: "list",
        items: [
          "Each request is a short summary until you click [[Show details]], which shows our response, its clock and each step of its path. A response ready to download is shown either way.",
          "[[Show what was recorded]] lists everything that happened to it.",
          "With several requests, [[All]], [[Open]] and [[Closed]] and the search box above the list narrow it down.",
        ],
      },
    ],
  },
  {
    id: "responses",
    title: "Responses and disputes",
    summary: "Downloading an answer, and what to do if you disagree.",
    blocks: [
      {
        kind: "list",
        items: [
          "When a request is answered you are told, and the card shows [[Our response]]. [[Download the file]] saves it; the download is available for a limited time, so keep a copy.",
          "An answer is [[Complete]] only when everything you asked for was done. Otherwise it is [[Partial]] and says what remains.",
        ],
      },
      {
        kind: "steps",
        title: "Disputing a response",
        items: [
          "Click [[Dispute this response]] on the answered request.",
          "Say what was wrong - late, incomplete, sent the wrong way, or the outcome itself.",
          "Tick [[This is about the Data Protection Officer's own decision]] if it is; it then goes to someone other than the DPO.",
          "Click [[Raise the grievance]]. It is linked to the original request.",
        ],
      },
      {
        kind: "note",
        title: "If you are still not satisfied",
        text: "You may complain to the Data Protection Board of India, independently of us.",
      },
    ],
  },
  {
    id: "without-an-account",
    title: "Making a request without signing in",
    summary: "The public rights page, verified by a code.",
    blocks: [
      {
        kind: "steps",
        items: [
          "Open [[Your rights and how to exercise them]] from the sign-in page.",
          "In [[Make a request]], choose what you are asking for and give the email or mobile you registered with.",
          "Click [[Send the request]]. You are given a reference.",
          "Type the code we send to the contact we already hold for you in [[The code we sent]] and click [[Confirm it is me]].",
        ],
      },
      {
        kind: "note",
        text: "The code always goes to the contact we already hold - never to a new one typed on the form.",
      },
    ],
  },
  {
    id: "nominations",
    title: "Naming someone to act for you",
    summary: "A nominee, for if you die or cannot act yourself.",
    blocks: [
      {
        kind: "steps",
        items: [
          "On [[My requests]], find [[Somebody to act for you]].",
          "Enter [[Their name]], [[Their mobile]] and optionally [[Their email]], and tick [[Which of your rights they may exercise]].",
          "Click [[Nominate]]. It shows [[Waiting for the nominee to accept]]; we send them a link.",
          "When they accept with a code, it shows [[In place]]. Nothing happens until the event you named.",
        ],
      },
      {
        kind: "steps",
        title: "If somebody named you",
        items: [
          "Open the link you were sent, choose where to receive a code, and click [[Send me a code]].",
          "Type the code and click [[Accept the nomination]]. Keep the nomination reference you are shown.",
          "If the time comes, use [[Act on their behalf here]] on the sign-in page, with that reference.",
        ],
      },
    ],
  },
  {
    id: "profile",
    title: "My profile",
    summary: "Your contacts, a second email and your date of birth.",
    blocks: [
      {
        kind: "list",
        items: [
          "[[My profile]], in the account menu under your name, shows your name, contacts, date of birth and status.",
          "Changing your mobile, or adding a second email, is confirmed with a code sent to it; until then it cannot sign you in.",
          "Your date of birth, once given, cannot be changed here. If it is wrong, contact the Privacy Office.",
          "If you are under 18, your profile says so: we cannot record consent from you.",
        ],
      },
    ],
  },
  {
    id: "notifications",
    title: "Notifications",
    summary: "What happened to your records.",
    blocks: [
      {
        kind: "p",
        text: "[[Updates]] lists events about you - a consent recorded, a request received or answered - each linking to your own page about it.",
      },
    ],
  },
  {
    id: "breach-notices",
    title: "If we tell you about a personal data breach",
    summary: "What a breach notice says, where to read it, and whom to ask.",
    blocks: [
      {
        kind: "p",
        text: "If a personal data breach may affect your personal data, we tell you by your registered email or mobile, and the same notice is written to your account. Open it from [[Updates]], or go to [[Personal data breach notices]].",
      },
      {
        kind: "list",
        title: "What each notice tells you",
        items: [
          "[[What happened]]: the breach, in plain words.",
          "[[What it may mean for you]]: the consequences that could follow.",
          "[[What we have done, and are doing]]: the steps taken to limit the harm.",
          "[[What you can do]]: what you can do to protect yourself.",
          "[[Questions]]: whom to ask, and how.",
        ],
      },
      {
        kind: "note",
        text: "A later notice about the same breach is marked as an update, and the earlier ones stay in your account.",
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
            q: "My code has not arrived.",
            a: "Check you typed the contact you registered with. Codes can take a minute and last ten minutes; then ask for a new one. After several requests in an hour you may need to wait before asking again.",
          },
          {
            q: "It says my code is invalid or expired.",
            a: "Use the newest code only - asking for a new one cancels the old. After five wrong tries the code is cancelled; ask for another.",
          },
          {
            q: "The link says “This link is not valid”.",
            a: "It has expired, been replaced, or was mistyped. Ask the person who gave it to you for a current one.",
          },
          {
            q: "I cannot create an account.",
            a: "A contact already registered cannot be used again - sign in with it. Anyone under 18 cannot open an account.",
          },
          {
            q: "I was signed out.",
            a: "For your safety you are signed out after 30 minutes without activity. Sign in again with a new code.",
          },
          {
            q: "I withdrew, but my data is still held.",
            a: "Withdrawal stops future processing. To have data already collected erased, make an erasure request.",
          },
        ],
      },
    ],
  },
  {
    id: "glossary",
    title: "Glossary",
    summary: "The words this portal uses.",
    blocks: [
      {
        kind: "terms",
        items: [
          { term: "Data principal", meaning: "You - the person the data is about." },
          {
            term: "Data fiduciary",
            meaning: "The organisation that decides why and how your data is processed.",
          },
          {
            term: "Purpose",
            meaning:
              "A reason your data is used, with what it uses and how long it is kept.",
          },
          {
            term: "Notice",
            meaning:
              "What you read before you decide. The exact version you saw is kept with your consent.",
          },
          {
            term: "Consent",
            meaning:
              "Your yes or no to each purpose, recorded with the notice and the time.",
          },
          {
            term: "Withdrawal",
            meaning: "Stopping a consent you gave. It stops future processing.",
          },
          {
            term: "Erasure",
            meaning: "Deleting data already collected - asked for with a request.",
          },
          {
            term: "Nominee",
            meaning: "Someone you name to exercise your rights if you die or cannot act.",
          },
          {
            term: "Reference",
            meaning: "The RR-… number of a request. Quote it if you contact us.",
          },
        ],
      },
    ],
  },
];
