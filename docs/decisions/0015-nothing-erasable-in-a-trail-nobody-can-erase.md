# 0015. Nothing erasable goes into a trail nobody can erase

**Status:** accepted · 2026-09-21

## Context

The audit trail is append-only and hash-chained, by trigger. That is its
value: nothing in it can be edited or removed by anyone, the Privacy Office
included, and the chain proves it. It is also the one store in the platform
where an erasure request cannot be honoured, because honouring it would mean
doing the thing the trigger exists to prevent.

A scan of the database on 21 September 2026 found personal data in it. Every
row's `detail_json` carried the client's IP address under `ip` — 2,261 of 2,264
rows — because `audit.record()` copied it from the request context. Two events,
`user.invited` and `user.created`, carried the invited email. One event,
`rights.ticket.reassigned`, carried the responder's contact, from and to. All of
it was there for a reason a person could give: an address to correlate an
attacker's actions by, an email to say who was invited, a contact to say who a
ticket moved between. None of it was ever read back by the platform. All of it
would outlive every right its owner had to have it removed.

## Decision

Nothing that a person could ask to have erased is written into the trail.

- **The client address is written as its blind index** — `HMAC-SHA256` under
  `BLIND_INDEX_KEY`, the same construction that lets a sealed email be looked
  up. The two questions an investigator asks of an address in an audit trail
  are "was this the same address as that?" and "did this known address
  appear?", and an index answers both exactly. What it cannot answer is "what
  was the address?", which is the point.
- **A person is named by their id.** `subject_user_id` and `actor_user_id` are
  on every row already. The invited email and the responder contacts are gone
  from the detail; the reassignment event records the respondent and account
  ids it moved between.
- **The office's reasons live in their rows, sealed; the trail records that
  one was given.** A refusal reason, a role change's justification, a
  transition's reason, a delegation's are the accountability record and are
  kept — in `rights_request.refusal_reason`, `project_status_history.reason`,
  `delegation.reason` and the rest, every one of them a sealed column with an
  audited write. Copying the words into the trail as well made a plaintext
  twin of a sealed column that no erasure could reach, and the dashboard's
  recent-activity feed was showing it. The trail now carries `reason_given:
  true`; the reader who needs the words follows the entity to its row.

## Consequences

- An erasure request can now be honoured completely: the trail holds ids that
  point at a row, and when the row is gone the ids point at nothing. Before,
  it held an address that pointed at a person.
- Investigating an incident by IP still works, on the platform's own data:
  compute the index of the address in hand and search for it. Correlating
  against an external log of raw addresses now needs the key, which is a
  restriction and is accepted as one.
- Rows written before this decision still carry raw addresses and, on eleven of
  them, an email. They cannot be rewritten, and this ADR says so rather than
  pretending otherwise. The platform's exposure from them is bounded to what
  the trail already held on this date, and grows no further.
- `docs/domain/personal-data.md` records `audit_log.detail_json` as holding an
  address index and ids, and nothing that could be asked for back.
