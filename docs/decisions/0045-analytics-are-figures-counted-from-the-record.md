# 0045: Analytics are figures counted from the record, for the roles that answer for them

- Status: accepted
- Date: 2026-11-23
- Migration: 0074

## Context

The Dashboard answers "what needs me today": queues, counts and a week's
trend. The organisation also needs to answer for a period - how many rights
requests were closed on time last quarter, whether every breach duty was met,
how consent is moving - to the people it reports to, to its officers and to
auditors, and to prove it with reports it keeps. The product owner decided
(2026-11-23):

1. **Management** reads the figures by logging in, *and* receives board packs
   by email.
2. Management reads both offices combined, and either one alone, with the
   other filters. The **administrator** reads the audit and health reports
   only.
3. **Targets** are editable in the console, by the administrator.
4. Counts of people below a **threshold** are withheld; the threshold is
   configurable and starts at 1 for testing.
5. Periods: both the calendar and the April-March **financial year** (this
   ADR's choice, the question being left open).
6. **Every report is kept** until somebody deletes it by hand; the roles that
   may read a report may download it.
7. The roles that do the work get **their own narrow figures**.

## Decision

1. **One catalogue** (`cmp.core.metrics`), like the message catalogue: each
   metric's key, title, exact definition, unit, section, audience, breakdowns,
   default target and amber line. Screens, reports and the generated
   reference (`docs/domain/analytics-metrics.md`) read it; how each is counted
   is one SQL source per key (`cmp.db.repositories.analytics`), and a test
   holds the two together.
2. **Counted when asked, from the record.** No summary tables: every figure is
   the live record's, and nothing has to be rebuilt or backfilled to agree with
   it. The existing indexes carry the queries (the trail on event and time). A
   report freezes what it counted, with its hash. If volumes ever need summary
   tables, they go behind the same catalogue without a screen changing.
3. **Figures, never records.** A metric is a count, a rate of two counts, or a
   median; a breakdown is by something the platform owns (a request type, a
   channel, a project, a holder's label). A metric that counts people is
   withheld - "fewer than N" - in the figure, its comparison, its line and its
   breakdown, when above nought and below the threshold; a rate is withheld by
   the size of the group under it (`analytics_setting`).
4. **The wall stays.** An officer reads their own office, as their session
   reads its rows (row level security on the policed tables, and an explicit
   office filter on the trail); a row of no office counts in each office's
   view. Management (`management`, a new role with no office) chooses both or
   one, and may split by office. Breach figures go to management and the
   officers only. The roles that do the work read their own work through the
   project register's own scope predicate, so the figures and the register
   cannot disagree.
5. **Who reads which part** is the matrix (`analytics`, `audit_report`,
   `health_report`, `analytics_setting`, `report`) and, within it, the
   catalogue's audiences, checked again by the service. The administrator
   reads audit, health and data quality and sets targets and the threshold;
   management, the DPO and the Legal PoC read the scorecard, the analytics and
   the record of processing; the officers also read audit reports and data
   quality for their office.
6. **Management is a read-only login.** It writes nothing but its reports and
   the tickets addressed to it - any member of staff may be asked to answer a
   ticket, and management answers only what it is asked. It always steps up
   to a second factor, whatever `MFA_REQUIRED_ROLES` lists: deployed files
   list roles by name and predate it (as for the breach-only login, ADR 0023).
7. **Audit reports are the trail's own rows**, as the audit pages already show
   them to the same roles: seven ready-made sets of events (privileged actions,
   access to personal data, configuration, security, integrity, regulatory
   evidence, reports). An **evidence pack** is the whole trail of one rights
   request or breach, in order. The nightly chain check now records a broken
   chain on the trail too, so the health figures can count it.
8. **Reports are made by the workers** on the existing `reports` queue
   (`cmp.reports.*`): asked for in a request (written, audited, queued after the
   commit), counted, laid out, rendered as PDF (the platform's own document
   layout), Excel or CSV (formula-neutralised), stored under `reports/` with its
   SHA-256, and served only while the file matches it. Kept until deleted; a
   download and a deletion are on the trail. A report of one's own work is its
   asker's alone. `report` and `report_schedule` are policed by office: a
   report of one office is read by that office, and one of both offices -
   management's combined figures - only by a session of no office, so an
   officer never reads the other office's figures through it.
9. **Schedules** make a kind weekly, monthly or quarterly at 06:00 India time
   for the period just ended (beat `run-report-schedules`, hourly), and mail it
   as an attachment (*A scheduled report*) to the active accounts of the roles
   named - only roles that may read that kind, checked when it is set up.
10. **Console only.** None of this is on the public portal, so none of it is
    in the relay's allowlist (ADR 0035): it is reached from inside, as the rest
    of the console is.

## Consequences

- A figure of last month read today and next week may differ, because the
  record may change (a request closed late, a correction); a report says when
  it was made, and its file does not change.
- Rows of no office (the shared intake, a public incident report, a sign-in)
  appear in both offices' views; management's combined view counts them once.
- A metric added to the catalogue needs a source, a test and a regenerated
  reference; nothing else - the screens list what the catalogue gives them.
- The threshold of 1 withholds nothing. Production should set it (5 is the
  usual choice) before figures of small groups - an HR category - are shared.

## Later (2026-11-24): the page redesigned

The product owner asked for a page more informative to read: charts, and
tiles that open. Recorded in `docs/domain/analytics.md` (Reading the page).
What it changed beyond the screens: `consent.partial` (given in part) joined
the catalogue; a figure and a catalogue entry name a rate's numerator and
denominator; `/analytics/figures` takes `grain`; and the codes sent for the
staff second factor, the portal sign-in and confirming a contact are on the
trail (`auth.otp_requested`, with the flow), which "Codes sent" and "Code
success" had been counting all along and nothing wrote.

## Not decided here

- Summary tables, if the record grows past what live counting answers quickly.
- Free-text addresses for scheduled mail: today only accounts of the roles
  named receive one.
- A management view inside the portal: management uses the console.
