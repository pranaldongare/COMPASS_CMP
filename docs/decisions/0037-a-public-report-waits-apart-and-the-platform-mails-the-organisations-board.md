# 0037. A public report waits apart, the organisation's board is told on a yes by the platform's mail, and a regulator's duty completes only with proof

**Status:** accepted · 2026-11-06; amended 2026-11-07 (a CERT-In mark set aside,
for the product owner to confirm, and what the review of the work changed, at the
end). Migrations 0058 to 0063, the product owner's nine items of that date. Amends
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
  with a reason, and the report stays. Both officers can read what was
  dismissed, with who did it and why, whichever office it was, so a report that
  was the other office's can still be raised. The outcome is written once, by
  trigger.
  Whatever the reporter said about a cyber attack or when they noticed it is
  kept beside the incident and starts nothing: a stranger's word creates no
  duty. The office marks CERT-In once it has read the report.
- **The organisation's board's duty starts at a validation of yes.** Created by
  the first *yes*, due `BREACH_ORG_BOARD_MINUTES` (30) from that validation,
  the moment there is something to tell it. Not first noticed, and not the
  awareness time, which is entered and may be hours earlier. No duty exists on
  logging. A later *no* sets it aside with the three DPDP duties, and a later
  *yes* reinstates it with a new thirty minutes. The reason is the one above:
  an incident that is junk or validated *no* must be able to close without
  telling the board anything.
