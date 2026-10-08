# Email notifications: the implementation plan (2026-10-08)

[Notification strategy](README.md)

The request: every module's emails end to end - subject, body, to, cc,
attachment - documented per module, and the gaps built. Decided with the
product owner on 2026-10-08:

| Question | Decision |
|---|---|
| Which modules get new emails | Projects & approvals, Rights (the office's side), Breach deadlines, Accounts & delegation |
| CC | The Privacy Office sets up to 5 per email in Message templates; never on an email with a code, a link, or a person's own record |
| Attachments | Built into the email layer; used only where the recipient owns the content: her consent record on the receipt, and the office's file on a ticket message to its holder. A rights response stays download-only |

## Where it started

26 emails, each to one recipient, no CC and no attachments anywhere. Only
sign-in, consent, rights requests and breaches sent email; projects,
approvals, accounts and delegations sent none, and staff learned of those
events only from the console's bell.

## The plan, and what was done

| # | Step | Status | Where |
|---|---|---|---|
| 1 | **Email layer: CC and attachments.** `send(to, subject, body, cc, attachments)` on every transport; `Cc` header; files make the email `multipart/mixed` after the text and HTML; at most 5 copies and 10 MB of files; copies logged obscured, files by name and size | Done | `infrastructure/email/transport.py` |
| 2 | **Which emails may be copied or carry files** - `COPYABLE`, `ATTACHABLE`, and each email's `to` and `attachment` in words | Done | `core/messages.py` |
| 3 | **`deliver()` adds copies and files** - copies from the office's settings (mirrored to Redis, opened like the recipient), only on a copyable email; files only on an attachable one; neither by SMS | Done | `infrastructure/messaging` |
| 4 | **Copy settings** - table `message_copy` (address sealed, blind index), `PUT /messages/{key}/copies`, the Copy to box in Message templates, every change audited | Done | migration 0046; `domain/messaging/service.py`; console `features/messages/components/copy-to.tsx` |
| 5 | **Attachments in use** - the consent record on the receipt; the office's file on a rights ticket message, to the holder | Done | `tasks/notifications/consent.py`, `tasks/notifications/rights.py` |
| 6 | **Projects** - submitted (every DPO), approved, sent back with the reason, closed with the reason (the owner), collector assigned (the new DCO) | Done | `domain/alerts`, hooked in `domain/projects/service.py` |
| 7 | **Rights, the office's side** - a request arriving from outside (every DPO; never her words), a grievance about the DPO (every administrator), the daily list of what is overdue or due within 7 days (every DPO) | Done | hooked in `domain/rights/service.py` (`create`, `escalate`, `sweep`) |
| 8 | **Breach deadlines** - a duty entering its last sixth, and overdue, once each (every DPO), every 5 minutes; a breach ticket returned (every DPO) | Done | `tasks/maintenance/breach.py` (beat `alert-breach-duties`), hooked in `domain/breach/tickets.py` |
| 9 | **Accounts & delegation** - role changed, console access ended (the person), cover arranged (both people) | Done | hooked in `domain/users/service.py`, `domain/delegations/service.py` |
| 10 | **Docs, generated per module** - `users.md`, `projects.md`, `consent.md`, `rights.md`, `breach.md`, each email end to end from the code; this plan; the strategy | Done | `docs/tools/generate-email-docs.py` |
| 11 | **Tests** - transport (Cc, files, limits), `deliver()` (copies only where allowed, files only where allowed), copy settings (refusals, sealed, audited), each new email reaching the right people and only after the act, the breach alert said once per stage | Done | `tests/unit/infrastructure/`, `tests/integration/test_alerts.py`, `test_message_copy_settings.py` |

## 13 new emails

| Module | Email | To |
|---|---|---|
| Projects | A project is waiting for approval | Every DPO |
| Projects | Your project is approved | The owner |
| Projects | Your project was sent back | The owner, with the reason |
| Projects | A project is closed | The owner, with the reason |
| Projects | You collect for a project | The new Data Collection Owner |
| Rights | A rights request has arrived | Every DPO |
| Rights | Rights requests due soon or overdue | Every DPO, daily |
| Rights | A grievance about the DPO needs a reviewer | Every administrator |
| Breach | A breach duty is due soon or overdue | Every DPO |
| Breach | A breach ticket was answered | Every DPO |
| Accounts | Your role has changed | The member of staff |
| Accounts | Your console access has ended | The person |
| Accounts | Cover arranged | Both people |

All 13 are email only, and all may be copied by the office.

**Since the plan (2026-10-08, migration 0049):** two more rights emails, for a
holder outside the organisation - *Ticket link to an outside holder* (every
email about its ticket: what happened, the date and the link, nothing of the
request) and *Code to open a ticket*. Both are email only and never copied:
they carry a link or a code. With them the platform sends 41 emails
([README](README.md)).

## Left as it is, on purpose

| What | Why |
|---|---|
| A rights response as an attachment | It is her data: download-only from her account keeps the audit and the window |
| A breach ticket message with a file, by email | Breach ticket emails never name the breach (BD-18); the holder reads the thread, and its files, in the console |
| A collector assigned by changing a **source's** owner in the registry | That moves every project using the source at once, by trigger; the project collector email is sent when a site's source or owner is set on a project. Listed for a later pass |
| Cover ending on its date | Nothing records the moment a cover lapses by date; an email would need a sweep of its own |
| SMS for the new alerts | They are for staff, who are reached by email |
