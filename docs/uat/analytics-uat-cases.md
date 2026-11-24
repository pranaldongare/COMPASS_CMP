# Analytics and reports: UAT cases

[ADR 0045](../decisions/0045-analytics-are-figures-counted-from-the-record.md) ·
[How the analytics work](../domain/analytics.md)

Run with seeded data across both offices, and with at least one account of
each role: management, DPO, Legal PoC, administrator, R&D User, DCO, HR PoC.

| # | As | Do | Expect |
|---|---|---|---|
| AN-01 | Administrator | Create an account with the role Management | It signs in with a password and a second factor; the sidebar shows Analytics, Tickets, Notifications, Profile; it lands on Analytics |
| AN-02 | Management | Open Analytics | Tabs: Management, Analytics, Record of processing, Reports. No Audit reports, Health or Settings |
| AN-03 | Management | Choose Office: R&D, then HR, then All offices | The figures change; All offices is not the sum where a row belongs to no office (shared intake) |
| AN-04 | Management | Breakdown: Office | Each figure that allows it is split by DPO office and Legal office |
| AN-05 | DPO | Open Analytics | Their office's figures only; no office picker; Audit reports and Data quality tabs present |
| AN-06 | DPO | Ask for `office=hr` (via the URL or API) | Refused (403) |
| AN-07 | Administrator | Open Analytics | Tabs: Audit reports, Health, Data quality, Reports, Settings. No scorecard |
| AN-08 | Administrator | Settings: set *Closed on time* target 90, amber 80 | Saved; the change is on the audit trail (Configuration changes) and every administrator and officer is mailed *A platform setting was changed* |
| AN-09 | Administrator | Set an amber line above a "higher is better" target | Refused with the reason |
| AN-10 | Administrator | Set the small-number threshold to 5 | Any count of 1-4 people shows as "fewer than 5", with no status; rates over such groups are withheld too |
| AN-11 | Management | Period: This financial year; then Last quarter | Labels read *FY 2026-27* and *Q3 2026 (Q2 FY 2026-27)*; comparison is the year/quarter before |
| AN-12 | Management | Custom dates over more than three years | Refused |
| AN-13 | R&D User | Open Analytics | Your work only: their own projects' figures; another R&D User sees different figures |
| AN-14 | HR PoC | Open Analytics | Your work: the activities in their categories |
| AN-15 | Management | Reports: new Management scorecard, PDF, Last month | Listed as queued, then ready; the PDF opens, shows period, office, who asked, every figure with target and status, and the definitions |
| AN-16 | Management | Board pack PDF | Includes the breaches of the period with their duties done |
| AN-17 | DPO | Open Reports | The scorecard management made for both offices is **not** listed (it carries the Legal office's figures); a scorecard the DPO makes is, for the DPO office, and the Legal PoC cannot see it |
| AN-18 | Administrator | Open Reports | Management's scorecard is not listed |
| AN-19 | R&D User | Your work report, Excel | Listed for them only; another R&D User does not see it |
| AN-20 | Administrator | Audit reports: Privileged actions, last 7 days, after resetting a user's second factor | The reset is listed with who did it; Make this a report gives CSV/Excel/PDF |
| AN-21 | DPO | Evidence pack for a rights request | A PDF of the request's whole trail in order |
| AN-22 | Any reader of a report | Delete it | Confirmed, gone from the list; the trail shows *report.deleted* |
| AN-23 | Any | Download a report | The trail shows *report.downloaded* with the file's SHA-256 |
| AN-24 | Management | New schedule: Management scorecard, monthly, to Management and DPO | Next run is the 1st at 06:00 IST; Administrator cannot be chosen as a recipient |
| AN-25 | Operator | Set the schedule's next run to the past and wait for minute 7 | A report for the month just ended is made and mailed, attached, to every active Management and DPO account |
| AN-26 | Management | Pause, resume, remove the schedule | Each on the trail; reports it made are kept |
| AN-27 | Administrator | Health | Codes sent/entered by flow, failed sign-ins, lockouts, 403s, audit checks and breaks, pipeline failures, queue depth |
| AN-28 | Data principal | Call `/analytics/catalogue` | Refused (403) |
| AN-29 | Administrator | Users, Provision account, role *Management*, with an office | Refused: "this role works across both offices; leave the office empty" |
| AN-30 | Administrator | The same, office left empty | Account created; the register shows the role as *Management*, no office |
| AN-31 | Management | Sign in (`sanjay.kapoor@cmp.local` on a demo database) | Asked for a second factor; lands on Analytics; the sidebar holds Analytics and Tickets only |
| AN-32 | Management | Open `/dashboard`, `/users`, `/requests`, `/breaches` directly | Dashboard sends to Analytics; Users and Requests refused; Breaches not found |
| AN-33 | Administrator | Audit, filter by role *Management* | The management account's sign-ins and report downloads listed |
| AN-34 | Management | Analytics, this quarter | *Needs attention* lists the figures off target, red first; each opens its figure |
| AN-35 | Management | Click a tile | The figure's page: value, status, "x of y", target; the line with the target dashed; *Back to the overview* returns to the same tab and period |
| AN-36 | Management | On a rate's page, choose *Office* under *Broken down* | Each office's share against the target line; a group too small reads "< 5" |
| AN-37 | Management | On a figure's page, choose *Day* with *This financial year* | *Day* is not offered; *Week* and *Month* are |
| AN-38 | Management | Any chart: *Table* | The same numbers as a table; *Chart* returns |
| AN-39 | Management | A figure's page: *CSV* | A file of the line's numbers, one row per bucket, with the status of each |
| AN-40 | DPO | A rights figure's page | *Open Rights requests* is offered; as management it is not |
| AN-41 | Administrator | Analytics, Health | *At a glance* tiles; a period with no nightly check reads *Not checked* |
| AN-42 | Any | Sign in with the second factor, then Health | *Codes sent* and *Codes entered correctly* both count the sign-in; *Code success* is at most 100% |
| AN-43 | Management | Analytics on a phone (390 px) | One column; filters wrap; charts readable; nothing scrolls sideways |
