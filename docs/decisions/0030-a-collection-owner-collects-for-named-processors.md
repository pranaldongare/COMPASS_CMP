# 0030. A collection owner collects for named processors, and sees their data sources only

**Status:** accepted · 2026-10-09. Migration 0050. Narrows the `data_source`
grant in `core/permissions.py` for the DCO and the RCO; cover is read through
`cmp_delegators_of` (migration 0006), as on projects.

## Context

A Data Collection Owner saw every data source in the registry, and could
register a new one under any third-party processor; a Research Collection
Owner, under any in-house team. Nothing recorded which processor somebody
actually collects for. The only link was indirect: the sources a person had
been made accountable for. A new DCO owned nothing, so that link could not
answer the question either.

The product owner asked (2026-10-09) that a DCO see only the data sources of
their own processor, and add new ones only under it, and that the same hold
for an RCO.

## Decision

- **The administrator says which processors a DCO or an RCO collects for.**
  One or more per person, in `collection_owner_processor`; a DCO's are third
  parties, an RCO's are in-house teams, and the other kind is refused. They
  are set on the account (`PUT /users/{user_uuid}/processors`, admin only) or
  when it is created (`processor_uuids`); creating an account with sources
  adds those sources' processors.
- **A DCO or an RCO sees the data sources of those processors and no
  others.** The list is filtered by the query; a source outside them is *not
  found* (404), not forbidden, on every route that names one. A source with
  no processor is nobody's to see in this way.
- **They register new sources only under those processors** (422 on
  `processor_uuid` otherwise). With one processor the console chooses it.
- **A source is handed only to somebody who collects for its processor**
  (422 on `owner_user_uuid`), so nobody is accountable for a source they
  cannot see. The owner picker offers only them
  (`GET /users/collection-owners?processor=`).
- **Cover lends the delegator's processors**, as it lends their projects.
- **A link is a working assignment, not evidence.** Taking one away deletes
  the row; the trail keeps `user.processors_set` with the processor uuids
  before and after. A processor is not taken away while the person is still
  accountable for one of its sources (409 `processor_still_held`): hand the
  source on first. A role change, or the end of staff access, takes them all
  away.
- **Existing data was filled in from what was already true:** every
  processor whose sources a DCO or an RCO owned when 0050 ran
  (`assigned_by` NULL).

## Consequences

- A DCO or an RCO with no processor sees an empty Data Sources page that
  says why, and cannot register a source until the administrator assigns one.
- The rule is on data sources only. Projects, sites and consent links keep
  their own scope (source ownership and the site's named runner), which this
  rule makes consistent rather than replaces.
- The processor register itself is still readable by every staff role, as
  before.

## Revisit when

- Organisations want a DCO Admin, rather than the administrator, to assign
  processors.
- A collection owner needs to see a source of a processor they do not
  collect for (for example a shared feed), which would want a per-source
  grant rather than a wider processor list.
