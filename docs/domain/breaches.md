# Personal data breaches

What the platform does when personal data it is responsible for is breached:
section 8(6) of the Act, Rule 7 of the DPDP Rules, and the CERT-In Directions
of 2022. The decisions behind the shape are
[ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md),
[ADR 0022](../decisions/0022-an-incident-first-and-a-breach-on-a-yes.md),
which puts the incident first, and [ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md),
which adds the public link, the reports and the organisation's board's mail,
and since its amendment of 2026-11-07 records the product owner's six answers;
the code is `cmp.domain.breach`, the routes are under `/breaches`, and the
console's pages are **Breaches** in the DPO's menu, headed **Incidents and
personal data breaches**.

**A breach belongs to an office** (0055). It is logged into the register of
the office that noticed it, and that office's officer holds it with every
power described here: the DPO on the DPO office's register, the Legal PoC on
the Legal office's. Neither sees the other's - its uuid answers 404, as to
anyone without the register. A member of staff of either office who is sent a
ticket on a breach answers it whichever office's breach it is. A legal hold is
likewise an office's to list and release, but what it stops it stops for
both: erasure of a person stops at a hold either office placed on her.

In order: an **incident** is logged as it was noticed, or arrives from anybody
through the **public link**; the office **validates** whether it is a personal
data breach under s.2(u); the first *yes* **records the breach**, starts the
DPDP duties and gives the office thirty minutes to **notify the organisation's
board**; the office finds **the people affected** and tells them; and each
report the regulators are owed is **drafted, finalised, sent by a person and
filed with its proof**. CERT-In runs from the moment of noticing whatever
validation says.

Two boards appear on this page. **The Board** is the Data Protection Board of
India, a regulator. **The organisation's board** is the organisation's own.

## Where the platform ends

The platform is the **system of record**. It records the breach, tracks every
duty's clock, holds the evidence that each duty was done, and sends mail to two
audiences: the people affected, and the organisation's board. **People** contain
the breach, preserve forensic evidence, decide whether it is a personal data
breach, and submit to the Board and to CERT-In through those bodies' own
channels. The platform never contains anything and **never talks to a
regulator**. Finalising a report mails the organisation's board, not the Board;
a filing is recorded after a person has sent the report, with the proof that it
was approved, the mail they sent and the reference the regulator returned.

## Who can see it

The officer of the office that holds it, and nobody else. The resource is
`breach`, and its guard answers every other role **404**, not 403 - on the register, on a breach that exists,
and on a write alike - so that a breach being handled is not itself disclosed
to a colleague walking uuids ([ADR 0004](../decisions/0004-scope-in-the-where-clause.md)).
The administrator, who reads the audit trail, sees that breach events occurred
and their reference (`Incident INC-2026-0001`, then `Breach BR-2026-0001
(INC-2026-0001)` once recorded), never a title or a reason, and cannot follow
the link.

