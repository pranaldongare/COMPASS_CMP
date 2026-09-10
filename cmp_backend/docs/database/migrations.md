# Migrations

Alembic for ordering and reversibility. **Every migration is raw SQL.**

## Why raw SQL

The schema is exact types, constraints, triggers and grants.
Autogenerate reproduces none of that faithfully, and the difference between
`text` and `varchar(200)`, or a missing trigger, is not visible in a diff of
models.

## The chain

| Rev | Contains |
|---|---|
| `0001` | Baseline: 22 tables, 25 enums, the `v_current_consent` view, indexes, CHECKs |
| `0002` | Enforcement: append-only triggers, the SHA-256 audit chain, notice freeze rules |
| `0003` | Least privilege: revokes `UPDATE`/`DELETE` from the application role on evidence tables |
| `0004` | Two defects found by exercising 0001/0002 against a real server |
| `0005` | Site ownership: a collection owner is who owns the site's source; per-notice Rule 3 overrides |
| `0006` | Delegation: cover arrangements between staff for a period |
| `0007` | The collection model: `collection`, `data_asset`, `asset_consent`, bystanders, dispositions |
| `0008` | A per-site owner override, recorded as a named exception |
| `0009` | Processor amendments: `project_processor` with the DPO's decision per processor, and requests to add one after approval |
| `0010` | One export per project, with the disclosure record written alongside the file |
| `0011` | Recoverable consent links: re-mint with a reason; the fingerprint is all that is stored |
| `0012` | Date of birth on a data principal; `cmp_is_minor()` |
| `0013` | Rights requests: the request, holders, scope items, nominations, the reference sequence |
| `0014` | The audit chain position is drawn inside the advisory lock ([ADR 0005](../../../docs/decisions/0005-audit-chain-position-inside-the-lock.md)) |
| `0015` | Mobile-first contacts: nullable email, mobile required for principals and nominees by trigger, verification per medium ([ADR 0007](../../../docs/decisions/0007-mobile-first-contacts.md)) |
| `0016` | Respondents per processor: portal tickets for in-house teams, email for third parties |
| `0017` | A ticket is a thread: the brief, and append-only `rights_ticket_message` |
| `0018` | Ticket robustness: withdraw, reassign, remind; file names on messages |
| `0019` | A request confined to one consent |
| `0020` | Sending a returned ticket back |
| `0021` | Response files released with the response, hashed and time-boxed |
| `0022` | A nomination records the request that invoked it and the trigger event |

## What 0004 fixed

**The empty-array CHECK.** `array_length(x, 1) >= 1` passes on an empty array,
because `array_length` returns NULL and a CHECK passes on NULL. Replaced with
`cardinality()`, behind a guard that refuses to apply if offending rows exist.

**A `format()` specifier in `cmp_append_only()`.** A bare `%` raised
"unrecognized format() type specifier". The statement was still refused — the
trigger worked — but the message was useless to whoever hit it.

## Guards that refuse

0004 refuses to apply while a purpose with no categories exists, and 0015
refuses while a data principal or a nominee has no mobile. A migration that
fails loudly beats one that deletes data to satisfy itself; fix the rows, then
run it again.

## Triggers rather than NOT VALID checks

0015 first tried a `NOT VALID` CHECK for the mobile rule and it broke the
update of every legacy row that lacked one, since Postgres validates such a
constraint on `UPDATE`. A `BEFORE INSERT` trigger applies the rule to new rows
only, which is what was meant.

## Reversibility is tested

The CI workflow runs `upgrade → downgrade → upgrade` on every push. The rollback path is
proven to work **before** it is needed, which is the only time anyone finds out
otherwise.

## The env is synchronous

`migrations/env.py` uses a sync engine. psycopg's async mode cannot run under
Alembic's runner, and a migration is not a place to be clever about event loops.

## Adding one

```bash
uv run alembic revision -m "what it does"
```

Then write the SQL by hand. Both directions. Test the downgrade before you commit
the upgrade.
