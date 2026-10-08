# Reviews, and what became of them

[Documentation](../README.md)

The reviews written about this platform, what was done about each finding,
and the decisions still open - in one place, so nobody has to rebuild the
picture from a dozen documents. Kept as of **2026-10-08** (HEAD 833b58f,
migration 0049). Each review document stays as it was written; this page is
where its status lives.

## The reviews

| Date | Review | What it covered | Status |
|---|---|---|---|
| 2026-09-10 | [Implementation review](2026-09-10-implementation-review.md) | An external review of the build: security, scaling, the record of what was done about each finding | Dispositions in the document itself |
| 2026-09-17 | [DPDP Act gap assessment](2026-09-17-dpdp-act-gap-assessment.md) | The Act, section by section, against what the platform does | Below: [the gap rows today](#the-2026-09-17-gap-rows-today) |
| 2026-10-01 | [Frontend architecture review](2026-10-01-frontend-architecture-review.md) | Both portals: UX, security, architecture, scaling, DPDP findings, P1-P3 | Below: [every finding](#the-2026-10-01-review-finding-by-finding) |
| 2026-10-05 | A frontend UX and UI review, with screenshots | Navigation, wording, layout, accessibility, per role | Kept outside the repository. Packages 1-5 done (926c5a9, 04b225b, 9939dde, 0e429b2, f672723, de134df, ce91d31, 2636084); package 6 open, [below](#open-decisions) |

## The 2026-10-01 review, finding by finding

| Finding | What | Status | Where |
|---|---|---|---|
| UX-1 | Whole-notice refusal with a mandatory purpose | Done | 4000084 |
| UX-2 | My consents error states | Done | ff9563f |
| UX-3 | The consent link and sign-in keep a person's progress | Done | 4b6a41d |
| UX-4 | Focus, the phone drawer, language markup | Done; portal controls and errors are English only - waits on owned translations | 30eba23 |
| UX-5 | A list's filters and page live in the URL | Done | de332c1 |
| SEC-1 | The decrypt route checks only that a cookie is present | **Open decision** (senior engineer). Since 0049 it also accepts an outside holder's ticket cookie, also unchecked ([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md), [known gaps](../backend/06-known-gaps.md)). The key service's API does not change | - |
| SEC-2 | Contact throttles keyed by a keyed hash | Done | d04c19c |
| SEC-3 | A refused request keeps its evidence | Done | aabd2ec |
| SEC-4 | Consent checks CSRF; the body limit counts what arrives | Done; the key service has no caller authentication and speaks plain HTTP - a deployment decision | f3db446 |
| DPDP-1 | A returned ticket counts only when it says the work was done | Done; since 0048 also only once the office accepts it | 40fa652, c59d9da |
| DPDP-2, DPDP-3 | Purpose cessation and retention | **Parked** by the product owner 2026-10-05, as S4-01 | - |
| DPDP-4 | Personal data breaches | Done (S3-01 to S3-09, and since) | [breaches.md](../domain/breaches.md) |
| DPDP-5 | Cross-border | By design ([ADR 0020](../decisions/0020-cross-border-transfer-checked-at-export.md)) | - |
| ARCH-1 | An executable CI gate | **Open** (engineering lead): `.github/workflows/ci.yml` still names `cmp_backend`; [ci.yml.proposed](../tools/ci-paths.md) is not applied. Local checks are the gate | - |
| ARCH-2 | The contract check catches what the server takes away | Done | dbb4f61 |
| ARCH-3 | A transition refreshes the notice it published | Done | 606abb9 |
| ARCH-4 | Files shared by the portals | The drift guard is done (f41165f, `frontend/shared-files.txt`); moving them into one package is **open** (engineering lead) | - |
| ARCH-5 | Services write and audit; routers do not | Done | 652fff7 |
| ARCH-6 | A production build must be told the other portal's address | Done | 19af84c |
| SCALE-1 | A durable outbox | **Deferred** on purpose ([ADR 0012](../decisions/0012-side-effects-after-commit.md)) | - |
| SCALE-2 | The SMS adapter retries what is retryable | Done | 32edaed |
| SCALE-3 | A savepoint per imported row | Done | 705bf21 |
| SCALE-4 | A refused key-service batch is narrowed down | Done | 589d768 |
| SCALE-5 | Storage | The unbuilt object backend is refused at startup and `/ready` checks storage (4b1cdd4); the object backend itself is **open** | - |

## The 2026-09-17 gap rows today

| Gap | Status |
|---|---|
| Personal data breach (s.8(6), Rule 7) | Done: the register, the duties and their clocks, the notices, tickets ([breaches.md](../domain/breaches.md)) |
| Children's data and guardian consent (s.9) | A minor is refused outright and an unknown age is asked for (S2-01); the guardian route is **deferred** (D-01 to D-03) |
| Erasure that reaches every store (s.12) | Done ([ADR 0019](../decisions/0019-erasure-reaches-every-store-but-the-record.md)), except backups - **parked** (P-03, with Legal) |
| Correction (s.12) | A person corrects her own name (S3-05, d4b2a66); correction is not taken as a request (2026-10-07); the rest is **parked** ([roles and access](../domain/roles-and-access.md)) |
| Cross-border transfer (s.16) | Done: checked at export, an unknown place refused ([ADR 0020](../decisions/0020-cross-border-transfer-checked-at-export.md)) |
| Retention and purpose cessation (s.8(7)) | **Parked** (S4-01) |
| Consent Manager, Significant Data Fiduciary duties, a register of legal versions, processor oversight | Not built; not scheduled |

## Parked and deferred backlog items

The Sprint 2-4 backlog (pinned at c3ab5fb) is kept outside the repository.
These are the items the documents cite; none is to be built without a fresh
decision.

| Item | What | Cited in |
|---|---|---|
| P-02 | Erasing a storage store the platform does not reach today | [ADR 0019](../decisions/0019-erasure-reaches-every-store-but-the-record.md) |
| P-03 | Backups under erasure: whether a backup holding an erased item is scrubbed or left to expire (there are no backups yet) | ADR 0019, [rights-requests.md](../domain/rights-requests.md), [runbook](../operations/runbook.md) |
| P-06 | The manual breach procedure, with Legal | [runbook](../operations/runbook.md) |
| D-01 to D-03 | The guardian route for a child's data | the 2026-09-17 assessment |
| S4-01 | Purpose cessation and retention (DPDP-2, DPDP-3) | ADR 0019 |
| S4-02, S4-03 | Legacy discovery; holder integration | ADR 0019, ADR 0020 |

## Open decisions

| Decision | Owner | Where it is written |
|---|---|---|
| SEC-1: the decrypt route's cookie-presence check (session or ticket cookie) - validate it with the API, or record an accepted risk | Senior engineer | [ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md), [known gaps](../backend/06-known-gaps.md), [csrf.md](../security/csrf.md) |
| `scripts/reseal.py` turns off append-only triggers to reseal evidence rows: an exception to [ADR 0002](../decisions/0002-evidence-enforced-in-the-database.md)? | Senior engineer | [migrations.md](../database/migrations.md) |
| CI (ARCH-1) and the shared frontend package (ARCH-4) | Engineering lead | [ci-paths.md](../tools/ci-paths.md), [best practices](../frontend/best-practices.md) |
| The key service's caller authentication and transport (SEC-4 rest) | Deployment | [encryption at rest](../security/encryption-at-rest.md) |
| The "without delay" breach target in hours (`BREACH_WITHOUT_DELAY_TARGET_HOURS`, unset) | Legal and the Programme | [ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md), [configuration](../operations/configuration.md) |
| The organisation's own email domains (`BREACH_TICKET_EMAIL_DOMAINS`, `cmp.local` today) - needed before go-live; it decides breach tickets and how a rights holder is reached | Product owner | [ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md), [configuration](../operations/configuration.md) |
| The public rights page's wording on correction, now that correction is not a request | DPO | `api/routers/public/rights.py`, [rights-requests.md](../domain/rights-requests.md) |
| Celery task results (Redis database 2, kept 24 hours; nothing reads them): keep, shorten or ignore them | Engineering lead | [runbook](../operations/runbook.md) |
| Translating the portals' controls and errors (needs owned translations) | Product owner | the 2026-10-05 UX review |
| Notifications as an inbox or a feed; splitting Users into staff and participants | Product owner | the 2026-10-05 UX review |
| UX package 6: contrast on real colour pairs, error summaries on long forms, core journeys at 320px, no interactive element inside another | Frontend | the 2026-10-05 UX review |
| An email to a project's collector when a source's owner changes; an email when a cover ends on its date | Product owner | [notifications plan](../notifications/implementation-plan.md) |

## Known environment issues

- The console browser specs `forms.spec.ts` "registers a project" and
  `routing.spec.ts` "the project form says where an approved project will
  go" fail on a development database grown past the project form's 200
  processors - data, not code ([testing.md](../operations/testing.md)).
