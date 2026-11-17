# 0042. An unclaimed report is escalated, a breach may change office, and the reporter is only acknowledged

**Status:** accepted · 2026-11-17. Migration 0073. Amends
[0037](0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)
(the shared intake) and [0032](0032-offices-are-logical-tenants-in-one-database.md) (a record's
office never changes).

## Context

The product owner asked for three things on 2026-11-17, all about an incident
between its arrival and an office's work on it:

- a report from the public link can wait in the shared intake for ever if
  neither office looks: management should hear when one is not taken up
  within half an hour, at addresses kept in settings, apart from the
  organisation's board;
- an office that claims a report, or logs an incident, sometimes finds it
  belongs to the other office. Until now a breach's office was fixed, so the
  only way was to close it and log it again, losing its clocks;
- the person who reported an incident need not be told what the office does
  about it: they may be nobody it touched.

## Decision

1. **Escalation is of a report nobody has claimed or dismissed.** Thirty
   minutes after a report arrives, if it still waits, every address on the
   escalation list is mailed, once per report. The mail gives the reference,
   when it arrived and how long it has waited - nothing of what it says, as
   the officers' own mail does not. The worker checks every minute. The
   report shows in the intake that it was escalated.
2. **The escalation list is its own list**: `breach_escalation_recipient`,
   kept on Breach settings by the administrator, the DPO and Legal. Being on
   the organisation's board puts nobody on it. With the list empty nothing is
   escalated and nothing is marked, so an address added later hears of what
   still waits.
3. **An incident or breach may be reassigned to the other office**, by an
   officer of the office that holds it, with a reason, while it is open. It
   goes as it stands: the row's office changes and nothing else - its
   reference, status, validation, duties and their clocks, people, notices,
   reports and tickets are untouched, and no clock starts again. It leaves the
   sender's register with the statement that moves it; the receiving office's
   officers are mailed with the reason. It may be sent back the same way.
4. **The database allows that one move and no other**:
   `cmp_breach_office_moves()` replaces the fixed-office trigger on `breach`,
   as `cmp_rights_request_office_moves()` did for a rights request (0055).
5. **The reporter is sent an acknowledgement, and no more.** On an incident
   that came from the public link an officer presses Send acknowledgement: a
   mail that thanks them and says the office is dealing with it. It may be
   sent again; each time is kept. The reporter is never sent the breach's
   reports or actions. If they are also a person the breach affected, they
   hear as every affected person does, by the notice.

## Consequences

- The trail of a reassigned breach is split: rows written before the move
  stay on the sending office's trail, since each row records the office the
  record had then and the chain is not rewritten. The breach's own history -
  status changes, validations, duties, reports - moves with it.
- The reassignment itself is one row, on the receiving office's trail. The
  sending office's trail has no row saying it left, and its bell may still
  list ticket events from before the move, whose links no longer open; the
  receiving office's bell does not show those earlier events.
- People already listed as affected stay listed after a move, though they
  were found through the sending office's projects. Finding more people uses
  the receiving office's projects.
- A running duty's alerts go to the receiving office from the next sweep.
- An incident the office logged itself is never escalated: an officer has
  it. Only the shared intake has nobody.
- A reporter of a dismissed report gets no acknowledgement beyond the one
  sent when the report arrived.

## Not decided here

- Escalating an incident an office holds but has not validated within some
  time. Today only the unclaimed report is escalated.
- A second, later escalation if a report still waits.
- A different waiting time per deployment: thirty minutes is in code.
