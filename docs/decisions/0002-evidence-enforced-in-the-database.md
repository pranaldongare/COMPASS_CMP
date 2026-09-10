# 0002. Evidence is enforced by the database, not the application

Status: accepted. Migrations 0002 and 0003.

## Context

The platform exists to prove, years later, what a person was shown and what
she agreed to. "The application always goes through the service layer" is a
claim about a codebase, and a codebase changes. A guarantee that only holds
while every future contributor remembers it is not a guarantee.

## Decision

The properties that make a record evidence live in PostgreSQL:

- consent artefacts, grants, disclosure records, history tables and the
  audit log refuse `UPDATE` and `DELETE` at the trigger level, and the
  application role's grants for those statements are revoked;
- a published notice and its renditions are frozen by trigger;
- an artefact must carry the SHA-256 of the text served, and the serving must
  precede the action, by trigger and CHECK;
- a consent link can only exist for an approved project's site, by trigger;
- the audit log is a hash chain computed by trigger in the same transaction
  as the write it describes.

The application enforces the same rules earlier, to give a better error. The
database is the layer that cannot be bypassed.

## Consequences

- A correction is always a new row: a new notice version, a superseding
  artefact. History is the chain of rows.
- Tests in `tests/integration/enforcement/` write raw SQL on purpose, to
  prove the rule holds without Python.
- A migration that must touch evidence, as 0014 did, has to work within the
  rules: it changes how future rows are written, never existing rows.
- Operators cannot "fix" a record by hand either. That is the point.

## Revisit when

Never for the evidence tables. The list of tables that count as evidence may
grow.
