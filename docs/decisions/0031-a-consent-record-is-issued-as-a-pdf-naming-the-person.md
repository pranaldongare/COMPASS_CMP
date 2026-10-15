# 0031. A consent record is issued as a PDF, naming the person and masking one contact

**Status:** accepted · 2026-10-15; extended the same day (records by ID, at
the end). `cmp.domain.consent.record`, `cmp.infrastructure.pdf`; routes
`GET /consents/{consent_uuid}/record`, `GET` and `POST /consent-records`,
`GET /me/consents/{consent_uuid}/record`.

## Context

Audit asked for the consent a data principal gave to be shown as a PDF, and
for those PDFs to be kept in a downstream system. The consent register can
already prove a consent on screen, through the artefact, its grants, the
hash of the notice text and the server's timestamps. What it could not do was
hand that proof to somebody who keeps it outside COMPASS.

A PDF in another system's store is a copy that COMPASS cannot reach. An
erasure under [ADR 0019](0019-erasure-reaches-every-store-but-the-record.md)
reaches every store the platform holds, and this would not be one of them.
So whatever personal data the PDF carries has to be decided once, on purpose.
The instruction was to add details specific to the person only where they
are required.

## Decision

- **Who the record is about: her name, one masked contact, her principal ID.**
  The mobile when she has one, else the email, masked: `+91******3210`,
  `a***@example.org`. Asked on 2026-10-15, the product owner chose the name and
  masked contact over a pseudonymous ID alone, so a reader can see whose record
  it is without COMPASS. Nothing else about her is included: no date of birth,
  no second contact, no network address. The page says so.
- **The record stands alone.** It holds:
  - the decision per purpose (granted, refused, or withdrawn by this record);
  - the purposes' data categories, retention and lawful basis;
  - the history of every decision on that notice;
  - the notice text **as it was shown, in the language it was shown**;
  - the SHA-256 recorded at capture, beside the hash of the stored text.

  A machine-readable copy (`consent-record.json`) is embedded in the PDF.
- **Every artefact, as it stands.** A withdrawal has its own PDF. The PDF of
  an earlier decision says it was superseded, by which record and when, so a
  copy filed before a withdrawal cannot be mistaken for one filed after it.
- **Who may have one.**
  - Staff who read consents in full, each in their own scope: the DPO, a DCO,
    a DCO Admin, an RCO.
  - The person, for her own consent.

  The R&D User, whose access to consents is summary counts, may not. A record
  outside a caller's scope is not found.
- **Each copy is audited.** `consent.record_downloaded` names the artefact and
  the kind of copy (staff or her own, single or in an archive). It does not
  include her name or contact, so nothing erasable enters the trail
  ([ADR 0015](0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
- **Delivery is a pull.** The downstream system gets one PDF at a time, or a
  ZIP from `GET /consent-records` with these filters: project, site, and
  `from`/`to` on when the decision was made. The ZIP contains every artefact
  in that range, not only the current ones. Otherwise a consent given in
  January and withdrawn in March would be missing from January's pull. It
  also contains `manifest.csv`, which has each file's SHA-256 and identifiers
  and no names. At most 200 records per archive; more is refused with the
  count (`archive_too_large`).
- **The PDF never prints what it could not open.** The name and contact are
  opened through the key service. A value still sealed after that call means
  the service did not answer. The request then fails with 503 rather than
  producing a PDF with ciphertext where a name should be.
- **Rendering is self-contained.** The PDF is built with `fpdf2`, which shapes
  text with HarfBuzz (`uharfbuzz`), using bundled Noto fonts for each script
  the platform serves notices in (`infrastructure/pdf/fonts/`, SIL OFL 1.1).
  It renders the same on any server, with no system font and no network fetch.

## Consequences

- Each PDF that leaves COMPASS carries a name and a partial contact that a
  later erasure cannot reach. The downstream store's retention and access
  rules now govern that copy. They should be agreed with whoever runs it.
- Four runtime dependencies are added: `fpdf2` (LGPL-3.0), `uharfbuzz`
  (Apache-2.0), `fonttools` (MIT) and `pillow` (MIT-CMU). There are also
  2.2 MB of fonts in the source tree.
- A language added to `language_code` needs its font. Without one, its text
  renders as empty boxes. A unit test checks every value has one and that
  each script renders without a missing glyph.
- The downstream system pulls through a staff session, because the API has no
  credential for a machine
  ([ADR 0003](0003-server-side-sessions-and-first-party-proxy.md)). A
  scheduled, unattended pull needs one. That is a new credential type and its
  own decision.
- Layout takes about a tenth of a second per record, off the event loop. A
  200-record archive takes around 25 seconds.

## Revisit when

- the downstream system is named and wants records pushed to it, or wants a
  pseudonymous record instead;
- a regulator or an auditor asks for PDF/A, which this output does not claim to
  be;
- a consent method is added that the record should describe (a guardian's
  verifiable consent under s.9 is the likely one).

## Extended 2026-10-15: records by consent ID

Staff who may download records can also ask for a list of them by consent ID:
`POST /consent-records` with `{"consent_uuids": [...]}`, up to 200. This is
for an auditor's sample, or the files a downstream store says it is missing.
In the console, **By consent IDs** on Consents takes a pasted list or an
uploaded `.csv`/`.txt`. A CSV with a `consent_uuid` column, such as the
archive's own manifest, is read by that column alone.

**All or none.** An ID that does not exist, or that is outside the caller's
scope, refuses the request: 422 `consent_records_not_found`, with each such ID
in `not_found`. The two cases are not told apart, as on every consent route.
A list is never answered by a quietly shorter archive. The archive, manifest
and auditing are the same as the filtered pull. The audit detail records
`selection: "ids"` or `"filters"`.
