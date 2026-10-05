# Personal data breaches

What the platform does when personal data it is responsible for is breached:
section 8(6) of the Act, Rule 7 of the DPDP Rules, and the CERT-In Directions
of 2022. The decisions behind the shape are
[ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md)
and [ADR 0022](../decisions/0022-an-incident-first-and-a-breach-on-a-yes.md),
which puts the incident first; the code is `cmp.domain.breach`, the routes are
under `/breaches`, and the console's pages are **Breaches** in the DPO's menu,
headed **Incidents and personal data breaches**.

In order: an **incident** is logged as it was noticed; the DPO team
**validates** whether it is a personal data breach under s.2(u); the first
*yes* **records the breach** and starts the DPDP duties. CERT-In runs from the
moment of noticing whatever validation says.

## Where the platform ends

The platform is the **system of record**. It records the breach, tracks every
duty's clock, and holds the evidence that each duty was done. **People**
contain the breach, preserve forensic evidence, decide whether it is a personal
data breach, tell the organisation's board, and submit to the Board and to
CERT-In through those bodies' own channels. The platform never contains
anything, never talks to a regulator and never reports to the organisation's
board: a submission or report is recorded after a person has made it, with the
reference the regulator returned or whom the board was told through.

## Who can see it

The DPO, and nobody else. The resource is `breach`, and its guard answers
every other role **404**, not 403 - on the register, on a breach that exists,
and on a write alike - so that a breach being handled is not itself disclosed
to a colleague walking uuids ([ADR 0004](../decisions/0004-scope-in-the-where-clause.md)).
The administrator, who reads the audit trail, sees that breach events occurred
and their reference (`Incident INC-2026-0001`, then `Breach BR-2026-0001
(INC-2026-0001)` once recorded), never a title or a reason, and cannot follow
the link.

## Logging an incident

**Breaches → Log an incident.** Three things are asked for, and every time is
typed in, never filled with "now":

| Field | Means | Anchors |
|---|---|---|
| First noticed (`detected_at`) | When the event was first noticed | CERT-In's six hours |
| Began (`began_at`) | When it started, if known. An assessment may revise it | the timing in 7(1)(a), 7(2)(a) |
| Where it occurred | The platform's own database, a processor, a data source, or elsewhere (in words) | 7(2)(a); S3-02 derives who was touched from it |

An incident logged five hours after it was noticed has one hour of CERT-In time
left, and the register says so. A time in the future is refused, and so is a
start after detection.

The incident gets a reference, `INC-<year>-<n>`, from its own sequence
(`breach_incident_ref_seq`), and is quoted by it until it is recorded as a
breach. Its title and the words describing where it occurred are sealed like
every other narrative the office writes. The table and the routes keep the
name `breach`: an incident is a breach row that has not been recorded as one.

## Validation

Whether the event is a personal data breach under s.2(u) - *pending* (still
validating; the clocks already running keep running), *yes* or *no* (not a
breach; the reasoning is kept) - with the reasoning and who made it. In the
code and the database it is still the *determination*. **The platform records
it and never computes it.** Nothing infers *no* from encryption: DPDP has no encryption
exemption and no severity threshold, and whether exposed data was sealed bears
only on this judgement, which is a person's. Whether a leak of sealed data whose
key was not exposed is a breach at all is Legal's question, not the code's.

A revision is a new row; the latest is current, and every earlier one stays for
the report.

- **Yes** carries `became_aware_at`: when the organisation became aware a
  personal data breach had occurred. It anchors every DPDP duty and cannot come
  before detection. The first *yes* records the breach (below). It creates the
  three DPDP duties, or reinstates any a previous *no* set aside, with clocks
  from this time.
- **No** marks those three duties not applicable, citing this determination.
  A duty already done stays done.
- **Pending** changes no duty.
- **CERT-In** is untouched by all three: it stands on its own test.

## Recording the breach

The **first** validation of *yes* records the incident as a personal data
breach, in the same transaction as the duties it starts. There is no separate
button: one would only be a way to hold back duties due without delay.

