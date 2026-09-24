# 0002. Evidence is enforced by the database, not the application

Status: accepted. Migrations 0002 and 0003. Amended 2026-09-21: sealing, and
the reseal script's handling of the append-only tables, which is under
review (below).

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

## Amended · 2026-09-21

Sealing personal data ([ADR 0016](0016-personal-data-sealed-by-a-separate-key-service.md),
[ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md)) touched this record
in four places. The decision above is not changed by this note; what follows
records what the code now does.

- **`scripts/reseal.py` rewrites existing evidence rows.** To seal values
  written before sealing was on, it runs `ALTER TABLE … DISABLE TRIGGER` on
  the append-only triggers of `consent_artefact`, `rights_ticket_message`,
  `project_status_history` and `person_type_history`, `UPDATE`s each
  plaintext value to its ciphertext, and re-enables the trigger in the same
  transaction before it commits (`backend/api/scripts/reseal.py:85-98`). It
  changes how a value is stored, not what it says, and nobody else can see the
  table without its trigger. It still does what "operators cannot fix a record
  by hand" and "never existing rows" rule out, and it needs a role that can
  disable a trigger, which is the owner and not the application role 0003
  restricts. It ran once on the development database on 2026-09-21. **This is
  under review, and is not settled by this note.**
- **0027 changed the type of `consent_artefact.ip_address`** from `inet` to
  `text` with a `USING` cast, which rewrote the column for every existing row.
  No trigger fires on `ALTER TABLE`.
- **Some rules now depend on the application.** Contact uniqueness is enforced
  on keyed hashes. The database requires the hash to be present (the
  `*_indexed` CHECKs), but cannot tell whether it was computed with the right
  key and normalisation. `dob_is_plausible` was dropped because a sealed date
  cannot be compared.
- **Evidence is readable only with the key.** A consent artefact's IP address,
  like every sealed column, opens only through the key service under
  `DKMS_MASTER_KEY`. The rows remain unaltered and append-only; whether they
  can be *read* years later now depends on that key surviving.
