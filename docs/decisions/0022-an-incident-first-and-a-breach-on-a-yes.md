# 0022. An incident is logged first, and a breach is recorded on a yes; the organisation's board is told within 30 minutes

**Status:** accepted · 2026-10-05. Amends [ADR 0021](0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md).
Migrations 0038 (S3-06) and 0039 (S3-07).

## Context

ADR 0021 made every report a breach from the first keystroke. Each one was
given a `BR-` reference, so the numbers counted suspicions rather than
breaches, and nothing stopped a notice going to principals about an event
nobody had yet decided was a breach. The office works the other way round: an
incident is noticed and contained, the DPO team validates whether it is a
personal data breach under s.2(u), and only then is there a breach to report.
The product owner set that order (BD-01).

Separately, an internal policy asks that the organisation's board hear of an
incident within 30 minutes of its being noticed (BD-02). The platform tracked
CERT-In's six hours and the Board's duties and had no clock for that.

## Decision

- **An incident is logged first** (BD-01, BD-08). Logging takes what recording
  a breach took - title, first noticed, began, where it occurred - and issues
  `INC-YYYY-NNNN` from its own sequence. The row is the existing `breach` row
  and the route stays `POST /breaches`; names in the code and the database are
  unchanged, and the console's words change.
- **Validation is the determination, renamed for people.** *Pending*, *yes* or
  *no*, with reasoning, as before. The platform still records it and never
  computes it.
- **The first yes records the breach, in the same transaction** (BD-09). It
  writes one `breach_recording` row carrying `BR-YYYY-NNNN` from the existing
  `breach_ref_seq`, the *yes* that caused it, who and when. There is no
  separate "record" button: it would only add a way to hold back duties due
  without delay. One per breach, never withdrawn: a later *no* sets the DPDP
  duties aside as before and leaves the recording; a later *yes* issues no
  second number.
- **Telling anyone waits for the recording; drafting does not** (BD-10).
  Sending the principals' notice is refused before it (409
  `breach_not_recorded`). Deriving who it touched, drafting and approving the
  notice, and drafting the Board's documents stay open during validation, so
  that the work is ready the moment a *yes* is recorded. Everything addressed
  to a principal or to the Board carries the breach reference.
- **The organisation's board is a duty on every incident** (BD-02, BD-11,
  S3-07). Created when the incident is logged, due `BREACH_ORG_BOARD_MINUTES`
  (default 30) after first noticed, stored at creation like every other due
  time. Validation never touches it: it is not a DPDP duty. The platform
  drafts a brief from the register; a person reports to the board through the
  organisation's own channel; the DPO records when, and to whom. The platform
  never reports to the board, as it never submits to a regulator.
- **Incidents logged before 0038 keep their reference.** Their `BR-` string is
  their incident reference, and where they have a *yes* the migration records
  the breach under the same string, from the first one. Incidents logged before
  0039 get no organisation's-board duty.

## Consequences

- BR numbers count recorded breaches. An INC that is validated *no* never has
  one; the gaps a reader sees in BR numbers are numbers drawn by a race and
  never used, not breaches withheld.
- Legacy rows carry a `BR-` string as their incident reference, and their
  trail names them once: "Breach BR-2026-0001", not "Breach BR-2026-0001
  (BR-2026-0001)".
- A notice cannot reach a principal during validation, even an approved one.
  The cost is the minutes between a *yes* and pressing Send; the gain is that
  nobody is told of a breach that was not one.
- The 30-minute clock runs from first noticed, so the time taken to log the
  incident is the critical path, and only the DPO role can log one. More than
  one person needs that role, and cover for it matters.
- The register now holds incidents that were never breaches. They close like
  any other once validated *no* and their duties are done.

## Revisit when

The board policy changes its time or its anchor; the team wants breach
tickets during validation, before a *yes* (one guard in the ticket service,
S3-08); or someone other than the DPO team should be able to log an incident.