- It issues the **breach reference**, `BR-<year>-<n>`, from `breach_ref_seq`,
  so BR numbers count recorded breaches and nothing else. It is what principals
  and the Board are given - the notice's email and SMS, the delivery in her
  account, both Board documents.
- The recording is one row in `breach_recording`: the BR, the *yes* that
  caused it, who made it and when. **One per breach, never withdrawn.** A later
  *no* sets the outstanding DPDP duties aside and the recording stays; a later
  *yes* reinstates them and issues no second number. Two *yes* sent at once
  issue one.
- From then on the breach is quoted by its BR, with the INC it was logged as
  beside it. The read model carries `incident_reference`, `breach_reference`
  (null until recorded) and `reference` - the BR once recorded, the INC until
  then.

**What waits for the recording.** Sending the notice to principals is refused
before it (409 `breach_not_recorded`, "Record the breach before anyone is
notified"), and the notices card shows the same words. Deriving who it touched,
drafting and approving the notice, and drafting either Board document stay
open during validation; a Board document drafted then lists *Not yet recorded
as a personal data breach* in what it does not yet hold, and is quoted by the
incident reference.

**Incidents logged before this order** (migration 0038) keep the `BR-` string
they were given as their incident reference. Where one of their
determinations is a *yes*, the migration recorded the breach from the first of
them, carrying the same string, so a breach already quoted to the Board keeps
its number.

## The assessment

The facts Rule 7 asks for, revised as knowledge grows. Each revision is a new
row and the latest is current; the page shows the latest and how many came
before.

| Fact | Rule |
|---|---|
| Nature and extent | 7(1)(a), 7(2)(a) |
| Likely impact | 7(2)(a) |
| Consequences likely for the people affected | 7(1)(b) |
| The data categories exposed - and for each, whether its values were sealed and whether its key was exposed | the determination; the report |
| Events, circumstances and reasons | 7(2)(b)(ii) |
| Mitigation implemented, under way or proposed | 7(1)(c), 7(2)(b)(iii) |
| What people can do to protect themselves | 7(1)(d) |
| Findings on the person who caused it - **sealed; it may name an employee** | 7(2)(b)(iv) |
| Remedial measures against recurrence | 7(2)(b)(v) |
| Who answers people's questions | 7(1)(e) |

The categories are recorded per category because DKMS seals personal fields,
not relationships: who consented to what sits in plaintext, so "was it
encrypted" has more than one answer for most breaches. A key cannot be marked
exposed for a category that was not sealed. **No code reads these flags to
decide a duty**; a source test fails if anything but the assessment itself
names them.

## The duties

One record per duty, created when its trigger is met. They run in parallel on
their own clocks; nothing waits for the assessment.

| Duty | Created when | Due | Basis |
|---|---|---|---|
| Organisation's board | **every incident, when it is logged** | 30 minutes from first noticed (`BREACH_ORG_BOARD_MINUTES`) | internal policy |
| Report to CERT-In | **Mark reportable to CERT-In** | 6 hours from first noticed | CERT-In Directions 2022, IT Act s.70B |
| Board - initial intimation | validation *yes* | without delay | Rule 7(2)(a) |
| Board - detailed report | validation *yes* | 72 hours from awareness, or the date the Board allows | Rule 7(2)(b) |
| Principals notified | validation *yes* | without delay | Rule 7(1) |

- **A due time is stored when the duty is created and never recomputed.** A
  change of configuration - or of the code's hours - moves nothing already
  running.
- **Without delay** has no statutory hours, so it has no due time. The register
  shows the time elapsed since awareness and flags it against an internal target,
  `BREACH_WITHOUT_DELAY_TARGET_HOURS`. **That target is not set**: what it should
  be is Legal's and the Programme's decision, and until it is made the register
  shows the elapsed time and flags nothing.
- **Recording a submission** (Board and CERT-In duties) is a new row: when it
  was made, as entered, and the reference the regulator returned, which is
  required. A submission before its clock started is refused.
- **The Board's extension** of the detailed report records when it was asked
  for and the date allowed, which becomes the report's due time as a new row.
  The initial intimation's clock does not move.
- **The organisation's board** is policy, not DPDP: validation never sets it
  aside or moves it, and an incident logged more than thirty minutes after it
  was noticed starts out overdue, as CERT-In does. **Record the report** on the
  duty takes when it was made (not before first noticed, not in the future) and
  **to whom** - required, sealed - and a reference only if there is one.
  Incidents logged before migration 0039 have no such duty.
- **Principals notified** cannot be completed by hand. It completes when every
  affected principal's notice is delivered or its failure recorded after retry
  (S3-03).

Each duty's clock reads, in the console: time left or overdue for a dated duty;
time since awareness for one due without delay, and whether it is past the
target once one is set. Overdue rows are marked.

## Who it touched

Rule 7(1) asks for a notice to *each* affected principal, to the best of the
fiduciary's knowledge. **Who it touched** on a breach's page derives the list
from the records, and the DPO confirms it.

| Where it happened | Who the records place there |
|---|---|
| A processor | Everyone in files exported to it (`export_line`, to the line's destination processor) |
| A data source | Everyone captured in its assets and not yet erased from them (`asset_consent`). Bystanders - people in frame who never consented - have no account and are not listed |
| The platform's own database | Everyone with a row in the affected tables, written within a window (either end may be open) |

The first two read the same relation a rights request reads to find a
person's holders (`db/repositories/holdings.py`), from the other end. For the
database, each table that holds something about a principal is mapped to the
person it is about and when the row was written
(`breaches.PLATFORM_TABLES`); a sealed table that cannot be traced to an
account says why (`NOT_ABOUT_A_PRINCIPAL`), and a test fails for one that does
neither. No table is ticked for a database breach until the DPO ticks it:
every table since the beginning is everyone on the platform.

**Show what the records say** previews the people, counted and sampled, before
anything is written. **Confirm the list** records a **revision**: what it was
derived from, how many the records found, how many were left out, how many were
added by hand, and how many were newly listed. The DPO may:

- **leave out** people the records wrongly include - the left-out count is on
  the revision;
- **add** people the records cannot show, found by contact or part of a name.

**Nobody listed is ever removed.** A later revision adds only people not
already listed - each keeps the revision that first listed them - and every
earlier row stays as it was. A notice already sent cannot be unsent, and
listing too many is the safe side of Rule 7. Each person a revision adds is
notified in turn (S3-03).

## Telling the people it touched

Rule 7(1): each affected principal is told, concisely, clearly and plainly and
without delay, five things - and **Telling the people it touched** on a
breach's page is where they are written, approved and sent.

| Content | Rule |
|---|---|
| What happened - its nature, extent and timing | 7(1)(a) |
| The consequences likely for her | 7(1)(b) |
| What has been done, and is being done, to limit them | 7(1)(c) |
| What she can do to protect herself | 7(1)(d) |
| Who to contact with questions | 7(1)(e) |

- **Draft, approve, send - nothing on its own.** The first draft is filled from
  the assessment. **Approve** is refused while any of the five is empty, and
  names which; the database refuses it too (`breach_notice_complete`). An
  approved notice does not change. **Send** is refused before approval and
  while nobody is listed.
- **Her account first, then her contacts.** Send writes the notice to each
  listed person's account in the same transaction - an audit row against her,
  which is how her portal's notifications are derived, linking to **Personal
  data breach notices** in her portal - and queues an email to her registered
  email and an SMS to her registered mobile, each sent by the worker after the
  commit. The email carries all five; the SMS says a breach may affect her data
  and points to her account, where the same notice is.
- **A resend never duplicates.** Send writes only what is missing for the
  latest approved version: people newly listed, channels never tried, and a new
  attempt where the last one failed. Two sends at once write each state once
  (`breach_notice_delivery_once`). An email or SMS still queued fifteen minutes
  after it was sent was lost before the worker saw it - a broker that dropped
  it after the commit - and Send queues the same delivery again.
- **An update is a new version**, approved like the first and sent to everyone
  listed, the people already notified included. Her portal shows the latest
  above the earlier.
- **The account.** Every state of every attempt on every channel for every
  person is a row in `breach_notice_delivery`: queued, delivered, or failed with
  the error's class. The card shows, per version and channel, how many are
  delivered, queued and failed, and lists the failures. This is the account the
  Board's report quotes (Rule 7(2)(b)(vi)).
- **The duty completes by delivery.** *Principals notified* is done when every
  listed person has a version whose every channel has an outcome - delivered, or
  failed after the worker's retries (five, from five seconds and doubling; a
  failure no retry will mend, such as a contact that cannot be opened, is
  recorded at once). Nobody can mark it done by hand. People listed after it
  completed **reopen** it, and the next send notifies them.

The words are sealed, like every narrative about the breach; the console and
her portal open them, and the worker opens them at `deliver()`. They go to
everyone listed, so they must name nobody.

## The organisation's board

**Brief for the organisation's board**, from an incident's page, drafts what
to tell the board from the register as it stands, at any point from the first
minutes on: the reference, the title, first noticed, began, where it occurred,
the validation and time of awareness if any, whether it is marked reportable
to CERT-In, every duty with its clock, and who it touched **as counts only**.
It names what the register does not yet hold. It never carries the finding on
who caused it, anybody's name or contact, or who recorded what. **Print**
produces the copy to hand over. The platform never sends it.

## The Board and CERT-In

**The platform never submits to the Board or to CERT-In.** It drafts the
Board's documents, tracks every clock, and records a submission after a person
has made it through the regulator's own channel. A source test holds that
nothing in the breach code imports a way to reach anywhere else, and that the
one task that sends anything sends the principals' notice.

**Documents for the Board**, from a breach's page, drafts both from the
register as it stands - at any point, as often as wanted; each says when it was
drafted, and names what the register does not yet hold rather than leaving it
blank. **Print** produces the copy to file.

| Document | Carries | Rule |
|---|---|---|
| Initial intimation | Nature and extent, timing (noticed, aware, began), where it occurred, likely impact | 7(2)(a) |
| Detailed report | (i) updated and detailed information - the latest assessment, its categories, every determination; (ii) events, circumstances and reasons; (iii) mitigation; (iv) findings on who caused it; (v) remedial measures; (vi) the account of notices to principals | 7(2)(b) |

Item (vi) is always present. Before any notice has gone it says so, in words,
with how many people are listed; after, it gives per version and channel how
many were delivered, queued and failed, and how many listed people have been
notified on every channel.

**Recording a submission** - **Record submission** on the duty - is a new row
with when it was made and the reference the regulator returned; the Board's
extension of the detailed report moves only that duty's due time. **CERT-In**
is the duty created by **Mark reportable to CERT-In**, due six hours from
detection; whoever files follows CERT-In's own format and records the filing
the same way. Who files with CERT-In - the DPO or corporate security - is not
yet decided; today only the DPO can record it.

**The dashboard.** The DPO's dashboard lists every open breach with each duty's
state and time remaining or elapsed, and its **Needs attention** counts
**Breach duties overdue** (critical) and **Breach duties outstanding**. No other
role's dashboard carries any of it.

## Breach tickets

The people a breach needs - whoever runs the system that leaked, whoever holds
the log, whoever can confirm a deletion - are asked through **tickets**, the
rights request's model ([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md),
[rights-requests.md](rights-requests.md#holders-and-tickets)). **Tickets** on a
breach's page.

- **Assign a ticket** to a member of staff - or, choosing **Someone without a
  console login**, to anyone internal named by an email (below) - with what you
  are asking and an optional **answer-by** date. Refused before the breach is recorded (409
  `breach_not_recorded`); refused for anyone whose address is not on
  `BREACH_TICKET_EMAIL_DOMAINS` - internal staff only - without repeating the
  address; one ticket per person per breach (409 `ticket_exists`).
- **The holder** finds it on **Tickets** in the console, beside their rights
  tickets. They see the breach reference, the instruction, the thread, the
  state and the answer-by date - nothing else from the register, which still
  answers them 404. Their email says only that a ticket from the Privacy Office
  is waiting; it names no breach.
- **Both sides write** on the thread, with a file if it helps; files are kept
  like a rights ticket's, with their hash and sealed name, and every download is
  on the trail. The holder **returns** it - *done*, *partial* or *failed*, with a
  summary - and the DPO **sends it back** with a reason or **closes** it. Only the
  DPO closes a ticket, **withdraws** one, or **reopens** a closed or withdrawn
  one. The moves come from the server with each ticket.

| From | Event | To | Who |
|---|---|---|---|
| (assignment) | | issued | DPO |
| issued | returned (outcome, summary, optional file) | returned | holder |
| returned | sent back (reason) | issued | DPO |
| returned | closed | closed | **DPO only** |
| issued, returned | withdrawn (reason) | withdrawn | DPO |
| closed, withdrawn | reopened (reason) | issued | DPO |

The holder is emailed when a ticket is assigned, sent back or reopened. The
bell tells them what the office did and wrote, linking to their ticket; it tells
the DPO what holders wrote and returned. The DPO's **Needs you today** counts
**Breach tickets returned** and **Breach tickets past their answer-by**, and
every staff dashboard lists the breach tickets addressed to its reader.

### Temporary logins

Somebody without a console login can hold a ticket (S3-09, BD-04). The DPO
gives a name, an email and optionally a mobile; the address must be on
`BREACH_TICKET_EMAIL_DOMAINS` (422 otherwise, the address not repeated) and is
looked up by its keyed hash. Active staff get an ordinary ticket. A data
principal's account is given the role `breach_holder` while the grant lasts,
its previous role kept on the grant; with no account at all, one is made -
`pending`, `employee`, `breach_holder`, marked as made for this breach. Either
way they are sent **Temporary console access for a breach ticket**: the reset
link and a code, from the sign-in service like an invitation, naming no breach
(BD-18). They set a password and sign in with an emailed code like all staff,
and land on **My tasks**: their ticket, notifications and profile are all the
console holds for them. The Tickets card marks their row **Temporary login**,
with whether they have signed in yet, or that it has ended.

Access ends on three triggers (BD-15): the **breach closes** (every grant on it
ends in the closing transaction), the **DPO withdraws** that holder's ticket, or
an **administrator ends it** from the register (**End temporary access**; never
`end_staff_access`). Ending one grant ends only that one if they hold another
on a different breach; otherwise an account made for the breach is switched
off and one that existed goes back to the role it held (BD-16), the password
is cleared, `person_type` is never touched, and every session is revoked after
the commit. If an administrator has meanwhile given them a real role, it stays.
**Reopening their ticket** grants access again with a new grant row and a new
email; reopening a closed breach does not.

### Colleagues

A holder whose ticket is open - issued or returned - on an open breach can
**Add a colleague** (BD-05, BD-14): a name, an email, an optional mobile, and a
required note, sealed. The same domain check and three-way lookup apply. The
colleague gets **their own ticket** on the breach, with `parent_ticket_id`
pointing at the adder's, opening with the adder's note rather than the DPO's
instruction, and can add colleagues in turn. The adder's answer is their own
ticket whatever happened to the colleague's account, so it never says whether
the address had one; somebody who already holds a ticket on the breach is a
neutral 409 `colleague_not_added`. The DPO sees each colleague indented under
the person who added them, and the bell says who added whom; additions are
visible, not approved.

## Open and closed

A breach is open or closed, and nothing else: the duties carry the rest. It
**closes** only when it has been determined, every applicable duty is done or
not applicable, and **no breach ticket is issued or returned** - the page lists
what is still in the way. It **reopens** with
a reason, recorded in its history, when something new is found. While closed,
nothing about it can be recorded.

## What the database holds

| Table | Holds |
|---|---|
| `breach` | The incident as logged; `reference` is its INC. Only its `status` may change, by trigger (`cmp_breach_status_only`) |
| `breach_recording` | The incident recorded as a breach by the first *yes*: its BR, that determination, who and when. One per breach; append-only |
| `breach_status_history` | Every open and close, with the reason for a reopening. Append-only |
| `breach_determination` | Every determination, with its reasoning and, for *yes*, the time of awareness. Append-only |
| `breach_assessment` | Every revision of the facts. Append-only |
| `breach_obligation` | One row per duty per breach - `org_board`, `cert_in` and the three DPDP duties - with its stored due time and the moment its clock runs from. Append-only; one of each kind per breach, by unique constraint |
| `breach_obligation_event` | Everything that happens to a duty afterwards: completed (with `reported_to`, sealed, for the organisation's board - required there by trigger), not applicable, reinstated, extended, reopened. Append-only |
| `breach_affected_revision` | Each confirmation of who it touched: the scopes, the counts, a sealed note. Append-only |
| `breach_notice` | Each version of the five Rule 7(1) contents, sealed. A draft is editable; an approved one is frozen by trigger (`cmp_breach_notice_frozen`) |
| `breach_notice_delivery` | Every state of every attempt on every channel for every person. Append-only; `breach_notice_delivery_once` makes resends idempotent |
| `breach_ticket` | One per person per breach: the holder, who assigned it, what it opened with (sealed), the answer-by date. Only the read markers change, by trigger (`cmp_breach_ticket_read_only`) |
| `breach_ticket_event` | What happened to a ticket: returned (outcome, sealed summary), sent back, closed, withdrawn, reopened (each but close with a sealed reason). Append-only |
| `breach_ticket_message` | The ticket's thread: office, holder or platform; sealed body and file name. Append-only |
| `breach_temporary_access` | One grant of a breach-only login: whose, on which breach, through which ticket, whether the account was made for it, the role it held before, who granted it, and - once - when, by whom and why it ended (`breach_closed`, `ticket_withdrawn`, `account_deactivated`). One open grant per person per breach, by partial unique index; the end is written once and nothing else changes, by trigger; never deleted |
| `breach_affected` | Each person listed, once per breach (`breach_affected_once`), with the revision that first listed them and what put them there - exports, assets or tables, never a value. Append-only |

Every write takes the breach row first (`FOR UPDATE`), so two people recording
at once act one after the other: two determinations of *yes* sent together
create each duty once and issue one breach reference.

## The trail

Every change writes an audit row against `breach`: `breach.recorded` (an
incident logged - the key predates the incident-first order), `.determined`,
`.confirmed` (recorded as a breach, with its BR), `.assessed`, `.cert_in_marked`, `.obligation_created`,
`.obligation_completed`, `.obligation_not_applicable`,
`.obligation_reinstated`, `.obligation_extended`, `.affected_revised` (with the counts, and nobody's name or id), `.obligation_reopened`, `.notice_drafted`, `.notice_edited`, `.notice_approved`, `.notice_sent` (with counts), `.closed`, `.reopened`. A breach ticket's events are against `breach_ticket`, with the holder as subject: `breach_ticket.assigned`, `.message`, `.returned` (with the outcome), `.sent_back`, `.closed`, `.withdrawn`, `.reopened`, `.file_read`, `.colleague_added` (with the adder's ticket's uuid); the administrator's trail names them by the breach reference only. A breach-only login's grant and end are against the account: `user.temporary_access_granted` and `user.temporary_access_ended`, with the breach reference and the cause, never a name or an address. Each person whose account a notice is written to gets `breach_notice.delivered` against her, naming the breach reference (the BR) and the version: that is her portal's notification, and the only breach event she is shown. The
detail carries the reference, the outcome, which duty, a due time and that a
reason was given - never the office's words, which are sealed on their rows
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).

## Open questions

Owned by people, and not decided by the code:

| Question | Owner |
|---|---|
| Whether an event is a personal data breach - above all a leak of sealed data whose key was not exposed | Legal |
| The internal target for "without delay" | Legal and the Programme |
| Who answers principals' questions (Rule 7(1)(e)) | Legal |
| Who files with CERT-In - the DPO or corporate security. Today only the DPO can record it | Security and Legal |
