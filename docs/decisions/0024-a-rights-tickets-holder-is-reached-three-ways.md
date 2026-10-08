# 0024. A rights ticket's holder is reached three ways, and an outside holder answers by a link and a code, never an account

**Status:** accepted · 2026-10-08. Migration 0049, commit 833b58f. Amends
[ADR 0009](0009-two-portals-by-audience.md) (the portal serves outside
holders); extends [ADR 0023](0023-breach-tickets-and-breach-only-logins.md)
(the same temporary login); bears on
[ADR 0016](0016-personal-data-sealed-by-a-separate-key-service.md) (SEC-1).

## Context

A rights request's ticket is addressed to a responder of each party that
holds her data. A responder with a console account answered in the console.
Everybody else was sent the request in full by email, answered by email, and
the office copied the answer in by hand. Two kinds of responder were served
badly by that:

- **A colleague with no console login.** Somebody in the organisation who
  holds the data - an engineer, a lab lead - but has never needed the
  console. Breach tickets had already met this with a breach-only temporary
  login (ADR 0023, S3-09).
- **Somebody outside the organisation.** A vendor or a third-party
  processor. Its email carried what she asked, about whom, and the office's
  instruction, to a mailbox the platform knows nothing about. Its answer and
  its proof lived in that mailbox until somebody retyped them.

Giving outside holders accounts was ruled out. ADR 0023 keeps platform-made
logins to the organisation's own domains, and an account per vendor contact
would be a staff-shaped login for people the organisation does not employ,
outliving the one ticket it was made for. A bare link was ruled out too: an
email is forwarded, and whoever holds a forwarded link would read the
request.

## Decision

Decided with the product owner on 2026-10-08.

- **How a holder is reached is settled as the ticket is sent**
  (`domain/rights/reach.py`, `place`), by the responder's address, so the
  office may name and rename a responder freely until then. "Internal" is an
  address on `BREACH_TICKET_EMAIL_DOMAINS`: one list of what the
  organisation's own addresses are, for breach and rights tickets alike.

  | The responder | Reached | Answers |
  |---|---|---|
  | an account that signs in to the console | the ticket in **My tasks**; the email in full, with a link to it | in the console, with files |
  | an internal address with no console login | a **temporary login**, then as above | in the console |
  | any other address | an email carrying **a link and nothing of the request** | on the portal, at `/ticket/{token}`, after a one-time code |

- **The temporary login is ADR 0023's.** The same role, `breach_holder`, the
  same email, the same off switch. The grant is a row in the same table,
  `breach_temporary_access`, against the rights holder (`holder_id`, with
  `breach_id` and `ticket_id` empty; exactly one of the two, by CHECK). It
  ends when the request closes, or the ticket is withdrawn or sent to
  somebody else; the login stays, to read, and the administrator's End
  temporary access ends every grant at once. One table keeps one answer to
  "who holds a temporary login, and why".
- **An outside holder's email carries the link and nothing else.** Every
  email about its ticket - the ticket, a message, a reminder, a ticket sent
  back, withdrawn, reopened or moved - is *Ticket link to an outside holder*:
  what happened, the date and the link. The link's keyed fingerprint is on
  the holder (`link_token`), with a sealed copy (`link_token_sealed`) so a
  reminder carries the same link; the token is never stored in the clear.
- **The link alone shows almost nothing.** Opened, it shows the reference,
  the holder's name, and where the code will go, masked
  (`domain/rights/holder_link.py`, `open_link`). Every way a link can fail
  answers the same 404.
- **The code goes to the address on the ticket, never one typed.** Holding
  the link is not enough: the holder must also read that mailbox. Codes are
  rate-limited per ticket, and the public routes per network address.
- **The code opens one ticket for an hour, in that browser.** A random value
  in an HttpOnly, SameSite=Strict `cmp_ticket` cookie; its fingerprint in
  Redis names the holder and the link it came through
  (`HOLDER_TICKET_SESSION_S`, an hour). Every call names the link in its
  path too, and both must agree (`signed_in`), so the cookie alone opens
  nothing. No session is minted and no account is touched (ADR 0013,
  amended).
- **Inside, the holder does what a holder in the console does.** It reads
  what is asked, the items, and the platform's brief of what it holds about
  the person; writes to the office with files; and answers *done*, *partial*
  or *failed*, which waits for review
  ([ADR 0025](0025-a-holders-answer-counts-once-accepted-and-the-server-owns-the-moves.md)).
  Its acts are on the trail with no actor and the channel `link`
  (`api/routers/public/holder_tickets.py`).
- **A ticket sent to somebody else gets a new link.** The old link stops
  working, and with it any hour opened through it; whoever had it is told it
  has moved. An outside holder whose ticket went before links existed is
  given one the first time anything is sent to it.
- **The office can still record an answer for any holder**, one sent by
  email for instance, and it counts as recorded.

## Consequences

- An outside holder's mailbox no longer receives the request. What a
  forwarded email gives away is a reference, a holder's name and a masked
  address.
- The portal now has visitors who are not data principals. They reach one
  ticket and no console route, so ADR 0009's split stands, amended.
- The decrypt routes now answer for a `cmp_ticket` cookie as well as a
  `cmp_session` cookie, and check neither value. This keeps SEC-1 open; it
  does not close it (ADR 0016, amended;
  [csrf.md](../security/csrf.md#not-covered-the-portals-own-dkmsdecrypt)).
- The holder routes take no session and no CSRF header. SameSite=Strict and
  the link in every path stand in for them.
- The address on the ticket is the whole of the outside holder's identity.
  A wrong address gives the ticket to whoever reads that mailbox, once they
  also have the link.
- "Internal" is only as good as the domain list, as ADR 0023 says. A vendor
  on the organisation's domain is given a temporary login.
- A responder with no email address is reached by nobody: the office
  reaches them itself and records the answer.

## Revisit when

SEC-1 is decided, which settles how the decrypt route treats the ticket
cookie; a holder integration (S4-03) lets a processor answer by an
interface rather than a page; an HR directory replaces the domain list; or
an outside holder needs more than an hour, or more than one ticket at a
time.
