# 0023. Breach tickets reach internal staff only, through breach-only temporary logins that end with the breach

**Status:** accepted · 2026-10-05; amended 2026-10-06 (a holder keeps a read-only login - see the end); extended 2026-10-08 (rights tickets give the same login - see the end). Amends [ADR 0021](0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md).
Migrations 0040 (S3-08) and 0041 (S3-09).

## Context

A breach is handled by people the register does not reach: whoever runs the
system that leaked, whoever holds the access log, whoever can confirm a copy
was deleted. The DPO asked them by email and recorded nothing, so neither the
Board's report nor a later audit could say who was asked what, or what they
said. Rights requests met the same need with tickets (0013, 0017, 0020): one
per holder, a thread, a return, the DPO deciding. Some of the people a breach
needs have no console login at all - an engineer who is a data principal on
the platform, or nobody on it - and must act inside one breach without being
given the run of the console.

## Decision

- **Breach tickets work like rights tickets** (BD-03). The DPO assigns a ticket
  to a person with an instruction and an optional answer-by date (BD-20); both
  sides write on its thread, with files; the holder returns it saying *done*,
  *partial* or *failed*; the DPO sends it back, closes it, withdraws it or
  reopens it. **Only the DPO closes a ticket** (BD-07): the holder has no route
  to close, withdraw or reopen at all. A ticket's state is folded from
  append-only events; the ticket row changes only its read markers.
- **Only on a recorded breach.** A ticket reaches a person on the breach's
  account, so it waits for the first *yes* (ADR 0022, BD-10).
- **Internal staff only** (BD-06, BD-12). "Internal" is an address on
  `BREACH_TICKET_EMAIL_DOMAINS`, checked on the server for every assignee and
  every colleague; production refuses to start with the list empty or holding
  only the development domain. A refusal names the rule, never the address.
- **One ticket per person per breach** (BD-14), by unique constraint behind the
  breach row's lock.
- **The holder sees their ticket and nothing of the register** (BD-13): the
  breach reference, their instruction, the thread, the state, the answer-by
  date. The register still answers them 404. Their email says only that a
  ticket from the Privacy Office is waiting (BD-18).
- **A breach cannot close while a ticket is issued or returned** (BD-17).
- **The trail says what happened, never the words**: the ticket, an outcome,
  that a reason was given, with the holder as subject.
- **S3-09 - a person without a console login gets a breach-only login** (BD-04,
  BD-15, BD-16). The DPO gives a name, an email and optionally a mobile. An
  address already on a data principal's account gets temporary access on that
  account, role `breach_holder`, its previous role recorded; an address with no
  account gets a new one, `pending`, set up through the reset flow like any
  staff invitation. The role reaches its own tickets, the shared Tickets page
  and the personal pages, nothing else, and is never granted by hand. The
  grant ends when the breach closes or the DPO withdraws that ticket; the
  login stays, read only (amended 2026-10-06, below). An administrator's End
  temporary access removes it: an existing principal goes back to
  `data_subject`, an account made for the breach is switched off,
  `person_type` is never touched, and every session is revoked after commit.
- **A holder may add a colleague, who follows the same flow** (BD-05, BD-14):
  their own ticket, opening with the adder's note and not the DPO's
  instruction, under the same domain check and the same three-way lookup. The
  DPO sees every addition; there is no approval step.

This is **the one exception** to "an administrator provisions every staff
account" ([roles-and-access.md](../domain/roles-and-access.md)). It is bounded
to one breach, to internal domains, and to a role that can reach only its own
ticket.

## Consequences

- "Internal" is only as good as the domain list. A contractor on the
  organisation's domain is internal to this check.
- A holder's additions are visible to the DPO but not approved first; a holder
  can bring a colleague into a breach without asking.
- A breach-only login is a real account: it signs in with a password and the
  emailed second factor like all staff (ADR 0006), and outlives the breach
  unless an administrator removes it - switched off, never deleted.
- The Board's detailed report can now point at who was asked what, and what
  they said, from the register.
- As built in S3-09: the second factor is required for `breach_holder` in
  code (`requires_mfa`), not only by `MFA_REQUIRED_ROLES`, so a deployment that
  narrows the list cannot leave a platform-made login on a password alone. A
  person holding grants on two breaches keeps the role until the last one
  ends, and the first grant's previous role is carried to the second. A
  suspended account, or a member of staff whose account is not active, is
  refused rather than given a second way in. An administrator's resend of a
  pending holder's invitation sends `breach_ticket_access`, not the staff
  invitation.

## Revisit when

An HR directory can confirm employment, replacing the domain list; the team
wants the DPO to approve colleague additions; tickets are wanted during
validation, before a *yes* (one guard in `tickets.assign`); or temporary access
needs a time limit beyond the breach closing.

## Amended 2026-10-06: the team's answers

The questions this decision left open were answered by the team on
2026-10-06:

- **The domain list.** `cmp.local` for now; production needs the
  organisation's list in `BREACH_TICKET_EMAIL_DOMAINS` before go-live.
- **A holder keeps the account** (replaces BD-16's switch-off at the end).
  When the breach closes or their ticket is withdrawn, the grant ends and the
  login stays, so they can still read their ticket; every write is already
  refused on a closed or withdrawn ticket and on a closed breach. Somebody who
  also holds a real role keeps it, and their tickets with it. A second breach
  for a kept login sends the "ticket waiting" email, not a new password. The
  administrator's End temporary access is the one off switch, and does what
  the end of a grant used to do.
- **No approval of colleague additions**: it would cost time a breach does not
  have. The check is that a holder works only through the console - a code
  sign-in on the public portal is a data principal's session, which reaches no
  ticket (ADR 0013).

## Extended 2026-10-08: rights tickets give the same login

A rights request's holder inside the organisation with no console login is
given the same temporary login when its ticket is sent (migration 0049): the
same role, the same email, the same off switch. The grant is recorded in the
same table, against the rights holder (`holder_id`, with `breach_id` and
`ticket_id` empty - exactly one of the two, by CHECK), and ends when the
request closes, or the ticket is withdrawn or sent to somebody else. One
table keeps one answer to "who holds a temporary login, and why", and lets
End temporary access end them all. A holder outside the organisation gets no
login: it answers on the portal by a link and a one-time code
([rights-requests.md](../domain/rights-requests.md#how-a-holder-is-reached)).
