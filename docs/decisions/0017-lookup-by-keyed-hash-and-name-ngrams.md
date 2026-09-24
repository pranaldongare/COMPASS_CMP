# 0017. Sealed values are found by keyed hash, and names by hashed runs

**Status:** accepted · 2026-09-21 (the exact hash, migration 0028) · 2026-09-22 (the name runs, migrations 0029 and 0030)

## Context

[ADR 0016](0016-personal-data-sealed-by-a-separate-key-service.md) seals
personal data with a randomised scheme: the same address encrypts differently
every time. That is right for data at rest and wrong for a column the
platform finds rows by. Sign-in looks up the email typed in; "is this address
taken" compares against every row; a code has to find the person it was
requested for; a nomination is matched by the nominee's contact. None of that
works on ciphertext, and a unique index on it admits every duplicate.

0027 therefore left eight columns in the clear: email, secondary email,
mobile, username and employee id on `auth_user`, the nominee's two contacts,
and a public request's submitted contact. Sealing them as well took something
back that staff used every day: typing part of a name into a search box.

## Decision

- **An exact keyed hash beside each lookup column.** `<column>_hash` holds
  `HMAC-SHA256("<kind>:" + normalised value)` under `BLIND_INDEX_KEY`, as hex.
  Deterministic, so it can be unique-indexed and compared; keyed, so a dump
  of the table cannot be joined against a list of guesses without the key.
  The value column beside it is sealed like any other and opened only to send
  something to it. Added as `*_idx` in 0028, renamed `*_hash` in 0029 because
  that is what it holds.
- **Every rule moves to the hash.** The unique constraints on email, mobile,
  username and employee id, the secondary email's, "the second address
  differs from the first", and the trigger that says an address belongs to one
  account whichever column holds it. A `*_indexed` CHECK refuses a row with the
  value and no hash, so a raw write that forgets it fails rather than escaping
  them.
- **Normalisation is part of the hash.** Emails are stripped and lower-cased,
  mobiles go through `normalise_mobile`, usernames are lower-cased, an employee
  id is compared as typed, and a contact is an address if it has an `@`
  (`cmp.infrastructure.dkms.blind.normalise`). The kind is mixed in, so an email
  and a username with the same text do not share a hash.
- **The API computes the hashes itself**, from the same key the key service
  holds as `DKMS_HASH_KEY`. Sign-in and search therefore do not wait on the key
  service. The two keys must be the same string.
- **Names get a second, weaker index, and only names.** `<column>_ngrams` is a
  `text[]` of the hashed overlapping three-character runs of the normalised
  name (`"ngram3:" + run`), with a GIN index. A search hashes the runs of the
  term and asks `@>`: the row must contain every one. A term shorter than three
  characters has no runs and is not searched. Three columns have one:
  `auth_user.full_name`, `rights_request.submitted_name`,
  `nomination.nominee_name`.
- **Date of birth is not looked up, but it was compared.** `cmp_is_minor()` was
  a date comparison in SQL, and a sealed date cannot be compared. 0028 added
  `minor_until`, the date eighteen years after birth, kept in the clear and
  saying nothing else, and sealed `dob`.

## Consequences

- A contact, username or employee id is found whole or not at all. Part of an
  address matches nothing, deliberately: a contact carries no runs.
- **A set of runs leaks more than a hash.** Counting how often each hashed run
  appears across a table, and matching that against a language's letter
  statistics, can recover common names without the key. That is the reason
  there are three such columns, all names, and never a contact or free text.
  A fourth needs the same argument made for it.
- **The hash is only as safe as the key.** With `BLIND_INDEX_KEY`, a mobile
  number or an IPv4 address can be enumerated in reasonable time. The key
  lives in the API's environment as well as the key service's.
- **The normalisation and the key are frozen by the data.** Changing either
  changes every stored hash: nobody can sign in and no rule holds until each is
  recomputed, which means opening each sealed value first. No tool does that
  today; 0028's backfill did it once. `normalise_for_ngrams` is separate from
  `normalise` for this reason: it was new, so it could fold spaces and compose
  accents without breaking stored hashes.
- **The database checks that a hash is present, not that it is right.** A
  writer with the wrong key or its own normalisation passes the `*_indexed`
  CHECK and escapes uniqueness. The repositories are the one writer that gets
  it right. This is a narrowing of
  [ADR 0002](0002-evidence-enforced-in-the-database.md)'s "the database is the
  layer that cannot be bypassed" for contact uniqueness, recorded in its
  amendment.
- **The date-of-birth CHECK is gone.** `dob_is_plausible` could not be
  restated on ciphertext. Registration still checks the date; `PATCH /me`
  does not ([schema.md](../database/schema.md)).
- 0028 and 0030 compute their backfills in Python, with the application's own
  functions, because the database does not hold the key. That is the amendment
  to [ADR 0001](0001-no-orm-raw-sql.md).
- The audit trail records the client address as `index_of("ip", …)` under the
  same key ([ADR 0015](0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
- The same contact rules as before, now said with hashes: [ADR
  0007](0007-mobile-first-contacts.md) and [ADR
  0013](0013-every-account-is-a-data-principal.md) are amended to point here.

## Revisit when

Staff need to search a sealed column other than a name, which is this
record's leakage argument made again for that column; the hash key has to
change, which first needs a re-hashing tool; or name search needs to be
fuzzier than "contains every run", which is a different index, not a longer
list here.
