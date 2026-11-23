# Analytics, reports and the management role

[ADR 0045](../decisions/0045-analytics-are-figures-counted-from-the-record.md) ·
[Every figure, report and audit report](analytics-metrics.md) (generated)

The **Dashboard** is what needs a person today. **Analytics** (console, under
Analytics) is what happened over a period: the figures an organisation answers
for, compared with the period before and judged against targets; the
ready-made reports over the audit trail; the platform's health; the record of
processing; and reports kept as files, made on request or on a schedule.

## Who sees what

| Role | Tabs |
|---|---|
| Management (`management`, new) | Management scorecard, Analytics, Record of processing, Reports. Both offices combined, or one (*Office*), and the offices side by side (*Breakdown: Office*) |
| Data Protection Officer, Legal PoC | The same for their own office, plus Audit reports and Data quality |
| Administrator | Audit reports, Health, Data quality, Reports, Settings (targets and the small-number threshold). No scorecard, by the product owner's decision |
| R&D User, DCO, DCO Admin, RCO, HR PoC | Your work: the figures of the projects they own, collect for or run in their categories, and Reports of their own work |

The matrix rows are `analytics`, `audit_report`, `health_report`,
`analytics_setting` and `report` ([roles and access](roles-and-access.md));
within them, each metric's and each report kind's audience in
`cmp.core.metrics` decides, and the service checks it again.

## Periods

Every tab has a period: the last 7 or 30 days; this or last month; this or
last quarter, named both ways (*Q4 2026 (Q3 FY 2026-27)*); this or last
calendar year; this or last financial year (April to March, *FY 2026-27*); or
custom dates, at most three years. Days are India's: a period runs from
midnight IST. Each figure is compared with the period before of the same kind,
and its line is drawn by day for a month or less, by week to six months, by
month beyond.

## What a figure is

- A **count** of rows in the period, a **median** (days, hours), a **rate** of
  two counts, or **as things stand** (open requests, consents in force). The
  exact words of each are in the [reference](analytics-metrics.md) and under
  each figure on the page.
- Counted **when asked, from the record**: there is nothing to rebuild, and a
  figure is the record's. A report freezes what it counted.
- **Never a record about a person.** Breakdowns are by request type, channel,
  outcome, project, holder, HR category, duty, office.
- **Small numbers are withheld.** A figure that counts people (*people* in the
  reference) is shown as "fewer than N" when above nought and below the
  threshold, in the figure, its comparison, its line and its breakdown; a rate
  is withheld by the group under it. N is the administrator's (Settings): 1 to
  start with, which withholds nothing. Set it - 5 is usual - before figures of
  small groups are shared.
- **Targets.** A figure with a target is green on it, amber up to its amber
  line, red beyond. The defaults are in the reference; the administrator may
  replace any target and amber line, and every change is on the trail and told
  to the administrators and officers (*A platform setting was changed*).
- **Offices.** An officer reads their office's rows; a row of no office - the
  shared intake of rights requests, a report from the public link, a sign-in -
  counts in each office's view and once in management's combined view.

## Audit reports

Seven ready-made sets of the trail's events, for a period: privileged actions,
access to personal data, configuration changes, security events, the trail's
integrity, regulatory evidence, and reports made and read. They are the trail's
own rows, as the Audit pages show them to the same roles (who acted, in what
role, about whom, on which record); an officer reads their own office's and the
rows of no office. An **evidence pack** is the whole trail of one rights
request or breach, in order, as a PDF.

The nightly check of the audit chain now records a broken chain on the trail
(`audit.verified`, `intact: false`) as well as alerting, so *Audit trail
breaks* counts it.

## Health and data quality

The administrator's Health tab: one-time codes sent and entered by flow, failed
staff sign-ins, accounts paused, requests refused (403), the trail's checks and
breaks, breach notices and board report mail that failed, consent changes
waiting for or refused by DataVault, reports that failed, and the depth of
each worker queue now (read from the broker). Data quality: people with no
confirmed contact, assets with people not matched, processors without a
security confirmation or a country.

## Reports

| | |
|---|---|
| Kinds | Management scorecard, Board pack, Analytics summary, Your work, Audit report, Platform health, Evidence pack, Record of processing, Data quality ([reference](analytics-metrics.md#report-kinds)) |
| Formats | PDF (the platform's document layout, its fonts embedded), Excel (a sheet per section and an About sheet), CSV (UTF-8 with a byte-order mark); every text cell neutralised against formulas |
| Made | By the workers on the `reports` queue (`cmp.reports.generate_report`), after the request that asked for it commits. The row is written first, *queued*; then *ready* with its file, or *failed* with why |
| Kept | Under `UPLOAD_ROOT/reports/`, with its SHA-256; served only while the file still matches it. Kept until somebody who may read it deletes it |
| Read | By the roles that may ask for its kind. An officer reads their own office's reports only - never one of both offices, which carries the other office's figures; the table's office policy says the same. A report of one's own work is its asker's alone. Every download and deletion is on the trail (`report.downloaded`, `report.deleted`) |

**Schedules** make a kind weekly (Mondays), monthly (the 1st) or quarterly (the
1st of a quarter), at 06:00 India time, for the period just ended, and mail it
with the file attached (*A scheduled report*) to the active accounts of the
roles named - only roles that may read that kind. Beat runs
`cmp.reports.run_schedules` hourly at minute 7. A schedule may be paused,
resumed and removed; the reports it made are kept.

## The management role

A login for the people the organisation reports to: no office of its own, so
it reads across both. It writes nothing but its reports and the tickets
addressed to it. It always steps up to a second factor, whatever
`MFA_REQUIRED_ROLES` lists. The administrator gives it on the staff register
like any other role.

## Architecture

| Piece | Where |
|---|---|
| Catalogue: metrics, report kinds, audit reports | `backend/api/src/cmp/core/metrics.py` |
| How each metric is counted; targets, settings, reports and schedules | `cmp/db/repositories/analytics.py` |
| Periods, figures, targets, audit reports | `cmp/domain/analytics/periods.py`, `service.py` |
| Reports and schedules | `cmp/domain/analytics/reports.py`, `cmp/tasks/reports/` |
| Files | `cmp/infrastructure/report_files.py` (PDF through `cmp/infrastructure/pdf`) |
| Routes | `cmp/api/routers/v1/analytics.py`: `/analytics/*`, `/reports/*` |
| Tables | `analytics_target`, `analytics_setting`, `report`, `report_schedule` (migration 0074) |
| Console | `frontend/console/src/app/(app)/analytics`, `src/features/analytics` |

None of it is on the public portal or in the relay's allowlist: it is reached
from the console, inside, as the rest of the console is.
