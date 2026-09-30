# Personal data breaches

What the platform does when personal data it is responsible for is breached:
section 8(6) of the Act, Rule 7 of the DPDP Rules, and the CERT-In Directions
of 2022. The decision behind the shape is
[ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md);
the code is `cmp.domain.breach`, the routes are under `/breaches`, and the
console's pages are **Breaches** in the DPO's menu.

## Where the platform ends

The platform is the **system of record**. It records the breach, tracks every
duty's clock, and holds the evidence that each duty was done. **People**
contain the breach, preserve forensic evidence, decide whether it is a personal
data breach, and submit to the Board and to CERT-In through those bodies' own
channels. The platform never contains anything and never talks to a regulator:
a submission is recorded after a person has made it, with the reference the
regulator returned.

## Who can see it

The DPO, and nobody else. The resource is `breach`, and its guard answers
every other role **404**, not 403 - on the register, on a breach that exists,
and on a write alike - so that a breach being handled is not itself disclosed
to a colleague walking uuids ([ADR 0004](../decisions/0004-scope-in-the-where-clause.md)).
The administrator, who reads the audit trail, sees that breach events occurred
and their reference (`Breach BR-2026-0001`), never a title or a reason, and
cannot follow the link.

## Recording a breach

**Breaches → Record a breach.** Three things are asked for, and every time is
typed in, never filled with "now":

| Field | Means | Anchors |
|---|---|---|
| First noticed (`detected_at`) | When the event was first noticed | CERT-In's six hours |
| Began (`began_at`) | When it started, if known. An assessment may revise it | the timing in 7(1)(a), 7(2)(a) |
| Where it occurred | The platform's own database, a processor, a data source, or elsewhere (in words) | 7(2)(a); S3-02 derives who was touched from it |

A breach recorded five hours after it was noticed has one hour of CERT-In time
left, and the register says so. A time in the future is refused, and so is a
start after detection.

The breach gets a reference, `BR-<year>-<n>`, which is what the office quotes
to the Board and to CERT-In. Its title and the words describing where it
occurred are sealed like every other narrative the office writes.

## The determination

Whether the event is a personal data breach under s.2(u) - *pending*, *yes* or
*no* - with the reasoning and who made it. **The platform records it and never
computes it.** Nothing infers *no* from encryption: DPDP has no encryption
exemption and no severity threshold, and whether exposed data was sealed bears
only on this judgement, which is a person's. Whether a leak of sealed data whose
key was not exposed is a breach at all is Legal's question, not the code's.

A revision is a new row; the latest is current, and every earlier one stays for
the report.

- **Yes** carries `became_aware_at`: when the organisation became aware a
  personal data breach had occurred. It anchors every DPDP duty and cannot come
  before detection. It creates the three DPDP duties below, or reinstates any a
  previous *no* set aside, with clocks from this time.
- **No** marks those three duties not applicable, citing this determination.
  A duty already done stays done.
- **Pending** changes no duty.
- **CERT-In** is untouched by all three: it stands on its own test.

## The assessment

The facts Rule 7 asks for, revised as knowledge grows. Each revision is a new
row and the latest is current; the page shows the latest and how many came
before.

| Fact | Rule |
|---|---|
| Nature and extent | 7(1)(a), 7(2)(a) |
| Likely impact | 7(2)(a) |
| Consequences likely for the people affected | 7(1)(b) |
| The data categories exposed - and for each, whether its values were sealed and whether its key was exposed | the determination; the report |
| Events, circumstances and reasons | 7(2)(b)(ii) |
| Mitigation implemented, under way or proposed | 7(1)(c), 7(2)(b)(iii) |
| What people can do to protect themselves | 7(1)(d) |
| Findings on the person who caused it - **sealed; it may name an employee** | 7(2)(b)(iv) |
| Remedial measures against recurrence | 7(2)(b)(v) |
| Who answers people's questions | 7(1)(e) |

The categories are recorded per category because DKMS seals personal fields,
not relationships: who consented to what sits in plaintext, so "was it
encrypted" has more than one answer for most breaches. A key cannot be marked
exposed for a category that was not sealed. **No code reads these flags to
decide a duty**; a source test fails if anything but the assessment itself
names them.

## The duties

One record per duty, created when its trigger is met. They run in parallel on
their own clocks; nothing waits for the assessment.

| Duty | Created when | Due | Basis |
|---|---|---|---|
| Report to CERT-In | **Mark reportable to CERT-In** | 6 hours from first noticed | CERT-In Directions 2022, IT Act s.70B |
| Board - initial intimation | determination *yes* | without delay | Rule 7(2)(a) |
| Board - detailed report | determination *yes* | 72 hours from awareness, or the date the Board allows | Rule 7(2)(b) |
| Principals notified | determination *yes* | without delay | Rule 7(1) |

- **A due time is stored when the duty is created and never recomputed.** A
  change of configuration - or of the code's hours - moves nothing already
  running.
