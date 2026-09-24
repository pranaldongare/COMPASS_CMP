# 0019. Erasure reaches every store that holds an item, and never the record of what happened

**Status:** accepted · 2026-09-24. Migration 0031, backlog item S2-03.

## Context

An erasure decision used to change one thing: her disposition on the
`asset_consent` row. The recording she asked to be erased stayed at the lab
that made it, the platform kept its pointer to it, and a request could close
as though it were gone. Section 12(3) asks for erasure, not a flag, and s.8(7)
asks for the same when a purpose is served. A platform that can only say
"decided" cannot answer either.

What "every store" means had to be established rather than assumed. The
platform never holds an asset's bytes: a recording lives at the data source
that collected it, and `data_asset.storage_ref` is that source's own pointer,
never dereferenced here. The inventory
([docs/domain/personal-data.md](../domain/personal-data.md)) shows the other
places her data sits: consent artefacts, the audit trail, the export CSVs sent
to processors, the response packages given to her.

## Decision

- **Quarantine first, always.** Applying any decision quarantines her
  appearance at once - out of use and release, and recoverable if the decision
  was a mistake. Erasure comes after it, not instead of it.
- **An item is carried out store by store**, by an executor
  (`cmp.domain.rights.erasure`):
  - the **holder's copy** - only the holder can erase it, so the instruction
    travels on the request's ticket and the store is done when the ticket is
    returned, the return and its evidence hash being the confirmation;
  - the **platform's pointer** - for an erasure, where nobody else is in the
    asset, `data_asset.storage_ref` is cleared. A redaction keeps the asset,
    and its pointer, for the other people in it (decision D-09).
- **Every attempt is evidence.** `rights_item_execution` is append-only: one
  row per attempt at each store - done, waiting, failed or held, and why,
  never a value about her. `executed_at` is set, and her disposition moves to
  erased or redacted, only when every store is done. A store that fails is
  retried daily, on each ticket return and on demand, and stays visible until
  it succeeds.
- **A legal hold stops it.** `legal_hold` covers an asset or a person, is the
  DPO's to place with a sealed reason, and is placed once and released once by
  trigger. A held item records `held` and goes no further.
- **The record of what happened is never erased.** Consent artefacts and the
  audit trail, which prove the processing was lawful when it happened (ADR
  0002, ADR 0015). And - decided with the product owner on 2026-09-24 - the
  export files processors were sent and the response packages she was given:
  both are records of an act, hashed where they were written, and rewriting
  them would falsify the history the platform exists to keep. The response
  says they remain, and why.

## Consequences

- A request can now close `complete` for an erasure (S2-02's guard reads
  `executed_at`), and only when it is true.
- The platform's claim is bounded by the holders' honesty: a returned ticket
  is the evidence a lab erased its copy, not proof. That is the limit of any
  system that does not hold the bytes; the evidence hash and the thread are
  what an auditor examines.
- A holder's return can only be recorded while the request is open. An item
  whose holder answers after the response waits, visibly, until the office
  acts on it.
- **Backups are outside this decision.** There are no database backups yet
  (P-03, parked), and whether a backup still holding an erased item is
  scrubbed or left to expire is Legal's call. The erasure record says nothing
  about backups until it is made.
- Retention lapse (`tasks/maintenance/retention.py`) still only quarantines or
  counts `erase_due`; driving cessation through this executor is S4-01.

## Revisit when

Legal decides the backup question; the platform starts holding asset bytes
itself (P-02), which would add a storage store erased through
`infrastructure/storage/service.py`; or a holder integration (S4-03) lets a
holder confirm erasure other than by returning its ticket.
