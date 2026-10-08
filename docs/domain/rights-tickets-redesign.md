# Rights request tickets: the redesign (2026-10-08)

[Rights requests](rights-requests.md)

The DSAR holder tickets worked, but grew one action at a time: up to seven
equal buttons a row, a "Next" that could lead into a dead end, answers that
counted the moment they arrived, external holders with no way to answer but
email, and words like *derive*, *escalate* and *collating*. Breach tickets,
built later, already do most of this better. Decided with the product owner on
2026-10-08:

| Question | Decision |
|---|---|
| External holders (vendors, third-party processors) | Answer through a **link on the external portal**, confirmed by a one-time code; no account |
| Internal holders | **As breach tickets**: the ticket in the console's *My tasks*; somebody without a console login gets a temporary one |
| Does an answer count at once? | **No**: the DPO reviews it, then **Accepts** it or **Sends it back** |
| Email content | **Full detail** to internal holders; **a link only** to external ones |
| Reminders | **Manual**, and **automatic every day** while a ticket is overdue and unanswered (and three days before, and on the day) |
| Scope | In two phases |

## Phase 1: the DPO's card, the review step, plain words, My tasks

Done on 2026-10-08.

| # | Change | Where |
|---|---|---|
| 1 | **The server says what a ticket may do next.** Each holder carries its `state` in plain words and its `moves`, each with a label, whether it is the main one, whether it needs a reason, whether it sends an email. The console draws buttons from that, never from a copy of the rules | `domain/rights/tickets.py`; `HolderOut.state`, `.moves`, `.overdue` |
| 2 | **One table, one ticket dialog.** Holder · State · Due · Last activity · Next action; the row opens the ticket: what it was asked (the brief and the instruction, no longer hidden), the thread, the answer, and its actions - the main one first, the rest under *More* | `holders-card.tsx` |
| 3 | **A guided path.** Find who holds the data → Choose who answers → Send tickets → Wait for answers → Review answers; only the current step's controls show | `holders-card.tsx` |
| 4 | **A review step.** An answer arrives as *Answered - review*; the DPO **Accepts** it or **Sends it back**. Only an accepted answer counts toward closing the request or toward an erasure being done. Partly done and could not do are amber and red, never a green "Returned" | migration 0048 `accepted_at`; `settle`, `execution`, `erasure` |
| 5 | **Reopen** a withdrawn ticket, with a new date; the holder is told | `reopen_ticket` |
| 6 | **Remove** a holder found by mistake, while nothing has been sent to it | `remove_holder` |
| 7 | **Plain words.** States: *Not confirmed · Not sent · Waiting · Overdue · Final reminder sent · Answered - review · Accepted · Sent back · Withdrawn · No answer*. *Escalate* is **Send final reminder** (confirmed before it sends); *Derive from the records* is **Find who holds the data**; *on the portal* is **in the console**; no table names on screen | console `features/rights` |
| 8 | **The Next link is right.** While confirmed holders have no ticket yet, the next step is *Send tickets*, and the request cannot move to collating past them | `state_machine.py`, `request-summary.tsx` |
| 9 | **One rule for overdue**, the server's: overdue once the due date has passed (the end of that day); a final reminder only then | `tickets.py` |
| 10 | **Nobody left guessing.** The holder is told when the office records or accepts their answer; the person a ticket is moved away from is told; a holder cannot write on a closed request | `service.py` |
| 11 | **Daily reminders** while overdue and unanswered, from the nightly sweep | `sweep_tickets` |
| 12 | **My tasks for holders.** *To do · Waiting on the office · Done*; a clear *Submit your answer* form - what was done, then a summary, then a file; the dialog stays open after a message; withdrawn and no-answer tickets say so | console `tickets/page.tsx` |

## Phase 2: external holders on the portal, internal without a login, per-holder instructions

Done on 2026-10-08 (migration 0049; [rights-requests.md](rights-requests.md#how-a-holder-is-reached)).

| # | Change |
|---|---|
| 1 | An external holder's email carries **only a link** to the **external portal**. They confirm with a one-time code sent to the address on the ticket, then read what is asked, answer (done, partly done, could not do), attach proof, and message the office - all on one page, no account |
| 2 | An internal holder with no console login gets a **temporary login**, as breach tickets do (S3-09), and the ticket in *My tasks* |
| 3 | Each holder gets **its own instruction**, prefilled; for an erasure, the ticket lists exactly which items to erase, redact or keep |