- **The platform mails the organisation's board.** This reverses the clause
  that it never does. **Notify Organization Board** opens a
  report drafted from the register; submitting it finalises it and queues a mail
  to every address on the board's list, kept under Breach settings by the
  administrator, the DPO and the Legal PoC. **The duty is done when the mail
  lands, not when it is queued**: once every address has its outcome and somebody
  was reached, it completes, naming those reached and nobody else. A mail that
  reaches nobody leaves it outstanding, and its overdue alert fires. Each address
  has a delivery account like a notice's. Sending again tries those not reached
  and any address added to the list since, and never one taken off it, whatever
  was waiting for it. The report's words are quoted in the mail: they are
  somebody's words, so a link or a code in them stays text and becomes no button.
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
  by delivery, and the regulators' by filing; nothing else writes a completion.
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
- The board hears nothing of an incident until a *yes*, with one exception: a
  report to CERT-In. It may be written and finalised on the mark alone, whatever
  validation says, because its six hours wait for neither, and finalising any
  report mails the board (item 3 of the product owner's nine). So the board may
  read a whole report, under an `INC-` number, on an incident later validated
  *no*: the telling of suspicions that moved its duty, in this one case. Short of
  that, a long validation is a long silence towards the board, while CERT-In's
  six hours from first noticed run regardless. The policy's owner has chosen that.
- A report finalised for a regulator goes to the board in full, in the mail and
  as a PDF, outside the sealed register. The 72-hour report's section on the
  person who caused the breach is drafted from the assessment's findings and may
  name an employee, and every address on the list reads it. Only the board's own
  report starts out naming nobody. That is what telling the board of every report
  costs, and why neither mail may be copied.
- The board's list is one list, which both offices and the administrator keep. A
  report on either office's breach reaches every address on it, so an address one
  office added reads the other office's reports, across the wall between them.
  Anyone who keeps the list could add an address, their own included, and the
  administrator, who sees no breach, would then be mailed the reports. An entry is
  checked only as an address, the trail records a change and never which address,
  and nobody else is told. The list was asked for as one list; this cost is the
  product owner's decision to revisit.
- Incidents logged before this keep their duty and its stored due time, because
  a due time is never recomputed. Theirs is set aside by a *no*, or is done like
  any other; one already validated *no* and still outstanding was set aside by
  0063, since nothing short of a *yes* could complete it. Completions already
  recorded stand.
- Finalising needs somebody on the board's list. An empty list refuses it, so
  the list has to be filled before the first breach, not during it.
- A filed duty needs two files in hand. A regulator's duty that was met on time
  shows outstanding, then overdue, until somebody files it. `filed_at` is the
  time entered and may be earlier than the filing, as a submission's was, and
  earlier than finalising: a person may have sent the report first.
- A finalised report cannot be corrected, only followed by a new version, and
  each version mails the board again.
- The platform now holds the board's names and addresses. They are sealed, with
  a blind index so an address is listed once, and one taken off the list stays,
  because reports already mailed name it.
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
list, above: a list per office, a limit on who may be added, or the addresses
shown to the officer before submitting; or the Rules prescribe a form for the
reports that the sections here do not follow.

## Amended 2026-11-07: a CERT-In mark set aside, and what the review changed

A review of the work above found one decision that had cost more than was seen,
and places where the mail and the intake did not do what this record says. None
of it needed a migration.

### A CERT-In mark made in error

**This is a decision made for the product owner to confirm.** The rule below is
what the platform does until they answer.

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

- **Only once the latest validation is *no*,** and the event cites that *no*. Until
  then there may be something to report (409 `cert_in_not_validated_no`). A mark
  cannot be withdrawn on an incident still being validated.
- **A duty done or a report filed stands** (409 `duty_not_outstanding`,
  `report_filed`). Something was reported.
- **It tells nobody.** It mails nobody and leaves the organisation's board's duty
  alone. The reason is sealed on the duty's event, and the trail says only that
  one was given.
- **Set aside, there is no report to CERT-In.** It cannot be drafted, finalised or
  sent again (409 `breach_not_recorded`), and a draft left open stays a draft.
- **Marking it again brings it back** on the same six hours from first noticed,
  citing the latest validation.
- **A later *yes* does not bring it back.** CERT-In stands on its own test, and if
  a *yes* did, a real breach that was never a cyber incident could not close,
  because setting it aside needs a *no*. The officer marks it again.

Two questions stay the owner's: whether a mark may be withdrawn without a *no*, and
whether a *yes* should bring it back.

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
  CERT-In set aside, on an empty list and on a closed breach, and the press says how
  many it queued. It also re-reads the board's duty first, whatever follows: that is
  the way on when the re-read itself failed.

### The intake

The list is served a page at a time, 50 by default and 200 at most, oldest first,
each report by who sent it and its title. The rest of a report is read one report at
a time. The cost accepted above, a sentence for each junk report, did not cover the
list itself: served whole, about a hundred full reports passed what the console's
decrypt route can take in one request, and every report in the intake, the genuine
ones with them, then showed sealed in both offices.

### What this costs

- A report to CERT-In finalised before the mark was set aside has been mailed to
  the board, and that stands. It takes no proof and is not recorded as filed until
  the mark is made again, when the same report completes the duty.
- A worker killed after a mail went and before it was recorded mails that address
  again when its message comes back, and so does a broker connection lost in the
  middle of a send, when the message comes back while the first run is still going.
  A task that stood down instead would lose every mail killed before it went, and
  the board's clock is thirty minutes.
- A regulator's report filed while a *no* has set its duty aside is a true record
  and is not refused, but it completes nothing, and a later *yes* brings back a duty
  that report can no longer complete. The way on is a new version, which mails the
  board again. Whether the *yes* should complete the duty from the report already
  filed is the owner's to say.
- A duty done stays done, but one a *no* set aside while its report's mail was on
  its way comes back on a *yes* with that mail already landed. It reads the same as
  a settling that failed, so **Try again** completes it from the earlier mail, dated
  before the duty came back, and mails nobody. A new version is still on the
  **Reports** tab. Whether the earlier mail should count is the owner's to say.
- A delivery's time is when it was recorded, so a recording that had to be retried
  can make the duty's time a little later than the mail was.
- If the database and the broker fail together just after a send, the outcome is
  lost, and Try again can mail that address again once the hour's claim runs out.
- A notice to a person affected has the claim and nothing else here. A recording
  that fails after a notice is sent still escapes the task, and a lost notice is
  still queued again as the same delivery.
