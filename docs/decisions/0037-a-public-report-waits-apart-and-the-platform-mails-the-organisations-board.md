# 0037. A public report waits apart, the organisation's board is told on a yes by the platform's mail, and a regulator's duty completes only with proof

**Status:** accepted · 2026-11-06; amended 2026-11-07 (a CERT-In mark set aside,
and what the review of the work changed, at the end); amended again 2026-11-07
(the product owner's six answers of that day, which confirmed and widened the
set-aside, [at the end](#amended-2026-11-07-the-product-owners-answers)); corrected
in place 2026-11-08, where a review of what the answers built found these words and
the code apart. Migrations 0058 to 0065: 0058 to 0063 for the product owner's nine
items of 2026-11-06, 0064 and 0065 for the answers. The answers also reach
[ADR 0019](0019-erasure-reaches-every-store-but-the-record.md), whose erasure now
reaches a dismissed report from the public link, and
[ADR 0026](0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md),
whose "everything held" includes it. Amends
[ADR 0021](0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md)
and [ADR 0022](0022-an-incident-first-and-a-breach-on-a-yes.md): the clause that
the platform never reports to the organisation's board, which ADR 0022 added to
ADR 0021's account of where the platform ends, is reversed, and ADR 0022's board
duty moves. ADR 0021's rule that the platform never submits to a regulator
stands. It also changes two details elsewhere:
[ADR 0023](0023-breach-tickets-and-breach-only-logins.md), whose ticket row now
moves its date with the event that records it, and
[ADR 0029](0029-copies-and-files-never-on-a-code-a-link-or-her-own-record.md),
whose list of emails that may carry a file gains the two mailed to the board.
Numbered 0037 because 0036 is taken on the unmerged DataVault branch.

## Context

Five things in the breach workflow had stopped matching how the office works.

**Nobody outside the office could report anything.** Only an officer could log
an incident, so a member of staff, a vendor or a participant who saw something
had to find an officer first. ADR 0022 named that as a reason to revisit it.
The register could not simply be opened up: a `breach` row names the office
that holds it and the officer who logged it, and it is on the register the
moment it exists. A stranger's report has neither an office nor an officer, and
nothing should run on it until somebody has read it.

**A junk incident could not close.** ADR 0022 put the organisation's board's
duty on every incident at logging, thirty minutes from first noticed, and said
validation never touches it. So an incident validated *no*, or a report that
turned out to be nothing, stayed open with an outstanding duty until somebody
told the board about an event that was not a breach. The board was being told
of suspicions, and the office was recording that it had.

**The board was told by hand.** The platform drafted a brief, a person passed
it on through an offline channel, and the DPO recorded when and to whom. The
team wants one button: draft it, submit it, and the registered addresses are
mailed.

**A regulator's duty completed on somebody's word.** *Record submission* took a
time and a reference, and ADR 0021 said plainly that the evidence was only as
good as that entry. What was sent was not kept: the Board's documents were
drafted from the register as it stood whenever they were opened, so nothing
held what a person had actually read, approved and filed.

**People were found by table.** A breach of the platform's own database asked
the DPO to tick the tables affected. People running a breach know the project,
the activity or the vendor it reached. They do not know the schema, and they
cannot be asked to. Separately, a list of the people affected had to arrive as
a CSV when everybody who sends one sends a workbook, and a ticket's date, fixed
at assignment, could only be missed.

## Decision

- **A public link, and a report that waits apart from the register.** One link,
  `/report-incident` on the portal, for anybody, with no account. The reporter
  gives a name and an email proved by a code (`POST /incident-reports/code`,
  then `POST /incident-reports` with it). There are no anonymous reports. What
  arrives is an `incident_report` row, not a `breach` row, with its `INC-`
  number from the sequence the register draws on. It sits in a **shared
  intake**, in no office, on no clock, and both offices see it. Everyone in the
  roles named under **Breach settings** is mailed that it has come, and nothing
  of what it says: the two officers always, and any role the administrator, the
  DPO or the Legal PoC adds.
- **It waits apart because a report is not yet anybody's.** In `breach` it would
  need an office it does not have, sit on a register both offices are walled
  from each other's half of, and need every reader of that register to skip
  it. Apart, junk never reaches the register at all. An officer **claims** it,
  which logs an ordinary incident in that officer's office under the same
  number, first noticed being when the report arrived; or **dismisses** it,
  with a reason, and the report stays: a rights request from the reporter finds
  it, and an erasure request blanks their name and email
  ([amended](#a-dismissed-report-and-the-rights-of-the-person-who-sent-it)).
  Both officers can read what was dismissed, with who did it and why, whichever
  office it was, so a report that was the other office's can still be raised. The outcome is written once, by
  trigger.
  Whatever the reporter said about a cyber attack or when they noticed it is
  kept beside the incident and starts nothing: a stranger's word creates no
  duty. The office marks CERT-In once it has read the report.
- **The organisation's board's duty starts at a validation of yes.** Created by
  the first *yes*, due `BREACH_ORG_BOARD_MINUTES` (30) from that validation,
  the moment there is something to tell it. Not first noticed, and not the
  awareness time, which is entered and may be hours earlier. No duty exists on
  logging. A later *no* sets it aside with the three DPDP duties, and a later
  *yes* reinstates it with a new thirty minutes, and if its own report reached
  the board while it was aside, that *yes* completes it from that mail
  ([amended](#what-a-yes-finds-already-done)). The reason is the one above:
  an incident that is junk or validated *no* must be able to close without
  telling the board anything.
- **The platform mails the organisation's board.** This reverses the clause
  that it never does. **Notify Organization Board** opens a
  report drafted from the register; submitting it finalises it and queues a mail
  to the board's list, kept under Breach settings by the administrator, the DPO
  and the Legal PoC: since the owner's answers, to the addresses the sender
  chose from it in the window, with any added for that report alone
  ([amended](#who-a-report-goes-to)). **The duty is done when the mail
  lands, not when it is queued**: once every address has its outcome and somebody
  was reached, it completes, naming those reached and nobody else. A mail that
  reaches nobody leaves it outstanding, and its overdue alert fires. Each address
  has a delivery account like a notice's. Sending again tries the addresses the
  version went to that it has not reached, and never one taken off the list,
  whatever was waiting for it. As first built it also tried any address added to
  the list since; the answers took that out. The report's words are quoted in the
  mail: they are somebody's words, so a link or a code in them stays text and
  becomes no button.
- **The platform still never sends to a regulator.** ADR 0021 stands. A person
  sends to the DPDP Board and to CERT-In through those bodies' own channels, and
  the platform keeps the proof and the reference. A source test holds that
  nothing in the breach code imports a way to reach anywhere else, and that a
  report's task delivers only the two messages addressed to the board's list.
- **Reports are drafted, finalised and filed, and filing needs both proofs.**
  Four kinds go the regulator's way, each its own draft on its own versions:
  the initial intimation, the report to CERT-In, the 72-hour report and a
  closure report. A draft starts from the register and is the office's to
  rewrite; it is never regenerated underneath them. **Finalising** freezes the
  words, by trigger, and mails the organisation's board for its information: it
  does **not** mail the DPDP Board. A person then sends it, and attaches the
  **proof of internal approval** and **the mail sent to the regulator**.
  **Filing** records when it was sent, which may be before it was finalised here
  if a person sent it first, and the reference returned; it is refused without
  both proofs, and it completes the duty. The closure report is optional,
  discharges no duty and never stands in the way of closing.
- **The by-hand route is gone.** `POST /breaches/{uuid}/obligations/{duty}/complete`
  is removed, so that no regulator's duty can complete without its proof. The
  organisation's board's duty completes by its report's mail, the principals'
  by delivery, and the regulators' by filing: at the time, or, for a duty a *no*
  had set aside meanwhile, at the *yes* that brings it back
  ([amended](#what-a-yes-finds-already-done)). Nothing else writes a completion.
  Taking the route away also took the only way out of a CERT-In mark made in
  error, which the amendment at the end puts back.
- **Tables are removed from finding people.** The office finds the people
  affected by project or activity (everyone who gave consent in it, in a period
  if one is given), by vendor (everyone in files exported to it, and everyone in
  an HR activity whose category names it), by data source, from an Excel list of
  name, mail ID and mobile number, or by adding one person. What was derived from
  tables is not offered any more; people listed that way stay listed, and
  `breach_affected.found_by` keeps `platform` for them. "Who it touched" becomes
  "Affected people" on the card, and the people affected wherever else a person
  reads it. A list arrives as an Excel workbook, from the template, and a CSV is
  still taken.
- **A breach ticket's date may move, with a reason.** Its holder or the office
  may change it, saying why, with no approval. The date before, the date after
  and the sealed reason go on the ticket's events and thread, the two dates on
  the trail, and the other side is told. A trigger refuses a new date that no
  event records. The label is **Resolve by**, on breach tickets only: a rights
  ticket's date is the rights clock's, and does not change.

## Consequences

- The public link is a new unauthenticated write. It is limited per address and
  per contact, and nothing is stored until the code comes back, so a stranger
  who never answers leaves no row. A determined reporter with a real mailbox can
  still fill the intake, and each report costs an officer a sentence.
- Until a report is claimed both offices can read it, so a matter that turns out
  to be the Legal office's has been seen by the DPO office, and the other way
  round. That is the price of nobody having to route it first.
- The board hears nothing of an incident until a *yes*. A report to CERT-In may
  be written and finalised on the mark alone, whatever validation says, because
  its six hours wait for neither, and finalising any report mails the board
  (item 3 of the product owner's nine). As first built, that let the board read a
  whole report, under an `INC-` number, on an incident later validated *no*; since
  the owner's answers its mail is held for the first *yes*, and never sent if none
  comes ([amended](#a-report-to-cert-in-before-a-yes)). So a long validation is a
  long silence towards the board, while CERT-In's six hours from first noticed run
  regardless. The policy's owner has chosen that.
- A report finalised for a regulator goes to the board in full, in the mail and
  as a PDF, outside the sealed register. The 72-hour report's section on the
  person who caused the breach is drafted from the assessment's findings and may
  name an employee, and every address it is sent to reads it. Only the board's own
  report starts out naming nobody. That is what telling the board of every report
  costs, and why neither mail may be copied.
- The board's list is one list, which both offices and the administrator keep. A
  report on either office's breach is offered to every address on it, so an
  address one office added reads the other office's reports, across the wall
  between them. Anyone who keeps the list could add an address, their own
  included, and the administrator, who sees no breach, would then be mailed the
  reports. An entry is checked only as an address, and the trail records a change
  and never which address. The product owner kept the one list on 2026-11-07, and
  answered the rest: the sender sees every name and address before a report goes,
  and both officers are mailed every change to the list, by name and address
  ([amended](#who-a-report-goes-to)).
- Incidents logged before this keep their duty and its stored due time, because
  a due time is never recomputed. Theirs is set aside by a *no*, or is done like
  any other; one already validated *no* and still outstanding was set aside by
  0063, since nothing short of a *yes* could complete it. Completions already
  recorded stand.
- Finalising needs an address to send to. As first built that meant somebody on
  the board's list; since the answers an address for that report alone will do,
  so an empty list no longer holds up the board's thirty minutes, and the list
  should still be filled before the first breach, not during it.
- A filed duty needs two files in hand. A regulator's duty that was met on time
  shows outstanding, then overdue, until somebody files it. `filed_at` is the
  time entered and may be earlier than the filing, as a submission's was, and
  earlier than finalising: a person may have sent the report first.
- A finalised report cannot be corrected, only followed by a new version, and
  each version mails the board again.
- The platform now holds the board's names and addresses. They are sealed, with
  a blind index so an address is listed once, and one taken off the list stays,
  because reports already mailed name it. An address added for one report alone
  is kept the same way, and never listed.
- `GET /breaches/{uuid}/board/intimation`, `/board/report` and
  `/org-board/brief` remain as the register's own views. They are not what is
  mailed or filed.
- A holder can move their own date without asking. The move is visible to the
  office, on the thread and on the trail, and that is the only check on it.
- The UAT cases for breaches, in `docs/uat/`, still walk the old screens.

## Revisit when

The DPDP Board or CERT-In offers an interface that could be filed through, which
ADR 0021's *Revisit when* already weighs; the board's policy changes its time or
its anchor; the intake fills with reports nobody can act on, when a harder gate
than a proved email is worth its cost; the product owner takes up the one board
list again, above: a list per office, or a limit on who may be added (the
addresses are shown to the officer before submitting since 2026-11-07); or the
Rules prescribe a form for the reports that the sections here do not follow.

## Amended 2026-11-07: a CERT-In mark set aside, and what the review changed

A review of the work above found one decision that had cost more than was seen,
and places where the mail and the intake did not do what this record says. None
of it needed a migration at first. Only the CERT-In rule, as the owner then
widened it, needed one (0064).

### A CERT-In mark made in error

**The product owner confirmed this on 2026-11-07, and widened it: a mark may be
set aside at any time** ([the answers](#a-cert-in-mark-set-aside-at-any-time)).

The removal of the by-hand route is why it was needed. A *no* leaves CERT-In alone
because it stands on its own test, and that route was the only way to end a duty
that should never have been there. With it gone, an incident marked by mistake, or
logged with *Yes* to *Is it a cyber attack?*, could close only by finalising a
report to CERT-In, which mails the whole of it to the board, then attaching proof
of a mail nobody sent and entering a reference nobody returned. Short of that it
stayed open and overdue. The reason the board's duty moved, that an incident that
is junk or validated *no* must be able to close without telling the board
anything, did not hold.

So **Not reportable to CERT-In** sets the duty aside
(`POST /breaches/{uuid}/cert-in/not-applicable`), with a reason.

- **At any time, whatever validation says**: before any validation, while it is
  pending, after a *yes* or after a *no*. As first built it waited for the latest
  validation to be *no*, and cited it; the owner's answer took that rule out
  ([below](#a-cert-in-mark-set-aside-at-any-time)).
- **With a reason, and nothing else.** The reason is the ground, sealed on the
  duty's event and shown on its row; the trail says only that one was given.
- **A duty done or a report filed stands** (409 `duty_not_outstanding`,
  `report_filed`). Something was reported.
- **It tells nobody.** It mails nobody and leaves validation, the organisation's
  board's duty and every DPDP duty alone.
- **Set aside, there is no report to CERT-In.** It cannot be drafted, finalised or
  sent again (409 `breach_not_recorded`), and a draft left open stays a draft. A
  report to CERT-In finalised before a *yes*, whose mail to the board waits for
  it, is not sent at that *yes* while the mark is set aside
  ([below](#a-report-to-cert-in-before-a-yes)).
- **Marking it again brings it back** on the same six hours from first noticed.
- **A later *yes* does not bring it back.** CERT-In stands on its own test; the
  officer marks it again.

### The mail to the board

- **The duty's time is when the board was first reached.** It still completes only
  once every address has its outcome, but what it records, and what `late` compares
  with the due time, is the earliest delivery. An address that took its retries past
  the thirty minutes does not make a duty met in time read late.
- **An address is one address.** Taken off the list and put back it is a new row of
  the list and the same person: what it was sent it is not sent again, and the
  report's account shows it once. Delivered under either row counts as reached.
- **A lost mail takes a new attempt.** A mail's account is only added to, so a new
  row is the one thing that can say it is moving again. The old task, if it ever
  runs, finds the later attempt and stands down.
- **One send to one address at a time.** Reading that no outcome is recorded does
  not stop two tasks that start together, as they do when workers come back from an
  outage. Each now claims the report and the address in Redis before it sends, for
  longer than a task may run and less time than a mail takes to read as lost. A
  task that loses stands down, unless the claim is its own: a worker killed
  mid-task comes back under the same task id, and takes it back rather than leave
  nothing alive to send the mail. A notice to a person affected claims the same way.
- **A mail that has gone is never sent again to get it on the record.** If the
  recording fails, a separate task retries the recording and nothing else, for about
  a quarter of an hour, and the claim is kept for an hour so that Try again stands
  down meanwhile. The account and the duty are two transactions, so a key service
  that cannot open a name for the duty cannot undo the account of a mail, and the
  recording takes no breach row, so it does not wait behind a list being uploaded.
- **An address taken off the list is waited for no longer, at once.** What was still
  queued to it is recorded failed and the duty is re-read, on reports of either
  office. Nothing is served to the person who took it off.
- **Try again says what it would do.** The server serves how many addresses it would
  queue, `mail.retryable`, and the same check refuses the press, so the figure and
  the button cannot disagree. It is none on a superseded version, on a report to
  CERT-In set aside, on a report to CERT-In whose mail waits for a *yes* (409
  `report_held`, since the answers) and on a closed breach, and the press says how
  many it queued. It was also refused on an empty list (409 `no_board_recipients`)
  until the answers; that refusal is gone, since it tries only the version's own
  addresses and one added for that report alone is never off the list. It also
  re-reads the board's duty first, whatever follows: that is the way on when the
  re-read itself failed.

### The intake

The list is served a page at a time, 50 by default and 200 at most, oldest first,
each report by who sent it and its title. The rest of a report is read one report at
a time. The cost accepted above, a sentence for each junk report, did not cover the
list itself: served whole, about a hundred full reports passed what the console's
decrypt route can take in one request, and every report in the intake, the genuine
ones with them, then showed sealed in both offices.

### What this costs

- A report to CERT-In finalised after a *yes* and before the mark was set aside has
  been mailed to the board, and that stands. One finalised before a *yes* is held,
  and is not sent at the *yes* while the mark is set aside. Either takes no proof and is not
  recorded as filed until the mark is made again, when the same report completes
  the duty.
- A mark can now be set aside on an incident nobody has validated, or on a
  confirmed breach, to quiet a clock running late. The reason, the person and the
  moment are on the duty's event and the trail, and that is the only check on it,
  as it is on a ticket's date.
- A worker killed after a mail went and before it was recorded mails that address
  again when its message comes back, and so does a broker connection lost in the
  middle of a send, when the message comes back while the first run is still going.
  A task that stood down instead would lose every mail killed before it went, and
  the board's clock is thirty minutes.
- A regulator's report filed while a *no* has set its duty aside is a true record
  and is not refused, and it completes nothing then. The *yes* that brings the duty
  back completes it from that filing, by the owner's answer
  ([below](#what-a-yes-finds-already-done)).
- A duty a *no* set aside while its report's mail was on its way comes back on a
  *yes* with that mail already landed. The *yes* completes it from that mail, by the
  owner's answer, and mails nobody ([below](#what-a-yes-finds-already-done)).
- A delivery's time is when it was recorded, so a recording that had to be retried
  can make the duty's time a little later than the mail was.
- If the database and the broker fail together just after a send, the outcome is
  lost, and Try again can mail that address again once the hour's claim runs out.
- A notice to a person affected has the claim and nothing else here. A recording
  that fails after a notice is sent still escapes the task, and a lost notice is
  still queued again as the same delivery.

## Amended 2026-11-07: the product owner's answers

The six questions this record and its review had left open were answered by the
product owner the same day. Two migrations carry them: **0064** (who a report goes
to, mandatory addresses, and the CERT-In rule) and **0065** (a dismissed reporter
found and erased). Where the text above says otherwise, this section stands, and
the lines it changes point here.

### Who a report goes to

The answer to the one list (wall-1, security-2): it stays one shared list, and the
sender sees who is on it.

- **The window shows every name and address.** Finalising a report, from **Notify
  Organization Board** or any kind's **Finalise**, offers the whole list, every
  entry ticked (`GET /breaches/{uuid}/reports/recipients`). The sender may untick an
  entry for this send, or add an address for this report alone; the saved list does
  not change. What is sent is the list less what was unticked, plus those addresses
  (`{recipients, extra}`).
- **Who a version went to is frozen with it.** `breach_report_addressee` holds the
  set chosen, written before the version is frozen and refused after, by trigger.
  Every delivery names an addressee of its report by foreign key, so nothing is
  mailed to anyone a report was not addressed to. Reports finalised before this went
  to whoever their deliveries name, and that is what 0064 recorded for them.
- **An address for one report alone** is a row of the list's table marked
  `one_off`, sealed alike. It is never on the list, never mandatory and never taken
  off, so its mail always runs its course. An address typed that is already on the
  list is that entry, and two typed alike are one.
- **Mandatory entries.** The administrator, the DPO and the Legal PoC may mark an
  entry mandatory (`PUT /breach-settings/board-recipients/{uuid}/mandatory`). It
  then goes with every report finalised while it is set: leaving it out is refused
  (409 `recipient_mandatory`), and so is taking it off the list until it is made
  optional again. The mark moves only with a `breach_board_recipient_event` saying
  who moved it and when, by trigger, in 0061's idiom for a ticket's date.
- **Both officers hear of every change.** Adding an address, taking one off, and
  marking or unmarking one mail every active DPO and Legal PoC account,
  `breach_board_list_changed`, the one who made it included: who did what, the name
  and the address, and no breach, so it may cross the wall between the offices. An
  administrator who makes a change is not mailed, being no officer. The mail is the
  check the owner asked for, so a change it could not be queued for is refused (503),
  before anything is written. An unchanged mark records nothing and mails nobody.
- **Finalising needs an address, not a list.** An empty list with an address for
  this report is allowed; an empty list and none is 409 `no_board_recipients`; a
  list with nothing chosen is 422 on `recipients`. An entry taken off since the
  window read it is 409 `recipient_not_listed`, and the console reads the list again.
- **Try again tries the version's own addresses**: those it has not reached, a mail
  lost, or one never queued. An address added to the list since was never chosen for
  that version and is not mailed it; a new version reaches the list as it then
  stands. An address taken off the list is still not mailed, matched by blind index.

What it costs:

- A wrong or missing address is put right by a new version, which mails the board
  again, and not by Try again.
- An address chosen for one report is told to nobody else. Telling the other office
  would reveal that a breach exists. A sender who unticks every board member and
  sends only to an outsider meets the board's duty that way: a mandatory entry is the
  office's guard against it.
- Anyone who keeps the list can still add an address, their own included. What has
  changed is that both officers are told at once, by name and address.
- Nothing refuses a regulator's own mailbox, on the list or for one report, although
  a report mailed there would be a submission ADR 0021 says the platform never makes.
  Which domains to refuse is open ([breaches.md](../domain/breaches.md#open-questions)).

### A CERT-In mark set aside at any time

The owner confirmed **Not reportable to CERT-In**
([above](#a-cert-in-mark-made-in-error)) and widened it.

- **At any time, whatever validation says**: before any validation, while it is
  pending, after a *yes* or after a *no*. CERT-In stands on its own test and its six
  hours wait for no validation, so neither does knowing they were never owed. The
  first rule, only after a *no*, kept a mark standing on an incident still being
  validated, and on a real breach that was never a cyber incident it could not be set
  aside without a *no* the office did not mean. 409 `cert_in_not_validated_no` is
  gone.
- **With a reason, and nothing else.** The reason is the ground, sealed on the duty's
  event and shown on its row; the trail says only that one was given. The event cites
  no determination, since no validation set it aside, and a mark made again cites
  none either: there may be none yet. Migration 0064 lets a CERT-In duty's events
  stand without one, by trigger in place of 0034's CHECK, and keeps the rule for
  every duty validation moves.
- **A duty done or a report filed stands** (409 `duty_not_outstanding`,
  `report_filed`).
- **It tells nobody.** It mails nobody and leaves validation, the organisation's
  board's duty and every DPDP duty alone. An incident set aside before any
  validation still cannot close until it is validated.
- **Set aside, there is no report to CERT-In**, and a report to CERT-In whose mail
  waits for a *yes* does not go at that *yes* while the mark is set aside
  ([below](#a-report-to-cert-in-before-a-yes)).
- **Marking it again brings it back** on the same six hours from first noticed.
- **A later *yes* does not bring it back.** CERT-In stands on its own test; the
  officer marks it again.

What it costs: a mark can be set aside on an incident nobody has validated, or on a
confirmed breach, to quiet a clock running late. The reason, the person and the
moment are on the duty's event and the trail, and that is the only check on it, as
it is on a ticket's date.

### What a yes finds already done

A *no* sets aside what is not yet done, and a later *yes* brings it back on new
clocks. The work for it may have been done meanwhile, and the product owner's answer
(decisions 3 and 4) is that it counts. The *yes* does it at once, under the breach's
row, and mails nobody.

- **The board's own report that reached it** completes the board's duty at the
  *yes*, with no Try again. It is dated when that report first reached the board,
  names whom it reached, is recorded as the system's (`recorded_by` empty, the
  validator as the trail's actor, `by: earlier_mail`) and mails nobody. If several
  versions did, the first is recorded, as it would have been with no *no*: the
  oldest finalised version of the board's report that has run its course and
  reached somebody. A mail still on its way completes the duty when it lands. One
  that reached nobody leaves it outstanding on its fresh thirty minutes. A key
  service that cannot open a name for the duty leaves the *yes* standing and the
  duty outstanding, with `breach.board_duty_unsettled` in the log. Try again, on any
  version of the board's report, reads every version again, oldest first, and
  completes the duty from the first that reached somebody (`by: try_again`, the
  person pressing as the actor); a key service still away fails the press (503). The
  worker's re-read after any later outcome reads them the same way (`by: delivery`),
  so a later version that lands first is not the one recorded.
- **A regulator's report filed while aside** completes the initial intimation or the
  72-hour report at the *yes*, from when it was sent and the reference that came
  back, recorded as the filer's (`by: filed_report`). If several were filed, the
  first filing recorded is the one, by when it was recorded and then by version.
- **A filing is no longer checked against the duty's clock (logic-4).** A *yes*
  after a *no* starts it again at its own awareness, and the check refused a true
  date, on a field the form does not have. Filing is refused only in the future or
  before the incident was first noticed (422 on `filed_at`, "It cannot have been sent
  before the incident was first noticed").
- **CERT-In is out of reach**: a *yes* does not bring it back, and it can be neither
  filed while set aside nor set aside once filed.
- **Notices to the people affected** delivered while the *no* stood are not counted:
  the *yes* brings that duty back outstanding, and **Send** again completes it.
  Whether the same rule should reach them is open
  ([breaches.md](../domain/breaches.md#open-questions)).

What it costs: such a duty is checked against the clock the *yes* brings back, not
the one the *no* set aside. The board's earlier mail always reads on time, dated
before that clock started. A regulator's report reads late if it was sent after the
reinstated due, and its date may fall before or after that clock's start, since a
*yes* may enter any awareness from first noticed on. Nothing on the trail says the
first clock lapsed: its due stays on the duty's row and on
`breach.obligation_created`, and the *no* that set it aside on the duty's events. A
filing between first noticed and awareness is now taken. Duties a *yes* brought back
before this change are not swept: the board's completes from Try again, and the next
*yes* reads any duty again.

### A dismissed report and the rights of the person who sent it

The review of 2026-11-07 found (data-7) that a report from the public link an office
dismissed kept its reporter's name and email, sealed, with no way for that person to
ask what was held or to have it erased: no rights request looked there. The product
owner's answer (decision 5): a rights request finds it by the reporter's email, and
an erasure blanks the name and email, keeping the `INC-` number, the reason and who
dismissed it.

- **Found by the address's blind index.** 0065 gives `incident_report` the same
  index as `auth_user.email_hash`, written with the report and backfilled through the
  key service. Once identity is verified, an access or erasure request about
  everything held looks: by the account's email once a code to it came back (or, on
  an account from before each contact's proof was stamped, when neither is), and its
  second email once proved, or for a request with no account by the email it gave. An
  email never proved beside a mobile that was is not looked by: a nominee's account
  is made that way, with the address the principal typed, which may be somebody
  else's (2026-11-08). Only the two officers are shown what it finds, on the
  request's **Holders** tab. A response the administrator releases on a request
  about the office still carries the requester's own reports in its package; who
  should answer that part is open ([breaches.md](../domain/breaches.md#open-questions)).
- **Access** gives a requester with an account their own name, email and words, in
  the response package, with when the report was received and dismissed, and that it
  was not taken up. A request with no account has no package: it is answered by
  mail, with each report's number, dates and title only. Neither carries the
  office's reason or who dismissed it, as the office's other notes on a request are
  not shown.
- **Erasure is an officer's act on the request**
  (`POST /requests/{uuid}/public-reports/erase`), not an item: an item is a person's
  appearance in an asset, and a report is not one. It names no report; it finds them
  again by the index, so nothing a caller sends can reach another person's, and
  blanks the name, the email and the index in one statement. It needs an erasure
  request that has started, not confined to one consent, with no legal hold on the
  person; on a request with no account, none on any account the contact it gave is
  on, as an email, proved or not, or the mobile, whatever its role (2026-11-08).
  **Complete** waits until it is done, or the answer is partial. The trigger that
  writes a report's outcome once allows this one change, once. The mail answering a
  request with no account says of each report not yet erased that it still carries
  the name and email, says what is kept only once one was erased, and points at no
  account: the message is the answer.
- **A code to that address.** A request with no account matching a dismissed report's
  address is sent a code to the address the report came from, so the public form's
  neutral reply stays true for these reporters and the office need not verify them
  by hand. The request's detail tells the officers whether a code has somewhere to
  go (`code_channel`), never where. On the public form a wrong code, one of the
  wrong length and a spent budget of tries all answer as a reference no code was
  sent for does, so tries no longer tell a reporter from a stranger (2026-11-08);
  how long the reply takes still may ([breaches.md](../domain/breaches.md#open-questions)).

What it costs: the words stay, may name the reporter, and once the index is gone a
later request cannot reach them; the reason stays and may name them too. A report
that was claimed is not reached at all: it is the incident's record of what the
office was told, and it may sit in the other office's register, so neither request
surfaces it. Nothing expires a dismissed report: it is kept until a rights request
erases its reporter. Each of these is for Legal or the owner to revisit
([breaches.md](../domain/breaches.md#open-questions)). ADR 0019's "every store" and
ADR 0026's "everything held" now include these reports.

### A report to CERT-In before a yes

The answer to logic-6 and mail-11 (decision 6): the board's mail is held, and goes
unchanged at the first *yes*.

- **Finalising a report to CERT-In before the incident is recorded** records who it
  goes to and queues nothing. The version reads as held, and the button says so:
  **Finalise and hold for validation**. Try again is refused while it is held (409
  `report_held`).
- **The first *yes* sends it**: the newest finalised version, its words and PDF as
  frozen, to the addresses chosen when it was finalised, less any taken off the list
  since; nobody added or marked mandatory after it. The subject and the PDF carry the
  breach reference the *yes* issued. `breach.report_released` is on the trail.
- **A *no* keeps it held.** A mail is held exactly while the incident has no breach
  reference, and a *no* issues none, so it waits for the first *yes*, even after a
  *no*, and an incident that closes on a *no* never sends it. That is how "never if
  validation says *no*" was read: never while it stays *no*.
- **Set aside at the first *yes*, it is withheld**, with `breach.report_withheld` on
  the trail, and nothing sends it later by itself. Marked again, a person sends it
  with **Send to the board** (Try again) or writes a new version: an automatic send
  could mail the board a stale version beside the new one the office is likely to
  write. Set aside and marked again before the *yes*, it goes at the *yes* as though
  never set aside.
- **Nobody left to send it to.** If everybody it was chosen for has been taken off
  the list by the first *yes*, nothing goes, and the trail says withheld, not sent
  (`why: nobody_on_the_list`, with how many were left out; 2026-11-08). Try again has
  nobody to try; a new version reaches the list as it then stands. The withheld row
  reads *Report held for the board not sent at the validation* for either reason.
- **Only the newest goes.** An earlier version finalised before the *yes* was replaced
  before it went, and stays unsent.
- **After the first *yes*** the board has the breach and its own report, so a report
  to CERT-In finalised then, even during a later *no*, is mailed at once, as before.
- **Filing a held version** completes its duty; its mail still waits for the *yes*.

What it costs: through a long validation the board does not hear that a report to
CERT-In was written, while CERT-In's six hours run regardless; if no *yes* comes, it
never does.