- **Without delay** has no statutory hours, so it has no due time. The register
  shows the time elapsed since awareness and flags it against an internal target,
  `BREACH_WITHOUT_DELAY_TARGET_HOURS`. **That target is not set**: what it should
  be is Legal's and the Programme's decision, and until it is made the register
  shows the elapsed time and flags nothing.
- **Recording a submission** (Board and CERT-In duties) is a new row: when it
  was made, as entered, and the reference the regulator returned, which is
  required. A submission before its clock started is refused.
- **The Board's extension** of the detailed report records when it was asked
  for and the date allowed, which becomes the report's due time as a new row.
  The initial intimation's clock does not move.
- **Principals notified** cannot be completed by hand. It completes when every
  affected principal's notice is delivered or its failure recorded after retry
  (S3-03).

Each duty's clock reads, in the console: time left or overdue for a dated duty;
time since awareness for one due without delay, and whether it is past the
target once one is set. Overdue rows are marked.

## Who it touched

Rule 7(1) asks for a notice to *each* affected principal, to the best of the
fiduciary's knowledge. **Who it touched** on a breach's page derives the list
from the records, and the DPO confirms it.

| Where it happened | Who the records place there |
|---|---|
| A processor | Everyone in files exported to it (`export_line`, to the line's destination processor) |
| A data source | Everyone captured in its assets and not yet erased from them (`asset_consent`). Bystanders - people in frame who never consented - have no account and are not listed |
| The platform's own database | Everyone with a row in the affected tables, written within a window (either end may be open) |

The first two read the same relation a rights request reads to find a
person's holders (`db/repositories/holdings.py`), from the other end. For the
database, each table that holds something about a principal is mapped to the
person it is about and when the row was written
(`breaches.PLATFORM_TABLES`); a sealed table that cannot be traced to an
account says why (`NOT_ABOUT_A_PRINCIPAL`), and a test fails for one that does
neither. No table is ticked for a database breach until the DPO ticks it:
every table since the beginning is everyone on the platform.

**Show what the records say** previews the people, counted and sampled, before
anything is written. **Confirm the list** records a **revision**: what it was
derived from, how many the records found, how many were left out, how many were
added by hand, and how many were newly listed. The DPO may:

- **leave out** people the records wrongly include - the left-out count is on
  the revision;
- **add** people the records cannot show, found by contact or part of a name.

**Nobody listed is ever removed.** A later revision adds only people not
already listed - each keeps the revision that first listed them - and every
earlier row stays as it was. A notice already sent cannot be unsent, and
listing too many is the safe side of Rule 7. Each person a revision adds is
notified in turn (S3-03).

## Open and closed

A breach is open or closed, and nothing else: the duties carry the rest. It
**closes** only when it has been determined and every applicable duty is done
or not applicable - the page lists what is still in the way. It **reopens** with
a reason, recorded in its history, when something new is found. While closed,
nothing about it can be recorded.

## What the database holds

| Table | Holds |
|---|---|
| `breach` | The breach as recorded. Only its `status` may change, by trigger (`cmp_breach_status_only`) |
| `breach_status_history` | Every open and close, with the reason for a reopening. Append-only |
| `breach_determination` | Every determination, with its reasoning and, for *yes*, the time of awareness. Append-only |
| `breach_assessment` | Every revision of the facts. Append-only |
| `breach_obligation` | One row per duty per breach, with its stored due time and the moment its clock runs from. Append-only; one of each kind per breach, by unique constraint |
| `breach_obligation_event` | Everything that happens to a duty afterwards: completed, not applicable, reinstated, extended, reopened. Append-only |
| `breach_affected_revision` | Each confirmation of who it touched: the scopes, the counts, a sealed note. Append-only |
| `breach_affected` | Each person listed, once per breach (`breach_affected_once`), with the revision that first listed them and what put them there - exports, assets or tables, never a value. Append-only |

Every write takes the breach row first (`FOR UPDATE`), so two people recording
at once act one after the other: two determinations of *yes* sent together
create each duty once.

## The trail

Every change writes an audit row against `breach`: `breach.recorded`,
`.determined`, `.assessed`, `.cert_in_marked`, `.obligation_created`,
`.obligation_completed`, `.obligation_not_applicable`,
`.obligation_reinstated`, `.obligation_extended`, `.affected_revised` (with the counts, and nobody's name or id), `.closed`, `.reopened`. The
detail carries the reference, the outcome, which duty, a due time and that a
reason was given - never the office's words, which are sealed on their rows
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).

## Open questions

Owned by people, and not decided by the code:

| Question | Owner |
|---|---|
| Whether an event is a personal data breach - above all a leak of sealed data whose key was not exposed | Legal |
| The internal target for "without delay" | Legal and the Programme |
| Who answers principals' questions (Rule 7(1)(e)) | Legal |
| Who files with CERT-In - the DPO or corporate security. Today only the DPO can record it | Security and Legal |
