# DKMS: every personal field, every endpoint — the plan

**Status: done.** Each phase was a commit; every checkbox is ticked. Kept as the
record of what was decided and why.

## Where it stands

Of the 54 personal columns in [pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md):

| Group | Columns | State |
|---|---|---|
| Sealed on write | 33 | Done. Every repository write goes through `seal()`; the API serves `SE::…`; the portals decrypt in one call per response. Includes the eight former lookup keys, behind their blind indexes |
| Plaintext by nature | 21 | ids, flags, hashes, storage paths, jsonb. `audit_log.detail_json` now carries the IP's index and no email; the two jsonb copies on the holder carry sealed values |

Every endpoint that *writes* a sealed column encrypts, because the seal is at
the repository and every endpoint goes through one. The eight lookup columns,
the audit trail, the rows written before the switch, and a test over each of
the 159 endpoints were what this plan added.

## Why the eight are hard, and how they get sealed anyway

Randomised ciphertext cannot be looked up. `WHERE lower(email) = lower(%s)` is
how sign-in finds the account, how "is this address taken" is answered, how a
one-time code finds its person. Sealing the column alone breaks all three.

**The blind index.** Beside each sealed lookup column, a second column holds
`HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`. It is deterministic - the
same address always produces the same index - so it can be unique-indexed and
looked up, and it reveals nothing without the key. The plaintext column is then
sealed like every other. Sign-in computes the index of what was typed and looks
that up; the sealed value beside it is opened only to send the code.

| Table | Sealed | New index column |
|---|---|---|
| `auth_user` | `email`, `secondary_email`, `mobile`, `username` | `email_hash`, `secondary_email_hash`, `mobile_hash`, `username_hash` |
| `nomination` | `nominee_email`, `nominee_mobile` | `nominee_email_hash`, `nominee_mobile_hash` |
| `rights_request` | `submitted_contact` | `submitted_contact_hash` |

**Date of birth** has a different problem: `cmp_is_minor(dob)` is a SQL
comparison that decides the section 9 case. It becomes `minor_until`, a date
eighteen years after birth, kept plaintext - it says when a person stops being a
child and nothing else - while `dob` itself is sealed.

**What is lost, and accepted:** partial search. The users list matched `q=`
against name and email with `ILIKE`; the audit lookup and the requests list
did the same. A sealed column cannot be searched for a substring. Search by
exact contact works through the index; search by reference, uuid and project
works as before; search by "part of a name" does not, and the documents say so.

## Phases

- [x] **A. Blind index and the eight columns.** `BLIND_INDEX_KEY` setting;
  `cmp.infrastructure.dkms.blind`; migration 0028 (index columns, backfill from
  the plaintext still present, unique indexes moved from value to index, the
  three triggers rewritten, `minor_until`, columns widened to `text`); every
  write computes the index and seals; the nine exact-match lookups use the
  index; the partial searches drop the sealed columns. `dob` sealed.
- [x] **B. The audit trail.** Stop writing the invited email into
  `detail_json` (the row's `user_id` already names the person); record the IP
  as its blind index rather than the address. One ADR, because the trail is
  the one store nothing can be erased from.
- [x] **C. Re-seal what is already there.** `scripts/reseal.py`: every sealed
  column, every plaintext row, in batches, idempotent - a row already `SE::` is
  skipped. Run once after A; runnable again at any time.
- [x] **D. Tests, endpoint by endpoint.** An HTTP harness (`httpx` over the
  ASGI app, the real database, a session minted per role) and a generated
  suite over the 159 endpoints in the PII list: every GET is called and every
  sealed field in its response is asserted to be `SE::…` or null and never
  plaintext; every POST/PUT/PATCH that writes a personal field is called with a
  valid body and the row it wrote is read back and asserted sealed. Plus a
  repository-level test, parametrised over the field map, that each column's
  writer seals it. *As built:* `tests/http/` - a world built through the API,
  five files of journeys, `contract.call()` on every response, and
  `test_zz_coverage.py` closing the loop from three sides (ledger ⊇ documented
  list; nothing seen sealed is undocumented; every sealed column holds only
  ciphertext after the run). Three leaks it found are fixed: the ticket brief
  and the contact log held contacts in clear jsonb; the audit search matched
  sealed names.
- [x] **E. The portals.** A test that the API client's interceptor opens a
  sealed response end to end (unit, both apps), and a browser test that the
  users list and a request page show plaintext and no `SE::`. *As built:*
  `src/lib/api/client.test.ts` in both portals (MSW at the network boundary);
  `e2e/sealed-never-shown.spec.ts` in both, which also requires the API to
  have answered sealed on the pages that always show a person.
- [x] **F. Documents.** `personal-data.md`, `pii-fields-and-endpoints.md`,
  `roles-and-access.md` (search), the changelog.

## Verification, at the end

```bash
cd backend/api && pytest                     # every suite, encryption on
python scripts/reseal.py --check             # zero plaintext rows in sealed columns
psql -c "select count(*) from auth_user where email not like 'SE::%'"   # 0
```

And on the running stack: sign in with an email whose stored form is `SE::…`,
receive the code at it, open the users list and see names.
