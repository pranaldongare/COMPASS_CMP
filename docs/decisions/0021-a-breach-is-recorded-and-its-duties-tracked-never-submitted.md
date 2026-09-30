# 0021. A breach is recorded and its duties tracked; the platform never submits

**Status:** accepted · 2026-09-30. Migration 0034, backlog items S3-01 to S3-04.

## Context

Section 8(6) obliges the fiduciary, on a personal data breach, to intimate the
Board and each affected principal "in such form and manner as may be
prescribed", and Rule 7 prescribes it: every affected principal told without
delay what happened, what it means for her, what was done, what she can do and
whom to ask (7(1)); the Board told without delay (7(2)(a)) and sent a detailed
report within 72 hours of becoming aware, or such longer period as it allows
(7(2)(b)). Separately, and already in force, the CERT-In Directions of April
2022 under IT Act s.70B require a reportable cyber incident to be reported
within six hours of noticing it. The platform had no breach concept at all.

The plan proposed for Sprint 3 walked a breach through `reported → assessed →
notified → closed`. Checked against the Rule, that shape would have delayed
duties due *without delay* behind an assessment, and it had no room for CERT-In,
for an extension, or for a determination made by a person.

## Decision

- **One record per duty, created when its trigger is met, each on its own
  clock.** CERT-In runs from `detected_at`, when the event was first noticed;
  every DPDP duty from `became_aware_at`, when the organisation became aware a
  personal data breach had occurred. The two are kept apart, with `began_at`, and
  all three are **entered by the DPO, never defaulted** to the moment of saving:
  a breach recorded five hours late shows one hour of CERT-In time left.
- **A due time is stored when the duty is created and never recomputed**, as the
  rights clock does. The Board's extension, and a duty reinstated by a later
  determination, are new rows carrying their own due time. A duty's state is read
  by folding its events.
- **"Without delay" has no hours, and the platform invents none.** Those duties
  have no due time; the register shows the time elapsed since awareness and flags
  it against `BREACH_WITHOUT_DELAY_TARGET_HOURS`. The number is Legal's and the
  Programme's to choose, and until they do the setting is empty and nothing is
  flagged (decided with the product owner on 2026-09-30).
- **The platform records the determination; it never computes one.** Whether an
  event is a personal data breach under s.2(u) is a person's judgement, recorded
  with its reasoning as *pending*, *yes* or *no*, revised by new rows. Above all
  nothing infers *no* from encryption: DPDP has no encryption exemption and no
  severity threshold. The assessment records, per data category, whether its
  values were sealed and whether the key was exposed - because DKMS seals
  fields, not relationships - and no code reads it to skip or delay a duty (a
  source test holds this).
- **The state machine gates only closing.** `open → closed` is refused while the
  breach is undetermined or any applicable duty is outstanding; reopening is
  allowed with a reason. A determination of *no* marks the three DPDP duties not
  applicable, citing it; a later *yes* reinstates them with clocks from its own
  awareness time. CERT-In stands on its own test.
- **Evidence is never edited.** Determinations, assessments, duties, their
  events and the status history are append-only by trigger and grant; the breach
  row itself changes only its status (`cmp_breach_status_only`). Every narrative
  field is sealed - the finding on who caused it above all, since it may name an
  employee - and the trail records what was done, never the words (ADR 0015).
- **The register is the DPO's and hidden.** Resource `breach`, DPO only, and its
  guard answers every other role **404** rather than 403
  (`RequireResource(..., hidden=True)`): that a breach is being handled is itself
  withheld, and a caller walking uuids cannot tell a breach from nothing.
- **Who it touched is derived, confirmed and only ever added to.** From a
  processor's exports, a source's assets, or the platform's own tables in a
  window - the first two from the same holdings relation the rights module
  reads, generalised rather than copied. The DPO confirms each revision,
  leaving out and adding by hand; a person listed stays listed, and each
  revision adds only the newly found.
- **Where the platform ends.** It records, derives, tracks every clock, drafts
  every document and sends the notices to principals. People contain the breach,
  preserve evidence, make the determination, submit to the Board and to CERT-In
  through those bodies' own channels, and record the reference each returns. No
  code sends anything to a regulator.

## Consequences

- A submission is recorded after the fact, with when it was made and the
  regulator's reference; the platform's evidence is only as good as that entry.
  The trail shows who recorded it and when.
- A mistyped detection time cannot be corrected in place: the CERT-In clock was
  stored from it. The record shows what was entered; a correction is a note on
  the duty, and the Board's report carries every determination and revision.
- A later *yes* that moves the awareness time does not move clocks already
  running. Its time is on its own row, for the report.
- The principals' duty cannot be completed by hand. It completes when every
  affected principal's notice is delivered or its failure recorded after retry
  (S3-03).
- The administrator, who reads the audit trail, sees that breach events occurred
  and their reference - never a title or a reason - and cannot open the register.

## Revisit when

Legal sets the internal target for "without delay"; decides who files with
CERT-In (the DPO or corporate security - today only the DPO can record it); or a
regulator offers an interface the platform could submit through, which this
decision would then have to weigh against keeping a person in the loop.
