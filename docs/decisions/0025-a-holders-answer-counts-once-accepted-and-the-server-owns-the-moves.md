# 0025. A holder's answer counts only once the Privacy Office accepts it, and the server owns a ticket's moves

**Status:** accepted · 2026-10-08. Migration 0048, commit c59d9da. Amends
[ADR 0019](0019-erasure-reaches-every-store-but-the-record.md) (the holder's
copy is done on an accepted answer).

## Context

A rights ticket's answer counted the moment it came back. A holder pressing
Return settled the request toward collating and, for an erasure, marked the
holder's copy gone, though nobody at the office had read what it said. The
2026-10-01 review had already found the worst case, a return saying "unable
to erase" closing a request complete (DPDP-1); the fix there, an outcome on
every return (migration 0037), still took the holder's word unread.

The console also drew each holder's buttons from its own copy of the rules:
up to seven of equal weight on a row, a "Next" that could lead into a dead
end, and an *Escalate* that appeared at noon on the due day because the
browser and the server disagreed about what overdue meant. Breach tickets,
built later, already took their moves from the server
([ADR 0023](0023-breach-tickets-and-breach-only-logins.md)).

## Decision

Decided with the product owner on 2026-10-08
([rights-tickets-redesign.md](../domain/rights-tickets-redesign.md)).

- **An answer waits for review.** A holder's answer arrives as *Answered -
  review*. The DPO **accepts** it (`accepted_at`, `accepted_by` on
  `rights_request_holder`) or **sends it back** with a reason. A CHECK holds
  that only a returned ticket can be accepted.
- **Only an accepted answer counts.** It counts toward moving the request to
  collating (the state machine refuses while an answer is waiting for
  review) and toward an erasure's holder copy being done
  (`domain/rights/execution.py`, `returned_done`, `returned_short`;
  `domain/rights/erasure.py`). An accepted answer saying *partial* or
  *failed* is still not done: the store records *failed* with the holder's
  word, as ADR 0019 already said.
- **An answer the office records itself is accepted as recorded.** The
  office wrote it, for a holder reached by email, so reviewing its own words
  would be ceremony.
- **Partly done and could not do are never shown as success.** They read
  amber and red, never a green "Returned".
- **Sending back stays open after acceptance.** While the request is still
  being worked, an accepted answer can be sent back; sending back clears the
  acceptance and what the holder said.
- **Overdue is one rule, the server's.** A ticket is overdue once its due
  moment has passed (`domain/rights/tickets.py`, `overdue`). The console
  sends the end of the chosen day, so a ticket due today is overdue
  tomorrow.
- **A final reminder only once overdue.** *Send final reminder* (formerly
  *Escalate*) is refused before then (`ticket_not_overdue`) and is sent once.
  After it the response may go out partial, naming the gap.
- **Reminders run on their own.** The nightly sweep reminds a ticket three
  days before its date, on the day, and every day while it is overdue and
  unanswered, at most once a day (`sweep_tickets`). The office can remind by
  hand as well.
- **The server says what a ticket may do next.** Each holder carries its
  `state` in plain words, whether it is `overdue`, and its `moves`: each
  with a label, whether it is the main one, whether it needs a reason or a
  date, and whether it sends an email, so the console asks before it does.
  The console draws its buttons from that and holds no copy of the rules.
  The holder's own view (*My tasks*) gets the same states in its own words.
- **Nobody is left guessing.** The holder is told when the office records or
  accepts their answer; whoever a ticket is moved away from is told; a
  holder cannot write on a closed request.

Returns already in the database when 0048 ran were marked accepted as of
their return, so nothing that had settled unsettled.

## Consequences

- A request takes one more step to reach collating: every answer must be
  read and accepted or sent back. The step is the point. The cost is the
  DPO's time between an answer arriving and their review of it.
- An erasure can no longer be recorded done on a holder's say-so alone. It
  is done on the holder's word *and* the office's acceptance of it. That is
  still not proof the copy is gone (ADR 0019); it is a person at the office
  having read the claim.
- A ticket's state is now worked out on the server, in one place, for the
  console's card, its dialog, the holder's *My tasks* and the outside
  holder's page ([ADR 0024](0024-a-rights-tickets-holder-is-reached-three-ways.md)).
  A change to the rules is a change to `tickets.py` and its tests.
- The console can no longer disagree with the server about a date, because
  it never computes one.
- Daily reminders mean an overdue holder hears from the platform every day.
  A holder who has said they cannot answer by the date should be given a new
  one, or the ticket sent back with a later date.

## Revisit when

The office wants some answers to count without review - for a trusted
holder, say, or an access request where nothing is changed; the daily
cadence proves too much for holders; or a holder integration (S4-03) brings
answers the office can check by machine rather than by reading.
