# DKMS: every personal field, every endpoint — the plan

**Status: in progress.** Each phase is a commit; the checkbox is ticked when it
lands.

## Where it stands

Of the 54 personal columns in [pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md):

| Group | Columns | State |
|---|---|---|
| Sealed on write | 25 | Done. Every repository write goes through `seal()`; the API serves `SE::…`; the portals decrypt in one call per response |
| Plaintext — lookup keys | 8 | `email`, `secondary_email`, `mobile`, `username`, `dob`, `nominee_email`, `nominee_mobile`, `submitted_contact`. **This plan seals them** |
| Plaintext by nature | 21 | ids, flags, hashes, storage paths, jsonb. Two need work: `audit_log.detail_json` carries the client IP and invited emails, and cannot be erased |

Every endpoint that *writes* a sealed column already encrypts, because the
seal is at the repository and every endpoint goes through one. What is not
yet true: the eight lookup columns, the audit trail, rows written before the
switch, and a test that proves each of the 159 endpoints behaves.

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
| `auth_user` | `email`, `secondary_email`, `mobile`, `username` | `email_idx`, `secondary_email_idx`, `mobile_idx`, `username_idx` |
| `nomination` | `nominee_email`, `nominee_mobile` | `nominee_email_idx`, `nominee_mobile_idx` |
| `rights_request` | `submitted_contact` | `submitted_contact_idx` |

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

- [ ] **A. Blind index and the eight columns.** `BLIND_INDEX_KEY` setting;
  `cmp.infrastructure.dkms.blind`; migration 0028 (index columns, backfill from
  the plaintext still present, unique indexes moved from value to index, the
  three triggers rewritten, `minor_until`, columns widened to `text`); every
  write computes the index and seals; the nine exact-match lookups use the
  index; the partial searches drop the sealed columns. `dob` sealed.
- [ ] **B. The audit trail.** Stop writing the invited email into
  `detail_json` (the row's `user_id` already names the person); record the IP
  as its blind index rather than the address. One ADR, because the trail is
  the one store nothing can be erased from.
- [ ] **C. Re-seal what is already there.** `scripts/reseal.py`: every sealed
  column, every plaintext row, in batches, idempotent - a row already `SE::` is
  skipped. Run once after A; runnable again at any time.
- [ ] **D. Tests, endpoint by endpoint.** An HTTP harness (`httpx` over the
  ASGI app, the real database, a session minted per role) and a generated
  suite over the 159 endpoints in the PII list: every GET is called and every
  sealed field in its response is asserted to be `SE::…` or null and never
  plaintext; every POST/PUT/PATCH that writes a personal field is called with a
  valid body and the row it wrote is read back and asserted sealed. Plus a
  repository-level test, parametrised over the field map, that each column's
  writer seals it.
- [ ] **E. The portals.** A test that the API client's interceptor opens a
  sealed response end to end (unit, both apps), and a browser test that the
  users list and a request page show plaintext and no `SE::`.
- [ ] **F. Documents.** `personal-data.md`, `pii-fields-and-endpoints.md`,
  `roles-and-access.md` (search), the changelog.

## Verification, at the end

```bash
cd backend/api && pytest                     # every suite, encryption on
python scripts/reseal.py --check             # zero plaintext rows in sealed columns
psql -c "select count(*) from auth_user where email not like 'SE::%'"   # 0
```

And on the running stack: sign in with an email whose stored form is `SE::…`,
receive the code at it, open the users list and see names.
