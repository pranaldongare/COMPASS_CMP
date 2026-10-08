# 0026. A rights request is access, erasure or a grievance, about everything a person has

**Status:** accepted · 2026-10-07. Migration 0043, commit 4e0e52e. Amends
[ADR 0010](0010-rights-clock-and-defaults.md) (three kinds, not four, and no
consent-scoped requests).

## Context

The rights module took four kinds of request - access, correction, erasure
and a grievance - and from migration 0019 a request could be confined to one
of her consents: "Ask about this consent" on the portal, a consent picker on
the forms. Both were built ahead of a decision about how the Privacy Office
would actually take requests.

The DPO made that decision on 2026-10-07. Two of the four shapes did not
match the office's work:

- **Correction as a request.** What people asked to correct was almost
  always their name, and a name is hers to change from her own account
  (S3-05, built 2026-09-30, commit d4b2a66). The rest of correction - other
  profile fields, instructing processors that received an old value,
  corrections to evidence - was parked by the product owner, and a request
  type that promised it would have been a promise the platform could not
  keep.
- **A request about one consent.** The office answers for everything it
  holds on a person. A request confined to one study invites an answer that
  is true for that study and silent about the rest, which is not what s.11
  or s.12 asks for.

The same decision asked that a person can send documents with her request:
a proof of who she is, a letter, a screenshot. She could not.

## Decision

- **Three kinds.** A new request is access, erasure or a grievance, on every
  channel: the portal, the public form, a nominee, and one the DPO logs.
  Nothing is reclassified as a correction. The server refuses the fourth
  (`TAKEN`, `taken()` in `backend/api/src/cmp/domain/rights/service.py`),
  saying a name is corrected from her account, so a stale client cannot
  bring it back. An unknown kind names the three.
- **About everything held.** There is no project or consent to pick on any
  form, and the API refuses a `consent_uuid` on a new request as an unknown
  field. Holders are derived from everything held on her.
- **Documents with a request.** Signed in, she may send up to ten files with
  an open request - PDF, PNG, JPEG, text or Word, 25 MB each
  (`rights_request_attachment`, migration 0043). Each is kept as it came,
  append-only by trigger and grant, its name sealed. The portal sends them
  once the request is recorded, so the clock runs from the request, and one
  refused does not undo it. The DPO downloads them from the request page;
  every download is on the trail, which never records a name. The public
  form takes none: nobody is known until the code is confirmed.
- **Refusing is a button that says what it does.** At step 4 of the request
  page, refusing is a button with the reason it asks for, rather than grey
  text. A refusal closes the request `refused` and needs its reason in
  writing; the email carries the reason and the grievance route
  (`service.refuse`).
- **Requests made before are handled to the end as they were.** The
  `correction` type stays in the database. An old correction keeps its type
  on the classification card and counts as carried out as before, on
  returns that say *done*. A request confined to one consent still shows it
  and keeps the holders derived from that consent's chain. No stored record
  changes meaning.

## Consequences

- A person who wants something corrected other than her name has no request
  to make on the platform. She can raise a grievance or write to the DPO,
  and the office acts outside the rights module. This is the parked part of
  S3-05, not a solved one.
- A change of name from her account is not sent to processors that received
  the old one in an export. That was designed and parked (S3-05); until it
  is built the office instructs them by hand if at all.
- Every access and erasure answer is about everything held. A request is
  larger to answer than a consent-scoped one would have been, and cannot be
  answered narrowly by mistake.
- Documents she sends are personal data held by the platform, sealed by
  name, and are in the inventory
  ([personal-data.md](../domain/personal-data.md)).
- Two shapes of request now exist in the data: the old (four kinds,
  sometimes confined) and the new. The code that reads them keeps both paths
  until no old request is open.
- **Open for the DPO.** The public rights page
  (`backend/api/src/cmp/api/routers/public/rights.py`, lines 128-131) still
  lists "Correction and erasure" under s.12, with "Correction of inaccurate
  data, completion of incomplete data". That is the Act's wording, but the
  platform no longer takes a correction as a request, and a reader may
  expect to. Whether the page keeps the Act's words, says how a name is
  corrected, or both, is the DPO's to decide.

## Revisit when

The rest of correction is scheduled - other profile fields, or telling
processors of a change - which would bring it back as a self-service route
or as a request, a choice to make with the product owner then; the office
wants to take narrow requests again; or Legal reads s.12 as requiring a
correction request the platform must accept.
