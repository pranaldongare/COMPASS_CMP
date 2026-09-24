# 0020. A transfer is checked at export, and an unknown place is refused

**Status:** accepted · 2026-09-24. Migration 0032, backlog item S2-04.

## Context

Section 16 lets a data fiduciary transfer personal data outside India except to
a country the Government has notified as restricted. A purpose carried a
`cross_border_permitted` flag, set by the Privacy Office and shown on the
notice, and nothing read it. No processor said where it was, and no export said
where its rows went.

Personal data leaves the platform in one place by design: the export CSV, one
row per person, handed to whoever collects at the site the consent was given at.

## Decision

- **A row's destination is the processor running its site**, and the
  processor's `location_country` is where the row goes. Recorded on each
  `export_line` as it was at the moment of the export.
- **Every destination is checked before anything is written.** India is
  domestic. Anywhere else goes only if the country is not on the restricted
  list and every purpose the people granted permits a cross-border transfer.
  One failing destination refuses the whole export; a file is one disclosure.
- **An unknown place is refused.** A processor with no recorded country cannot
  receive an export (decided with the product owner on 2026-09-24): "we did not
  record it" must not pass as "domestic". The column may be empty; the export
  may not go.
- **The restricted list is data, not code.** `restricted_country` holds the
  Government's notifications as the Privacy Office records them - a country,
  the notification, lifted once. What belongs on it is Legal's to say.
- **The decision is evidence.** `export_log.transfer_basis` records each
  destination, its country and the ground it went on; a refusal is audited, in
  a transaction of its own, with the processors and causes and none of the
  people.

## Consequences

- Every processor needs a country before its sites can be exported. Existing
  deployments must record them; until they do, their exports are refused and
  say which processor is missing one.
- A withdrawal row - exported so the agent stops - carries no granted purpose
  and is not held back by one.
- Holder derivation for rights requests reads the processor from the line. It
  had read it from the export's site, which no one-per-project export had, so
  exports derived no holders at all until 0032.
- The check applies to the export, the one place data leaves in bulk. A
  processor that re-transfers onward is bound by its contract, not by this.

## Revisit when

A second channel carries personal data out of the platform (an API
integration, S4-03), which must apply the same check; or the Government's list
is published in a form the platform could read rather than have typed in.
