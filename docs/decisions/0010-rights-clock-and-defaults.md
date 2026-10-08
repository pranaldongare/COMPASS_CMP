# 0010. The rights clock starts at receipt, and the open questions have defaults

Status: accepted. Migration 0013 onward, September 2026. Amended 2026-10-07:
a new request is access, erasure or a grievance, about everything held - see
the end and [ADR 0026](0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md).

## Context

The Act gives a data principal four things to ask for and one person to
name, and Rule 14 requires the fiduciary to publish a response period with an
outer limit of ninety days. The flows were specified as five diagrams that
left several questions open. Building nothing until Legal answered them would
have shipped nothing.

## Decision

**The clock.** The response period starts at receipt (D0), not at
verification, and the due date is stamped on the row at receipt. A change in
configuration applies to the next request, never to one already running.
The checkpoints between D0 and D are computed from the two and returned by
the API, so no client computes a date.

**The defaults.** Each open question is answered by a default that can be
changed without unwinding a record:

| Question | Default |
|---|---|
| Response period | 90 days, the Rule 14 limit |
| Grievance period | the same, separately configurable |
| Who reviews a complaint about the DPO | the administrator, who assigns a reviewer |
| Nominees per person | one live nomination |
| Nominee acceptance window | 30 days |
| Unverified public request | closed after 7 days |
| Released file download window | 30 days |
| Standard of proof for death or incapacity | the DPO's note; the standard is Legal's to publish |
| Quarantine's time limit | none |
| Backups | out of scope for erasure |

**The shape.** A holder per party, a ticket per holder, a thread per ticket,
a scope item per appearance of her in an asset. Erasure changes the person's
junction row and never the asset, because an asset holding three people is
not deleted when one of them asks. Consent artefacts are never erased.

## Consequences

- The rights page states the period, because the Rules require it published.
- Every default is a setting, listed in `.env.example`, and the table above
  is the place to change a default deliberately.
- Later additions (respondents per processor, threads, send-back, response
  files, consent-scoped requests, nomination invocation) extended the shape
  without changing a stored record's meaning.

## Revisit when

Legal publishes the standard of proof or a shorter period. Both are
configuration or a note, not a migration.

## Amended 2026-10-07: three kinds, about everything

The DPO set how requests are taken (commit 4e0e52e). Two things above no
longer describe a new request:

- **Three kinds, not four.** A new request is access, erasure or a
  grievance, on every channel - the portal, the public form, a nominee, and
  one the DPO logs - and nothing is reclassified as a correction. The server
  refuses the fourth (`TAKEN` and `taken()` in
  `backend/api/src/cmp/domain/rights/service.py`), saying that a name is
  corrected from her account (S3-05). The Context's "four things to ask for"
  is the Act; the platform now takes three of them as requests.
- **About everything held.** A new request is never confined to one
  consent: the input has no `consent_uuid`, and the API refuses one as an
  unknown field (422). "Consent-scoped requests" in the Consequences was an
  addition of migration 0019 that new requests no longer use.

Requests made before keep what they were. A correction is still handled to
the end as it was, and a request confined to one consent still shows that
consent and keeps the holders derived from it. No stored record changes
meaning, which is the property the Consequences claim. The decision and its
reasons are [ADR 0026](0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md).