**Breach settings** is the one page about breaches the administrator may open,
because nothing on it is about a breach ([below](#breach-settings)).

## The register

**Incidents and personal data breaches** lists every incident, open first by
default, with its outstanding duties and their clocks. **Search** finds one by
either reference (`INC-`, `BR-`), words of its title or where it occurred. The
filters ask the register the office's questions: **Show** open, closed or all;
**Validation**; **Duties** overdue or due within 24 hours; **Recent activity**
in the last day, week or month - anything written to it, its notices or its
tickets, from the audit trail; **Tickets** with one open or past its
resolve-by date. **Sort** by the most recent activity or by what is due soonest,
late first. The filters live in the address, so a filtered register can be
bookmarked or shared; every clock and count is the server's. The register
holds at most 500 incidents and their titles are sealed, so the narrowing is
done in the console after the titles are opened.

**Reported through the public link**, above the list, is what waits for an
office to take it up ([below](#the-public-link)).

## The page

A breach's page is one workspace, shaped like a project's (2026-10-06). Above
the tabs, where it stands: **Close** - or **Reopen** - with exactly what still
stands in the way, beside the details it was logged with (after the tabs on a
phone), and **Notify Organization Board** once the breach is recorded. Under the
tabs, the work in the order it runs: **Duties** (the default: every clock),
**Validation**, **Reports** (what the organisation's board and the regulators
are sent), **People & notices** (the people affected and what they are told),
**Tickets**, **Assessment**, **Attachments** and **Activity** (every close and
reopening, with its reason). A tab's count says how much is there; **Duties**
turns red when a duty is late and **Tickets** when one is past its resolve-by
date, whichever tab is open. Until it is validated, a prompt above the tabs
leads to Validation. The address names the tab (`#tickets`, `#people`,
`#reports`), so the bell's links and older addresses such as `#notices` open the
right one.

## Logging an incident

**Breaches → Log an incident.** Three things are asked for first, and every
time is typed in, never filled with "now". **What is known so far** follows
them (below).

| Field | Means | Anchors |
|---|---|---|
| First noticed (`detected_at`) | When the event was first noticed | CERT-In's six hours |
| Began (`began_at`) | When it started, if known. An assessment may revise it | the timing in 7(1)(a), 7(2)(a) |
| Where it occurred | The platform's own database, a processor, a data source, or elsewhere (in words) | 7(2)(a) |

An incident logged five hours after it was noticed has one hour of CERT-In time
left, and the register says so. A time in the future is refused, and so is a
start after detection.

The incident gets a reference, `INC-<year>-<n>`, from its own sequence
(`breach_incident_ref_seq`), at least four digits (`cmp_next_number`, 0062), and
is quoted by it until it is recorded as a breach. Its title and the words describing where it occurred are sealed like
every other narrative the office writes. The table and the routes keep the
name `breach`: an incident is a breach row that has not been recorded as one.

Logging starts no duty but CERT-In's, and that only on a *Yes* below: the
organisation's board's duty waits for validation.

### What is known so far (2026-10-08)

Below those, **What is known so far** asks the Privacy Office's intake
questions. **Every one is optional** - in the first minutes much is not known,
and the incident is logged anyway - and all but one are free text:

| Asked as | Column | For |
|---|---|---|
| Is it a cyber attack? (Yes - reportable to CERT-In / No / Not known yet) | `cyber_attack` | **Yes creates the CERT-In duty at once** - six hours from first noticed - exactly as *Mark reportable to CERT-In* does. No and Not known add nothing; the button stays for later |
| Where it started | `origin` | The system, team, vendor or place it began in |
| How it was found | `discovery` | Who noticed it, where and how |
| Systems affected | `affected_systems` | Applications, databases, servers, networks, devices |
| What happened | `incident_details` | As much as is known now |
| How much is affected | `impact_scale` | Records, people or files - an estimate |
| Countries involved | `countries_involved` | Where data was held or went, if it crossed a border |
| Kinds of personal data | `data_nature` | Identifying (names, contacts) or sensitive (health, financial, biometric) |
| Whose data | `subject_types` | Participants, employees, customers |
| Our entities involved or affected | `entities_involved` | The organisation's own companies, institutes or offices |
| Third parties involved | `third_parties` | Vendors, service providers, processors, partners |

The answers are **kept as logged** (migration 0047): sealed like every
narrative about a breach, shown under the breach's **Details**, and never
changed afterwards - `cmp_breach_status_only` now holds every column of the
row but its status. What is learned later belongs in the assessment.

## The public link

Anybody may report an incident, with no account (2026-11-06, migration 0058,
[ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)). The one link is
`/report-incident` on the portal, shown under **Breach settings** to be given
out.

**What they do.** They give their name and email, and a code goes to that
address (`POST /incident-reports/code`); the report goes in with the code
(`POST /incident-reports`). A wrong code takes nothing, so a stranger who never
answers leaves no row, and there are **no anonymous reports**. They say in a
line what happened and as much of it as they know; the rest of *What is known so
far* is theirs to leave, and they may say when they noticed it and whether it is
a cyber attack. They are given its `INC-` number, on the page and by email, and
nothing more. It is limited per address and per contact, like every public form.

**It waits apart.** A report is an `incident_report` row, not a `breach` row: it
has no office and no officer, and nothing should run on it until somebody has
read it. It takes its number from `breach_incident_ref_seq`, so no incident ever
shares one, and it waits in the **shared intake**, on no clock, above the list
under *Incidents and personal data breaches*, as **Reported through the public
link**. Both offices see it. Everyone in the roles named under **Breach
settings** is mailed that one has arrived: its number and when, nothing of what
it says.

**It is read a page at a time** (2026-11-07). The list shows fifty, the oldest
first, with how many are waiting and **Previous** and **Next**
(`GET /breaches/intake`, `limit` up to 200), and each row says who sent it, its
title and when it arrived. **Read it** fetches the rest of that one report
(`GET /breaches/intake/{report_uuid}`). A stranger with a few mailboxes can fill
the intake and nothing can be deleted from it, so it has to stay readable while
they do: served whole, about a hundred long reports were more than the console
could open at once, and every report, the genuine ones with them, showed sealed.
**Claim** and **Dismiss** work from the row.

**An officer takes it up, once.** From the report:

- **Claim** logs it as an ordinary incident in that officer's office, under the
  number it arrived with. First noticed is when it arrived, the first the office
  could have known; what the reporter says of when they noticed it is kept
  beside it and anchors nothing. From then on the other office cannot see it, and
  **Details** on its page shows who reported it.
- **Dismiss** needs a reason. The report and the reason stay, and nothing reaches
  the register. **Dismissed reports**, on the register, shows both officers the
  latest 200 with who sent each, who dismissed it and why, whichever office it
  was, so a report that was the other office's can still be raised
  (`GET /breaches/intake/dismissed`).
- **The reporter's rights over a dismissed report** (2026-11-07, 0065,
  [ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#a-dismissed-report-and-the-rights-of-the-person-who-sent-it)).
  A rights request from the reporter finds it by the blind index of their email (an
  account's only once proved), once identity is verified, and an erasure request
  blanks their name and email, keeping the number, the words, the reason and who
  dismissed it ([rights-requests.md](rights-requests.md#reports-from-the-public-link)).
  **Dismissed reports** then shows "erased" and when, and never which request: both
  offices see that list, and a request is one office's.

The second of two officers acting at once is told the other has (409
`already_claimed`, `already_dismissed`), and so is an officer who has it open: it
is read again every minute, and once it is taken up it closes with a warning. The
outcome is written once, by trigger,
and what the report says never changes. **A stranger's word starts no duty**: a
reporter's *yes* to a cyber attack is kept as what they said and creates no
CERT-In duty, which an officer's does. The officer marks it once they have read
it.

## Attachments

An incident arrives with what showed it - the email that reported it, a
screenshot, a chat, a log. They are kept with it (2026-10-06): chosen on
**Log an incident** and sent once it is logged, or added later on the
**Attachments** tab while it is open. Each is one of **Email**, **Proof**,
**Chat** or **Other**, with an optional note; PDF, PNG, JPEG, text, CSV, a
saved email (.eml, .msg) or Word, at most 25 MB. Evidence is kept as it came:
the name and the note are sealed, the hash and size recorded, and a file is
never replaced or removed - a file added in error stays, with the right one
beside it. Every download is on the trail, and carries the hash recorded when
it was kept beside the hash of what was read. For the officer of the breach's
office alone, like the rest of the register.

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
  from this time, and the organisation's board's, with thirty minutes from the
  validation itself. A duty it brings back whose work was done while it was
  aside is done at once, from that work, and nobody is mailed
  ([below](#what-a-yes-finds-already-done)). The first *yes* also sends a report
  to CERT-In held for it ([below](#the-one-report-held-for-a-yes)).
- **No** marks those four duties not applicable, citing this determination.
  A duty already done stays done. An incident validated *no* owes the
  organisation's board nothing, and can close.
- **Pending** changes no duty.
- **CERT-In** is untouched by all three: it stands on its own test. A mark made
  in error is set aside by the office, at any time and with a reason
  ([below](#a-cert-in-mark-made-in-error)), and a later *yes* does not bring it
  back.

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
notified"), and the notices card shows the same words. Finding the people
affected and drafting and approving the notice stay open during validation.
Writing a report waits for the recording, for the same reason; the report to
CERT-In alone waits for the CERT-In duty instead, because its clock waits for
neither. Finalised before the recording, its mail to the organisation's board
waits for the first *yes* ([below](#the-one-report-held-for-a-yes)).

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
| Organisation's board | validation *yes* | 30 minutes from that validation (`BREACH_ORG_BOARD_MINUTES`) | internal policy |
| Report to CERT-In | **Mark reportable to CERT-In**, or *Yes* to *Is it a cyber attack?* when logged | 6 hours from first noticed | CERT-In Directions 2022, IT Act s.70B |
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
- **A regulator's duty completes by filing its report**, and no other way: when
  it was sent, as entered, and the reference the regulator returned, with both
  proofs held ([below](#the-reports)). A filing is refused only in the future or
  before the incident was first noticed (422 on `filed_at`), never against the
  duty's clock, which a *yes* after a *no* starts again later than the report may
  have gone. One filed while a *no* had set the duty aside completes nothing
  then; the *yes* that brings the duty back completes it from that filing, the
  first recorded if several were. The route that recorded a submission by hand
  is gone, so no duty to a regulator completes without proof.
- **The Board's extension** of the detailed report records when it was asked
  for and the date allowed, which becomes the report's due time as a new row.
  The initial intimation's clock does not move.
- **The organisation's board** is policy, not DPDP, and starts at a validation
  of *yes* (ADR 0037): no duty runs before one, and an incident that is junk or
  validated *no* must be able to close without telling it anything. The first
  *yes* creates the duty, due thirty minutes from that moment, not from first
  noticed or from the awareness time entered. A later *no* sets it aside and a
  later *yes* gives it a new thirty minutes; if a report of its own reached the
  board while it was aside, that *yes* completes it from that mail, dated when the
  board was first reached, and mails nobody. **It is done when the mail lands**,
  not when **Notify Organization Board** queues it: once every address has its
  outcome and somebody was reached, the duty completes, naming those reached and
  nobody else. The time it records is when the first address was reached, which
  is what the thirty minutes ask: an address that took its retries past them does
  not make a duty met in time read late. A mail that reaches nobody leaves it
  outstanding, and its overdue alert fires. An incident logged before this keeps
  the duty it has, with its
  stored due time, until it is done or a *no* sets it aside, and one validated
  *no* before this changed had it set aside by migration 0063; one logged before
  migration 0039 has none.
- **Principals notified** cannot be completed by hand. It completes when every
  affected principal's notice is delivered or its failure recorded after retry
  (S3-03).

Each duty's clock reads, in the console: time left or overdue for a dated duty;
time since awareness for one due without delay, and whether it is past the
target once one is set. Overdue rows are marked.

### A CERT-In mark made in error

**Not reportable to CERT-In**, on the duty's row, sets the duty aside (2026-11-07,
[ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)).
Confirmed by the product owner on 2026-11-07, who let it happen at any time.

A *no* leaves CERT-In alone, so an incident marked by mistake, or logged with *Yes*
to *Is it a cyber attack?*, keeps its duty. The route that recorded a submission by
hand was the way out of that, and it is gone: without this, a false alarm could
close only by mailing the board a report, attaching proof of a mail nobody sent and
entering a reference nobody returned.

- **Whatever validation says.** Before any validation, while pending, after a *yes*
  or a *no*; the event cites no determination (migration 0064), since no validation
  set it aside. A set-aside or re-mark recorded before 0064 cites the validation then
  latest, and is served with its `determination_uuid`. It was first allowed only
  once the latest validation was *no*, and 409 `cert_in_not_validated_no` is gone
  with that rule. Set aside before any
  validation, the incident still cannot close until it is validated.
- **With a reason**, sealed on the duty's event and shown on its row. The trail says
  only that one was given.
- **A duty done or a report filed stands** (409 `duty_not_outstanding`,
  `report_filed`). Something was reported.
- **Nobody is told.** It mails nobody, and leaves validation, the organisation's
  board's duty and the DPDP duties alone. A report already mailed to the board has
  been mailed, and that stands.
- **Set aside, there is no report to CERT-In.** A draft left open stays a draft.
  Writing one, finalising it, **Try again**, keeping a proof and recording it as
  sent are all refused (409 `breach_not_recorded`, "CERT-In was set aside as not
  reportable. Mark it reportable again first"), and the register's brief no longer
  says it is reportable. If it was sent after all, mark it first and then file the
  same report, which completes the duty. A report to CERT-In whose mail waits for
  the first *yes* is not sent at that *yes* while the mark is set aside
  ([below](#the-one-report-held-for-a-yes)).
- **Marking it again brings it back**, on the same six hours from first noticed. A
  later *yes* does not: CERT-In stands on its own test.

### What a yes finds already done

A *no* sets aside the duties not yet done, and a later *yes* brings them back on new
clocks. The work may have been done meanwhile, and the product owner's answer of
2026-11-07 is that it counts
([ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#what-a-yes-finds-already-done)).
The *yes* reads three of the duties it brings back again - the board's, the initial
intimation and the 72-hour report - under the breach's row, and mails nobody; the
principals' it does not (below).

- **The organisation's board.** If one of the board's own reports reached it while
  the duty was aside, the *yes* completes the duty from that mail: dated when the
  board was first reached, naming whom it reached, recorded as the system's. Of
  several, the first version to have run its course and reached somebody is the one.
  A mail still on its way completes the duty when it lands; one that reached nobody
  leaves the duty outstanding on its new thirty minutes. If the key service cannot
  open a name for it, the *yes* stands, the duty stays outstanding and
  `breach.board_duty_unsettled` is logged. **Try again**, on any version of the
  board's report, reads every version again, oldest first, and completes the duty
  from the first that reached somebody, recorded as a person's press
  (`by: try_again`, with them as the actor); a key service still away fails the
  press (503). The worker's re-read after any later outcome reads every version the
  same way, so a later version that lands first is not the one recorded.
- **The initial intimation and the 72-hour report.** A report filed while the duty
  was aside completes it at the *yes*, from when it was sent and the reference that
  came back, recorded as the filer's. Of several, the first filing recorded is the
  one, by when it was recorded and then by version.
- **CERT-In** is never brought back by a *yes*, and no report to CERT-In can be
  filed while it is set aside.

Such a duty is checked against the clock the *yes* brings back, not the one the *no*
set aside. The board's earlier mail always reads on time, dated before that clock
started. A regulator's report reads late if it was sent after the reinstated due,
and its date may fall before or after that clock's start, since a *yes* may enter
any awareness from first noticed on. Nothing on the trail says the first clock
lapsed: its due stays on the duty's row and on `breach.obligation_created`, and the
*no* that set it aside on the duty's events. Notices to the people affected that
were delivered while the *no* stood are not counted: the *yes* brings that duty back
outstanding, and pressing **Send** again completes it ([open](#open-questions)). A
*yes* recorded before this change that brought a duty back with its work done is not
swept: the board's duty completes from **Try again**, and the next *yes* reads any
duty again.

## The people affected

Rule 7(1) asks for a notice to *each* affected principal, to the best of the
fiduciary's knowledge. **Affected people**, on the **People & notices** tab,
builds that list in the words of the work (2026-11-06, ADR 0037): the person
running a breach knows what it reached, not how the data is stored. There are
five ways to add to it, and the office uses as many as it needs.

| Way | Who it finds |
|---|---|
| **From a project or activity** | Everyone who gave consent in it, including those who later withdrew, between two dates if given. Only the office's own, each shown with how many people are in it |
| **From a vendor** | Everyone in files exported to that processor (`export_line`, to the line's destination processor), and everyone standing in an HR activity whose category names it. Only those the office can see: the registry is shared, a breach is one office's |
| **From a data source** | Everyone captured in its assets and not yet erased from them (`asset_consent`). Bystanders - people in frame who never consented - have no account and are not listed |
| **Upload an Excel list** | [Below](#people-the-records-cannot-show-a-list-sent-to-us): name, mail ID and mobile number |
| **Add one person** | Somebody the records cannot show, found by their contact or part of their name |

The vendor and the data source read the same relation a rights request reads to
find a person's holders (`db/repositories/holdings.py`), from the other end. A
consent later withdrawn still counts for a project: their data was held, and
listing too many is the safe side of Rule 7.

**Tables are not a way to look any more.** Choosing the platform's tables was
removed: nobody running a breach should have to know them. People already listed
that way stay listed, shown as *From the platform's records* (`found_by`
`platform`), and nothing writes it now.

The office sees who the records show, counted and sampled, before anything is
written. Confirming records a **revision**: where it looked, how many the records
found, how many were left out, how many were added by hand, and how many were
newly listed. The office may:

- **leave out** people the records wrongly include - the left-out count is on
  the revision;
- **add** people the records cannot show, as above.

**Nobody listed is ever removed.** A later revision adds only people not
already listed - each keeps the revision that first listed them - and every
earlier row stays as it was. A notice already sent cannot be unsent, and
listing too many is the safe side of Rule 7. Each person a revision adds is
notified in turn (S3-03).

### People the records cannot show: a list sent to us

The decision: [ADR 0027](../decisions/0027-a-breach-can-reach-people-with-no-account.md).

Often the people affected are not on the platform at all - a processor's own
participants, a team's contact list - and before 2026-10-07 the breach could
then never close: the notice is owed to everyone listed, and nobody could be
listed. **Upload an Excel list** takes the list from outside, in one of two
forms, each from an Excel template the office downloads there (a CSV is still
taken):

| List | Columns | What happens to each row |
|---|---|---|
| People | Name, Mail ID, Mobile number (either contact, or both; the name optional) | Somebody whose email or mobile is an account's is listed as that account (*In a list sent to us*), and also sees the notice in their account. Anybody else is kept as a **contact of this breach alone** - name, email and mobile sealed - and is told by email and SMS. |
| Asset IDs | Asset ID, Source code (only where two sources share an ID) | The asset is found by the platform's asset ID or by the capture tool's own; the people who consented in it are listed. People in it who consented to nothing name nobody and cannot be traced: they are counted, and said. |

- **Checked, then taken.** *Check the file* writes nothing: it counts what
  the file would add - on the platform, not on the platform, already listed or
  repeated (skipped), unreadable, untraceable - and names each row it cannot
  read by its row number, with why (no contact, not an email, an unknown or
  ambiguous asset). *Add N to the list* takes the rows that can be read; a
  corrected file can be sent again, and rows already listed are skipped. The
  headings people use instead of ours - *Mail ID*, *Phone*, *Full name* - are
  understood, and a file of more than 50,000 rows is refused. An old `.xls`
  workbook is refused with how to save it as `.xlsx`, and so is one that cannot
  be read.
- **The file is not kept.** It is a list of contacts in the clear; what matters
  is now sealed in the rows. Its sealed name, hash and counts are kept
  (`breach_upload`), and listed under *Lists taken*.
- **A contact is listed once per breach**, by the blind index of their email
  and of their mobile, and is never removed - like everyone listed.
- **They count.** *Principals notified* is owed to the accounts listed and the
  contacts alike; a contact is sent the email and the SMS (never an account
  they do not have), and each outcome counts toward the duty exactly as an
  account's does. Contacts added after the duty completed reopen it.

## Telling the people affected

Rule 7(1): each affected principal is told, concisely, clearly and plainly and
without delay, five things - and **Notice to the affected people** on the
**People & notices** tab is where they are written, approved and sent. Once it
is approved, one button, **Send to all *n* affected people**, reaches everybody
listed, on the platform or not.

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
  and points to her account, where the same notice is. **A contact with no
  account** is sent the email and the SMS only, in their own words (*Personal
  data breach notice, to someone with no account*): the email has all five
  with no account to point to, and the SMS carries what happened, what they
  can do and whom to ask.
- **A resend never duplicates.** Send writes only what is missing for the
  latest approved version: people newly listed, channels never tried, and a new
  attempt where the last one failed. Two sends at once write each state once
  (`breach_notice_delivery_once`). An email or SMS still queued fifteen minutes
  after it was sent was lost before the worker saw it - a broker that dropped
  it after the commit - and Send queues the same delivery again. Each task
  claims what it sends to first (below, for a report), so the two together send
  once.
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

## The reports

Every report a breach calls for is written here, on the **Reports** tab, and goes
one path (2026-11-06, migration 0059, [ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)).

| Report | Goes to | May be written | Discharges |
|---|---|---|---|
| Report to the organisation's board | The organisation's board, mailed by the platform | once recorded | Organisation's board |
| Initial intimation to the DPDP Board | The Board, by a person. Rule 7(2)(a) | once recorded | Board - initial intimation |
| Report to CERT-In | CERT-In, by a person | once it is marked reportable, whatever validation says | Report to CERT-In |
| 72-hour report to the DPDP Board | The Board, by a person. Rule 7(2)(b) | once recorded | Board - detailed report |
| Closure report | The Board, by a person, if the office sends one | once recorded | Nothing: it is optional, and never stands in the way of closing |

**Draft.** A report starts from the register, section by section, and from there
it is the office's: what is drafted is what a person read and meant, and it is
never regenerated underneath them. What the register does not hold stays empty.
A section may be rewritten as often as wanted while it is a draft; there is one
draft of a kind at a time, and the next version starts from the last one's
words. The words are sealed. Any version comes out as a PDF, and every read is
on the trail.

| Report | Sections |
|---|---|
| Organisation's board | What happened; when; where it occurred; people affected, as counts; where the duties stand; what happens next (optional). Its first draft names nobody, and never carries the finding on who caused it |
| Initial intimation | The nature and extent of the breach; its timing; where it occurred; its likely impact |
| CERT-In | The incident; when it occurred and was noticed; systems affected; what shows it (logs, addresses, files; optional); action taken so far |
| 72-hour report | Rule 7(2)(b)(i) to (vi): updated and detailed information; the events, circumstances and reasons; measures to mitigate the risk; findings on the person who caused the breach; remedial measures; the account of notices to Data Principals |
| Closure report | Summary; root cause; measures taken; measures to prevent recurrence; Data Principals notified; conclusion |

**Finalise.** Finalising is refused while a required section is empty, and names
each one. It freezes the words, by trigger, and mails the organisation's board,
one delivery per address, with the words in the mail and the report as a PDF.
The words are quoted in the mail: they are somebody's words, so a link or a code
in them stays text and becomes no button. A finalised report is corrected by a
new version, which mails the board again.

**Who it goes to** (2026-11-07, 0064,
[ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#who-a-report-goes-to)).
The window that finalises a report lists every name and address on the board's
list, all ticked (`GET /breaches/{uuid}/reports/recipients`), and sends
`{recipients, extra}`: the entries chosen, and any address added for this report
alone. The saved list does not change.

- **Untick** any entry this report should not go to. A **mandatory** entry is ticked
  and locked: leaving it out is refused (409 `recipient_mandatory`, with the
  entries in `details.missing`).
- **Add an address for this report alone**, with an optional name. It is kept,
  sealed, as an entry that is never on the list (`one_off`), so nobody else is
  mailed it later and Breach settings never shows it. One already on the list is
  that entry, and two alike are one. Not an address is 422 on `extra.N.email`.
- **Who a version went to is frozen with it** (`breach_report_addressee`), and every
  delivery names an addressee of its report, so nothing is mailed to anyone the
  version was not addressed to.
- **What is refused**: an entry taken off the list since the window read it (409
  `recipient_not_listed`, the entries in `details.gone`); an empty list and no
  address added (409 `no_board_recipients`, "Nobody is on the organisation's board
  list yet"); entries on the list but none chosen and none added (422 on
  `recipients`). An empty list with an address added goes: the board's thirty
  minutes do not wait on settings.
- **A report to CERT-In before the incident is recorded** records who it goes to
  and queues nothing; its mail waits for the first *yes*
  ([below](#the-one-report-held-for-a-yes)).

The trail's `breach.report_finalised` says how many were mailed, whether it is held,
how many were added for this report and how many on the list were left out.

**The mail, address by address.** Every address the version was addressed to has
an account like a notice's - delivered, queued or failed - with one line for one
address, and whether it was mandatory when the version was finalised and whether
it was added for this report alone. A line never queued reads **held** while its
report to CERT-In waits for a *yes*, and **not sent** otherwise: replaced by a later
version before it went, or withheld because CERT-In was set aside at the *yes*. An
address taken off the list and put back is a new row of the list and the same
person: delivered under either is delivered, and what it was sent it is not sent
again. Taken off and not put back it reads as neither failed nor on its way, and
stays in the list marked; an address added for one report alone is never taken off.

**Try again** shows when sending again would do something, on the newest finalised
version of a report on an open breach. It tries only the addresses this version was
sent to, never one added to the list since: that address was never chosen for it,
and a new version reaches the list as it then stands. The server says how many
addresses it would queue (`mail.retryable`): those not reached, those never queued
(a report to CERT-In withheld at the *yes* and marked again, when the button reads
**Send to the board**), and a mail lost on its way. A mail still queued fifteen
minutes on was lost before the worker saw it, and takes a new attempt: the account
is only added to, and that row is what makes it read as moving. If the first task
ever runs it finds the later attempt and stands down. An address taken off the list
is never mailed, whatever was waiting for it. What was queued to it is recorded
failed (`RecipientRemoved`) and the duty is re-read then, so a report does not wait
on an address nobody will try again.

A press re-reads the board's duty first, whatever follows, and answers how many it
queued. On any version of the board's own report it reads every finalised version,
oldest first, as a *yes* does, and completes the duty from the first that reached
somebody (`by: try_again`, the person pressing as the actor): the version that
reached the board may be an older one the console offers no button on. A key
service that cannot open a name for the duty fails the press (503), and nothing is
queued. It is refused, and `retryable` is 0, on a report to CERT-In set aside (409
`breach_not_recorded`), on a report to CERT-In whose mail waits for a *yes* (409
`report_held`, "This goes to the organisation's board when the incident is validated
as a personal data breach") and on a version a later finalised one replaced (409
`report_superseded`), checked in that order; a closed breach also serves 0 and
answers 409 `breach_closed`. An empty list refuses nothing, since the version's own
addresses are what it tries. If the re-read completed the duty, a press
that would be refused answers 200 with nothing queued. So the duty can stand with
`retryable` at 0 after a re-read failed; the console then offers **Try again** for
an `org_board` report's newest version once something was delivered and nothing is
queued.

**One send to one address at a time.** Two tasks can hold one address, and after an
outage they start together, so reading that no outcome is recorded stops neither.
Each claims the report and the address in Redis before it sends, for eleven minutes:
longer than a task may run, shorter than a mail takes to read as lost. A task that
loses stands down, and one that sends nothing lets the claim go. A worker killed
mid-task is not a second sender: its message comes back under the same task id and
takes its own claim back, because standing down there would leave nothing alive to
send the mail. A kill after the send can therefore mail one address twice, and so
can a broker connection lost in the middle of a send, when the message comes back
while the first run is still going: the cost every task here accepts. A claim nobody
comes back for runs out by itself, and a Try again pressed before it does stands
down with it.

**Delivered stands.** An address's line reads delivered once any attempt has been,
whatever is written after it. Recording takes no breach row, so a re-queue or a
removal can land just behind the delivered row, and neither unsends a mail.

**A mail that has gone is never sent again to get it on the record.** What follows
the send is only recording. If that fails, `cmp.notifications.record_breach_report_result`
retries it and nothing else, eight times over about a quarter of an hour, and the
claim is kept for an hour so that Try again stands down meanwhile. The account and
the board's duty are two transactions, so a key service that cannot open a name for
the duty cannot undo the account of a mail. Writing the account takes no breach row,
so it does not wait behind a long list being uploaded; if the re-read of the duty
still fails, Try again runs it.

**What the board reads may name somebody.** A report goes to every address the
sender chose, as it was written, in the mail and as a PDF, outside the sealed
register. The 72-hour report's section on the person who caused the breach is
drafted from the assessment's findings, which may name an employee
([ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)
counts the cost). Neither mail may be copied.

**File.** For the four that go to a regulator, finalising only tells the
organisation's board, for its information; it says so, and **it does not mail the
DPDP Board or CERT-In**. A person sends the report through the regulator's own
channel, then records it, with both proofs attached: the **proof of internal
approval** and **the mail sent to the regulator**. Filing takes when it was sent,
not when it is being recorded, and that may be before it was finalised here: a
person may have sent it first. It is refused in the future and before the
incident was first noticed (422 on `filed_at`, "It cannot have been sent before the
incident was first noticed"), and not against the duty's clock: a *yes* after a
*no* starts that clock at its own awareness, and the report may have gone before
it. It also takes the reference the regulator returned, which a closure report
need not have. It is refused without both proofs (409
`report_proof_missing`), and it is what completes the duty, at once, or at the
*yes* that brings back a duty a *no* had set aside
([above](#what-a-yes-finds-already-done)). There is no other way
to complete a regulator's duty. The proofs are kept with the breach's other
files, never replaced or removed.

### The one report held for a yes

The report to CERT-In may be written and finalised on the mark alone, whatever
validation says, because its six hours wait for neither. Every other report waits
for the recording. Its mail to the board is held until the first *yes* (2026-11-07,
[ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#a-report-to-cert-in-before-a-yes)),
so the board never reads a report on an incident that was never validated *yes*.

- **Finalised before the incident is recorded**, it records who it goes to and
  queues nothing. The button reads **Finalise and hold for validation**, and its
  lines read held. **Try again** is refused (409 `report_held`).
- **The first *yes* sends it**: the newest finalised version, as frozen, to the
  addresses chosen for it, less any taken off the list since. Nobody added to the
  list or marked mandatory after it was finalised is mailed it. The mail carries the
  breach reference the *yes* issued. `breach.report_released` is on the trail, with
  how many were queued and how many left out.
- **A *no* keeps it held**: a mail is held exactly while the incident has no breach
  reference, and a *no* issues none. It goes at the first *yes*, even after a *no*,
  and an incident that closes on a *no* never sends it. This is settled, not open.
- **Set aside at the first *yes***, it is withheld, `breach.report_withheld` on the
  trail, and its lines read not sent. Nothing sends it later by itself: once CERT-In
  is marked again, **Send to the board** (Try again) sends it, as a person's act, or
  a new version does. Set aside and marked again before the *yes*, it goes at the
  *yes* as though never set aside.
- **Nobody left to send it to**: everybody it was chosen for has been taken off the
  list by the first *yes*. Nothing goes, and it is withheld too,
  `breach.report_withheld` with `why: nobody_on_the_list` and how many were left
  out, never a release that queued nobody (2026-11-08). Try again has nobody to try;
  a new version reaches the list as it then stands. The trail reads *Report held for
  the board not sent at the validation* for either reason.
- **Only the newest version goes.** An older one finalised before the *yes* reads
  not sent, replaced, and Try again refuses it (409 `report_superseded`).
- **Filed while held**, it completes its duty; the mail still waits for the *yes*,
  then goes.
- **After the first *yes*** the board has the breach, so a report to CERT-In
  finalised then, even during a later *no*, is mailed at once.

## The organisation's board

**Notify Organization Board**, at the top of a recorded breach's page, opens its
report in a pop-up, drafted from the register. Under **Who it goes to** the pop-up
lists every name and address on the board's list, all ticked: mandatory ones are
locked, any other may be unticked, and an address may be added for this report
alone ([above](#the-reports)). **Send to the board** finalises it, which queues a
mail to the addresses chosen. The duty is done when that mail lands, naming who was
reached; if it reaches nobody the duty stays outstanding, and **Try again** on the
**Reports** tab sends it again to the addresses it went to. The button stands while
the duty does, and follows the same rule as **Try again**. While the mail is on its
way it says so. Where Try again would do something it leads to **Reports**: *Not
reached* if nobody was, and *Delivered: finish on the Reports tab* if the mail
landed and only the duty is waiting, which since 2026-11-07 is left only for a
settling that failed. When nobody the version went to can still be reached - every
one of them taken off the list since - it points to a new version, which reaches
the list as it now stands. Otherwise it offers a new report, and a further version
is written on the **Reports** tab. The thirty minutes run from the validation, and
the DPO team is several `dpo` accounts, so they never wait on one person.

`GET /breaches/{uuid}/org-board/brief` remains as the register's own view: its
counts, its clocks, what it does not yet hold, and no name. It is not what is
mailed.

## The Board and CERT-In

**The platform never submits to the Board or to CERT-In.** It drafts, tracks
every clock, and keeps what a person sent and the proof of it. A source test
holds that nothing in the breach code imports a way to reach anywhere else, and
that the breach tasks send only the principals' notice (`breach_notice`, or
`breach_notice_direct` to a person with no account); to a member of staff holding
a ticket, `breach_ticket_waiting` and `breach_ticket_date_changed`; and a report,
`breach_board_report` or `breach_report_finalised`, to the addresses chosen for it
from the board's list, or added for it alone. The office's own reminders -
`breach_duty_due` and `breach_ticket_returned`, to the officers of the breach's
office, and `breach_board_list_changed`, to the officers of both offices when the
board's list changes - go from `tasks/notifications/alerts.py`, with every other
module's notices to staff.

**The account of notices** in the 72-hour report (item (vi)) comes from the
register when it is drafted. Before any notice has gone it says so, in words,
with how many people are listed; after, it gives per version and channel how
many were delivered, queued and failed, and how many listed people have been
notified on every channel. A report that outlives the facts is brought up to
date by rewriting the section, or a new version.

**The Board's extension** of the detailed report moves only that duty's due time.
**CERT-In** is the duty created by **Mark reportable to CERT-In**, or by *Yes* to
*Is it a cyber attack?* when an officer logs the incident, due six hours from
detection; whoever files follows CERT-In's own format and records the filing the
same way. A mark made in error is [set aside](#a-cert-in-mark-made-in-error). Who
files with CERT-In - the officer or corporate security - is not
yet decided; today only the officer of the breach's office can record it.

`GET /breaches/{uuid}/board/intimation` and `/board/report` remain as the
register's own views, rebuilt each time they are read. What is sent is the report
above, frozen when it was finalised.

**The dashboard.** The DPO's dashboard and the Legal PoC's each list their own
office's open breaches with each duty's state and time remaining or elapsed, and
their **Needs attention** counts **Breach duties overdue** (critical), **Reported
incidents waiting for an office**, in both, and **Breach duties outstanding**. No
other role's dashboard carries any of it. These figures read the register, which
holds 500, so past 500 open incidents they count the 500 noticed last and leave the
oldest out. The overdue mail reads every open breach.

## Breach settings

**Breach settings** in the console (resource `breach_settings`, 0058) is how the
office hears of a breach. The administrator, the DPO and the Legal PoC keep it;
every other role is answered 403. It says nothing about any breach, so the
administrator keeps it without seeing one.

- **The public link**, to give out.
- **Who is told when a report arrives**: roles, not people; every active account
  in them is mailed. The two officers are always among them, because a report
  nobody who may claim it hears of would wait for ever. Anybody else it names is
  told a report arrived and can do no more about it than their role already
  allows. A breach-only login and a data principal cannot be chosen.
- **The organisation's board**: the addresses every report's window offers, each
  with an optional name. Name and address are sealed, an address is listed once,
  by its blind index, and one taken off the list stays, with who took it off and
  when, because reports already mailed name it. A name carrying the sealed prefix
  is refused (422 on `full_name`).
- **Mandatory** (2026-11-07, 0064): an entry ticked mandatory goes with every report
  finalised while it is set, and cannot be left out of one or taken off the list
  until it is made optional again (409 `recipient_mandatory`, "Make it optional
  before taking it off the list"). The row shows when the mark last changed and who
  changed it (`PUT /breach-settings/board-recipients/{uuid}/mandatory`); each change
  is a `breach_board_recipient_event`. An unchanged mark records nothing.

The trail says what changed, never an address: `breach_settings.changed` with
`board_recipient` `added`, `removed`, `made_mandatory` or `made_optional`, and the
entry's uuid.

**Both officers are told of every change to the list.** Adding an address, taking
one off, and marking or unmarking one mail every active DPO and Legal PoC account
(`breach_board_list_changed`), the one who made the change included: who did it,
what, the name and the address, and no breach. An administrator who makes a change
is not mailed, being no officer. It is the check the product owner asked for, so a
change is refused (503 `service_unavailable`) when the broker cannot take the
mail, before anything is written. With no active officer the change stands and
`breach_settings.nobody_to_tell` is logged at error.

**It is one list.** Both offices and the administrator keep it, and it has no
office. A report on either office's breach is offered to every address on it, and
anyone who keeps the list could add an address, their own included, and be mailed
reports they could not otherwise read: the administrator sees no breach here, but
an address on the list would. An entry is checked only as an address. The product
owner kept the one list on 2026-11-07
([ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#who-a-report-goes-to)),
and two things now stand against that cost: both officers hear of every change by
name and address, and the sender sees every name and address before a report goes.
What stays uncovered is an address added for one report alone: it is told to
nobody else, because telling the other office would reveal the breach.

## Breach tickets

The people a breach needs - whoever runs the system that leaked, whoever holds
the log, whoever can confirm a deletion - are asked through **tickets**, the
rights request's model ([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md),
[rights-requests.md](rights-requests.md#holders-and-tickets)). **Tickets** on a
breach's page.

- **Assign a ticket** to a member of staff - or, choosing **Someone without a
  console login**, to anyone internal named by an email (below) - with what you
  are asking, an optional **Resolve by** date and, if it helps, a document. The
  document goes on the ticket's thread as it is raised; if the file is refused,
  the ticket stands and the office is told. Refused before the breach is recorded (409
  `breach_not_recorded`); refused for anyone whose address is not on
  `BREACH_TICKET_EMAIL_DOMAINS` - internal staff only - without repeating the
  address; one ticket per person per breach (409 `ticket_exists`).
- **The holder** finds it on **Tickets** in the console, beside their rights
  tickets. They see the breach reference, the instruction, the thread, the
  state and the resolve-by date - nothing else from the register, which still
  answers them 404. Their email says only that a ticket from the Privacy Office
  is waiting; it names no breach.
- **Both sides write** on the thread, with a file if it helps; files are kept
  like a rights ticket's, with their hash and sealed name, and every download is
  on the trail. The holder **returns** it - *done*, *partial* or *failed*, with a
  summary - and the office **sends it back** with a reason or **closes** it. Only
  the officer of the breach's office closes a ticket, **withdraws** one, or
  **reopens** a closed or withdrawn one. The moves come from the server with each
  ticket.
- **Either side may change the date** while the ticket is open (0061, ADR 0037).
  **Change the date** takes the new date and a reason, which is required, and
  needs nobody's approval. The date before, the date after and the sealed reason
  go on the ticket's events and on its thread, and the two dates on the trail. A
  date in the past, or the date it already has, is refused. The other side is
  told by email in words that name no breach: the holder, or every active officer
  of the breach's office. A trigger refuses a new date that no event records.
  The label is **Resolve by** on breach tickets only; `answer_by` keeps its name
  in the code, and a rights ticket's date is unchanged.

| From | Event | To | Who |
|---|---|---|---|
| (assignment) | | issued | officer |
| issued | returned (outcome, summary, optional file) | returned | holder |
| returned | sent back (reason) | issued | officer |
| returned | closed | closed | **officer only** |
| issued, returned | withdrawn (reason) | withdrawn | officer |
| closed, withdrawn | reopened (reason) | issued | officer |
| issued, returned | date changed (date, reason) | as it was | either |

The holder is emailed when a ticket is assigned, sent back or reopened. The
bell tells them what the office did and wrote, linking to their ticket; it tells
each officer, the DPO and the Legal PoC, what holders wrote and returned and any
date they moved on their own office's tickets. The officers' **Needs you today**
counts **Breach tickets returned** and **Breach tickets past their resolve-by**, and
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
with whether they have signed in yet, or **read only** once their part is over.

**Their part ends; the login stays** (decided 2026-10-06). The grant - the
window in which they act - ends when the **breach closes** (every grant on it,
in the closing transaction) or the **DPO withdraws** that holder's ticket
(BD-15). The account is left as it is, so they can still sign in and read
their ticket; a withdrawn or closed ticket, and every ticket on a closed
breach, refuses every write, so read-only needs no check of its own. A person
who also holds a real role keeps it, and their tickets with it.
**Reopening their ticket** opens a new grant and emails them that a ticket is
waiting; reopening a closed breach does not reopen anybody's ticket.

**Rights tickets use the same logins** (0049, 2026-10-08): a rights ticket
sent to an internal address with no console login gives the same temporary
login, recorded in the same table against the rights holder
(`breach_temporary_access.holder_id`, `breach_id` then empty). End temporary
access ends both kinds ([rights-requests.md](rights-requests.md#how-a-holder-is-reached)).

**The off switch is the administrator's.** **End temporary access** on the
register (never `end_staff_access`) ends every open grant and puts the account
back as it was before its first grant: switched off if it was made for a
breach, its previous role - `data_subject` - otherwise (BD-16). The password is
cleared, `person_type` is never touched, and every session is revoked once the
change has committed. Asked again later, they get a new access email.

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
| `breach_obligation_event` | Everything that happens to a duty afterwards: completed (with `reported_to`, sealed, for the organisation's board - required there by trigger), not applicable (with a sealed `note` where a CERT-In mark was set aside), reinstated, extended, reopened. Append-only. A not-applicable or reinstated event cites the determination that moved it, by trigger (`cmp_breach_obligation_event_cites_determination`, 0064, in place of 0034's CHECK), except on CERT-In, which validation never moves. A completion's `recorded_by` is empty when the board's mail did it, and the filer when a filing did |
| `breach_affected_revision` | Each confirmation of the people affected: where it looked, the counts, a sealed note. Append-only |
| `breach_notice` | Each version of the five Rule 7(1) contents, sealed. A draft is editable; an approved one is frozen by trigger (`cmp_breach_notice_frozen`) |
| `breach_notice_delivery` | Every state of every attempt on every channel for every person. Append-only; `breach_notice_delivery_once` makes resends idempotent |
| `breach_ticket` | One per person per breach: the holder, who assigned it, what it opened with (sealed), the date to resolve it by (`answer_by`). Only the read markers and that date change, the date only with the event recording it, by trigger (`cmp_breach_ticket_read_only`) |
| `breach_ticket_event` | What happened to a ticket: returned (outcome, sealed summary), sent back, closed, withdrawn, reopened (each but close with a sealed reason), and a date changed (`date_before`, `date_after`, a sealed reason). Append-only |
| `breach_ticket_message` | The ticket's thread: office, holder or platform; sealed body and file name. Append-only |
| `breach_attachment` | A file kept with the incident: its kind, sealed name and note, where it is stored, its hash and size, who added it and when. A proof names its report (`report_id`), with the kinds `approval` and `sent_mail`. Append-only: never replaced or removed |
| `breach_report` | One version of one kind of report: who drafted it, and once each, who finalised it and when, and who recorded it as sent, when it was sent and the reference. One draft of a kind at a time, by partial unique index; frozen once finalised and again once filed, by trigger (`cmp_breach_report_frozen`) |
| `breach_report_section` | A report's words, a section at a time, sealed. Frozen with the report (`cmp_breach_report_section_frozen`), and a finalised report gains no section (`cmp_breach_report_section_no_late_words`, 0063) |
| `breach_report_addressee` | Who a finalised version was sent to (0064): one row per report and list entry, and whether that entry was mandatory when the version was finalised. Written before the version is frozen and never after (`cmp_breach_report_addressee_no_late_names`); append-only. Policed through its report |
| `breach_report_delivery` | Every state of every attempt to mail a report to one of its addressees, shaped like `breach_notice_delivery`; a failure's error class, never the address. Each names an addressee of its report, by foreign key (`breach_report_delivery_addressed`, 0064), so nothing is mailed to anyone a version was not addressed to. A lost mail takes a new attempt, not the same row. Append-only |
| `breach_board_recipient` | An address on the organisation's board's list: name and email sealed, a blind index, who added it and, once, who took it off; since 0064 `mandatory`, and `one_off` for an address a sender added for one report alone, which is never on the list, never mandatory and never taken off. One listed row per address, by partial unique index leaving one-offs out. Only the removal, once, and the mark change, by trigger (`cmp_breach_board_recipient_read_only`); never deleted. Not an office's |
| `breach_board_recipient_event` | Each time an entry was made mandatory or optional again, by whom and when (0064). The entry's `mandatory` moves only with one of these. Append-only; not an office's, like the list |
| `breach_settings` | One row: the roles told of a report from the public link. Not an office's |
| `incident_report` | A report from the public link: who sent it and what they said, sealed; the blind index of the address (`reporter_email_hash`, 0065); its `INC-` number; and its one outcome, claimed (`breach_id`) or dismissed with a sealed reason. Nothing but the outcome changes, once, and a dismissed report's reporter is erased once under a rights request - the name, the address and its index blanked, with when, by whom and under which request - by trigger (`cmp_incident_report_outcome_once`) and CHECKs; never deleted. No office and no policy: both offices see it until it has its outcome |
| `breach_temporary_access` | One grant of a temporary login: whose, on which breach, through which ticket, whether the account was made for it, the role it held before, who granted it, and - once - when, by whom and why it ended (`breach_closed`, `request_closed`, `ticket_withdrawn`, `reassigned`, `account_deactivated`). Since 0049 a grant may instead be for a rights ticket, `holder_id`, with `breach_id` and `ticket_id` then empty - exactly one of the two, by CHECK. One open grant per person per breach, or per rights ticket, by partial unique index; the end is written once and nothing else changes, by trigger; never deleted |
| `breach_affected` | Each person listed, once per breach (`breach_affected_once`), with the revision that first listed them and what put them there - a project or activity, exports, assets, an uploaded list (`found_by` project, processor, data_source, upload, dpo) or, on people listed before they stopped being a way to look, tables (`platform`), never a value. Append-only |
| `breach_upload` | Each list taken (0045): people or assets, its sealed file name and hash, and what it came to - rows read, matched, new contacts, skipped, unreadable, untraceable. The file is not kept. Append-only |
| `breach_contact` | Somebody affected with no account (0045): name, email and mobile sealed, with blind indexes so each is listed once per breach. Append-only. A delivery addresses an account or one of these, exactly one (`breach_notice_delivery_one_recipient`), and never writes a contact to an account (`breach_notice_delivery_portal_is_an_account`) |

Every write takes the breach row first (`FOR UPDATE`), so two people recording
at once act one after the other: two determinations of *yes* sent together
create each duty once and issue one breach reference.

## The trail

Every change writes an audit row against `breach`: `breach.recorded` (an
incident logged - the key predates the incident-first order), `.determined`,
`.confirmed` (recorded as a breach, with its BR), `.assessed`, `.cert_in_marked`, `.cert_in_set_aside` (that a reason was given), `.obligation_created`,
`.obligation_completed`, `.obligation_not_applicable`,
`.obligation_reinstated`, `.obligation_extended`, `.affected_revised` (with the counts, and nobody's name or id), `.affected_uploaded` (a list taken: its kind and counts), `.obligation_reopened`, `.notice_drafted`, `.notice_edited`, `.notice_approved`, `.notice_sent` (with counts), `.closed`, `.reopened`, `.attachment_added` (the kind, never the name), `.attachment_read`, `.report_drafted`, `.report_edited`, `.report_finalised` (how many addresses were mailed, whether it is held, how many were added for that report and how many on the list were left out), `.report_resent` (how many it queued, how many of them for the first time and how many again, and only if it queued any), `.report_released` (a report to CERT-In held for the first *yes* and sent then: how many queued, how many left out because taken off the list), `.report_withheld` (the same report not sent at that *yes*: `why` is `cert_in_set_aside`, CERT-In being set aside then, or `nobody_on_the_list`, everybody it was chosen for having been taken off the list since, with how many were left out), `.report_proof_added`, `.report_filed`, `.report_read` (each with the kind and the version). `.obligation_completed` says which duty, whether late, and `by` - `delivery`, `earlier_mail`, `try_again` (a person's press, who is the actor), `filing` or `filed_report` - with the report's version where a report did it, and for the board how many were reached; never whom. A report from the public link is against `incident_report`: `incident_report.received`, `.claimed` (with the office), `.dismissed` (that a reason was given), `.reporter_erased` (its reporter's name and email blanked under a rights request: the request's reference and the INC, never a name or an address; it carries the request's office, not the report's, so it is on that office's trail and the person's own when they have an account, and never on the other office's). A change under Breach settings is `breach_settings.changed`, with what changed - an address added or removed, made mandatory or optional again - and the entry's uuid, never naming an address. A breach ticket's events are against `breach_ticket`, with the holder as subject: `breach_ticket.assigned`, `.message`, `.returned` (with the outcome), `.sent_back`, `.closed`, `.withdrawn`, `.reopened`, `.date_changed` (with the two dates), `.file_read`, `.colleague_added` (with the adder's ticket's uuid); the administrator's trail names them by the breach reference only. A breach-only login's grant and end are against the account: `user.temporary_access_granted` and `user.temporary_access_ended`, with the breach reference and the cause, never a name or an address. Each person whose account a notice is written to gets `breach_notice.delivered` against her, naming the breach reference (the BR) and the version: that is her portal's notification, and the only breach event she is shown. The
detail carries the reference, the outcome, which duty, a due time and that a
reason was given - never the office's words, which are sealed on their rows
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).

## Open questions

Owned by people, and not decided by the code. The product owner answered six on
2026-11-07 ([ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md#amended-2026-11-07-the-product-owners-answers)):
who a report goes to, a CERT-In mark set aside at any time, an earlier mail and an
earlier filing counted at a later *yes*, a dismissed reporter's rights, and a report
to CERT-In held for a *yes*. Two readings of those answers are settled, not open: a
held report to CERT-In survives a *no* and goes at the first *yes*, and never if the
incident is never validated *yes*; and the earlier work a *yes* counts is the first,
as it would have counted with no *no* - the first finalised version of the board's
report that reached somebody, or the first filing ordered by when it was recorded
and then by version.
The last four rows are what the review of 2026-11-08 left for an owner.

| Question | Owner |
|---|---|
| Whether an event is a personal data breach - above all a leak of sealed data whose key was not exposed | Legal |
| The internal target for "without delay" | Legal and the Programme |
| Who answers principals' questions (Rule 7(1)(e)) | Legal |
| Who files with CERT-In - the officer or corporate security. Today only the officer of the breach's office can record it | Security and Legal |
| Notices to the people affected that were delivered while a *no* had set their duty aside: the same situation the owner answered for the board's mail. Not built: the *yes* brings the duty back and it waits for somebody to press **Send** again, which then completes it. The same rule would complete it at the *yes* | The product owner |
| A regulator's own mailbox - CERT-In's or the DPDP Board's - on the board's list or added for one report. Nothing refuses it, so the platform would mail the regulator a report, against [ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md), under words that say it has not gone to one. Which domains to refuse is to be named | Legal or the product owner |
| A dismissed report's reason and who dismissed it are left out of the reporter's access package, as the office's notes on a request are. Whether s.11 asks for the office's reason | Legal |
| Nothing expires a dismissed report: it is kept until a rights request erases its reporter. Whether a retention period should apply | Legal |
| A claimed report is not reached by an access or erasure request, a documented exception: it is the incident's record of what the office was told, and may sit in the other office's register ([personal-data.md](personal-data.md#personal-data-breaches)) | Legal and the product owner |
| A dismissed report's words stay after its reporter is erased, and may name them; once the index is gone a later request cannot reach them | The product owner |
| The portal's public promise on the report page and in its help, that a person whose report is closed without being taken up can ask for their name and email to be erased from it. Planned as "If your report is closed without being taken up, you can ask for your name and email to be erased from it."; the words to confirm are the page's own (`frontend/portal/src/app/report-incident/page.tsx`) | The product owner, to confirm |
| The administrator may answer an access or erasure request about the office, and the response package they release and can download (`GET /requests/{uuid}/download`) carries the requester's own dismissed reports - their name, email and words - although the register is hidden from them everywhere else (`public_reports` null, the erase 404; on an erasure, `complete_blocked_by` tells them only the DPO or the Legal office can take the name and email off). Whether that part is answered only by an officer (the response refused to the administrator while such reports are found), or left out of a package the administrator releases ([rights-requests.md](rights-requests.md#reports-from-the-public-link)) | The product owner |
| `POST /rights/requests/verify` answers every failure in the same words, but not in the same time: a reference with no account costs a key-service call (the contact it gave is opened to look for a dismissed report) that one with an account does not, and a reference a code was issued for costs a Redis call a stranger's does not. So how long a reply takes can still say something about the contact. Not equalised | The engineering lead |
| A request with no account whose contact is a mobile, verified by hand, is answered by text, and a text carries only the headline, never the Privacy Office's words or the digest; with no account to sign in to, that text is the whole answer. Whether it should carry them, or the answer go another way | The product owner |
| `users.by_contact` takes an account's own email even when it was never proved. A public-form request from the real owner of an address that somebody else's account carries unproved is attached to that account, and its code goes to that address. Since 2026-11-08 such a request finds none of the owner's dismissed reports, which is safer than handing them to the other account but does not serve the owner. A request with no account verified by hand still finds and erases reports by the email it gave, unproved; `code_channel` now steers the officers to a code instead | The engineering lead and the product owner |
