# Rights requests

How a data principal exercises the rights the Act gives her (ss.11 to 14),
and how the Privacy Office answers within a published period with a record it
can produce. The backend's own reference, including the clock arithmetic and
the enforcement inventory, is
[rights.md](../architecture/rights-module.md); this page is the
workflow as people experience it.

## The four rights

| Type | Section | What she asks | What she gets back |
|---|---|---|---|
| `access` | s.11 | a summary of her data, the processing, and who it was shared with | the summary, and any files the office releases with it |
| `correction` | s.12 | an update, completion or correction | the correction applied, or the reason it was not |
| `erasure` | s.12 | erasure of her data | a decision per appearance of her in an asset: erased, redacted, retained or quarantined |
| `grievance` | s.13 | a complaint, usually about how another request was handled | a finding: upheld or not, with the route to the Board |

Every request has a reference like `RR-2026-000042`, minted by the database,
which is what she quotes on the phone, in the public form, and in a grievance.

## Where a request comes from

| Channel | Who | How identity is established |
|---|---|---|
| `portal` | a signed-in data principal | her session |
| `public_form` | anyone, from the rights page | a code sent to a contact on file, or the DPO's manual verification |
| `nominee` | a nominee whose nomination is in effect | the nominee's own sign-in, plus the event evidenced |
| `staff_logged` | the DPO, from an email or a letter | the DPO's verification note |

The public form is deliberately neutral: it issues a reference whether or not
the contact is known, and the code goes only to a contact on file. An
unverified request is closed by the nightly sweep after seven days, and a
stranger who asks after it is told only that it is closed.

A request can be **confined to one consent**: from her consent page she can
ask for erasure of what was collected under that consent alone, and the
holders are then derived from that consent's chain rather than her whole
record.

## The clock

The clock starts at receipt (D0), not at verification, and the due date is
stamped on the row at receipt so a later change in configuration never moves
a running request. The default period is the Rule 14 outer limit.

| Checkpoint | Default | Setting |
|---|---|---|
| Acknowledge | D0 + 2 days | `RIGHTS_ACKNOWLEDGE_WITHIN_DAYS` |
| Tickets issued | D0 + 5 days | `RIGHTS_TICKETS_WITHIN_DAYS` |
| Halfway | midway | derived |
| Collate | D - 5 days | `RIGHTS_COLLATE_BEFORE_DAYS` |
| Respond | D0 + 90 days | `RIGHTS_RESPONSE_PERIOD_DAYS`, `GRIEVANCE_RESPONSE_PERIOD_DAYS` |

The API returns the checkpoints on every request, so the console, the
acknowledgement email and the dashboard cannot disagree about a date.

## The states

```mermaid
stateDiagram-v2
  [*] --> received
  received --> in_progress: verified and classified
  in_progress --> awaiting_holders: a ticket issued
  in_progress --> collating: nothing to ask anyone
  awaiting_holders --> collating: every ticket back, or escalated once
  collating --> closed: respond
  received --> closed: not verified, or reclassified as a withdrawal
```

Closure carries an **outcome**: `complete`, `partial`, `no_records`,
`refused`, `not_verified`, `reclassified_withdrawal`, or for a grievance
`upheld` or `not_upheld`. A response that does not give her what she asked
names the Data Protection Board as the next step.

Moving `received` to `in_progress` needs the request verified and classified;
for an erasure the intent confirmed with her; for a nominee's request the
event evidenced; for a grievance about the DPO, an independent reviewer
assigned. The transitions endpoint says what is missing, and the console
shows it beside a disabled button.

## Holders and tickets

A **holder** is a party that holds her data, derived from the disclosure
records and the assets (`export_line`, `asset_consent`) and confirmed by the
DPO, who may add one by hand. Each confirmed holder gets one **ticket**: the
instruction to return what it holds, addressed to a **respondent** of that
processor.

- An in-house processor's respondent is an account on the platform. The
  ticket reaches them on their dashboard and the console's tickets page, and
  they answer there, with files.
- A third party's respondent is a name and an address. The ticket travels by
  email, with a summary of the request, and the DPO records what came back.

A ticket is a **thread**: it opens with what the office already knows, and
either side may write on it, attaching files. Unread messages are counted on
both ends, so the office's bell rings when a respondent writes and the
respondent's when the office does.

| Ticket state | Means |
|---|---|
| `pending` | holder confirmed, ticket not yet sent |
| `issued` | sent, awaiting the holder |
| `returned` | the holder has answered |
| `unreturned` | the due date passed with no answer |
| `escalated` | reminded formally, once |
| `withdrawn` | the office no longer needs it |

A returned ticket can be **sent back** with a reason when the answer is not
enough; a ticket can be **reassigned** to another respondent, **reminded**,
or **withdrawn**. The last ticket to come back moves the request off
`awaiting_holders`.

## Erasure scope

For an erasure, the office builds the **scope**: one item per appearance of
her in an asset, each proposed and then decided by the DPO as `erase`,
`redact`, `retain` or `quarantine`, with a reason. Items are instructed to the
holder with the ticket and marked applied when confirmed. Applying an item
changes the person's disposition on the `asset_consent` row and never the
asset, because an asset holding three people is not deleted when one of them
asks. A retained item names the legal ground.

**Applied is not done.** Changing a disposition deletes nothing; until the
executor erases from every store (S2-03), an erase or redaction that has been
applied is still work outstanding. An item counts as **done** only with
evidence it was carried out: a quarantine applied is its own evidence (the flag
is the act), and an erase or redaction needs the execution record. A retained
item is not done - it was kept, lawfully, not erased.

## The response

Responding closes the request with an outcome and a response text.

**`complete` has to be earned** (S2-02). A correction or an erasure closes as
complete only when what it asked for was carried out: every holder returned its
ticket, every erasure item is done, and something was actually done - a request
with no item in scope and no holder's return is one nobody carried out, and
`no_records` is the honest answer when nothing is held. Anything short of that
closes `partial`, and the record she receives says, item by item, what happened
to each appearance of her - "quarantined: kept out of any use or release, not
erased", "decided for erasure, not yet carried out" - and lists what is not yet
done, in the file and in the mail. Nothing in it says "erased" for what was
not. The rule is `cmp.domain.rights.execution`; the request detail serves its
answer as `complete_blocked_by`, which is how the console knows to hold
Complete back and say why. Access and grievance are untouched: they ask for a
copy and a decision, not a change.

The response is sent to her by email and appears on her portal page, together with
any **response files** the office released, each downloadable for a bounded
period (`RIGHTS_DOWNLOAD_TTL_DAYS`, 30 by default) and hashed on the row.
She can **dispute** a closed request from the portal, which opens a grievance
linked to it, and a grievance carries the request it disputes.

## Nominees

A data principal names one nominee, by mobile with an optional email, while
she is well. The nominee receives a link and must accept it with a code sent
to the medium they choose; acceptance gives them an account and the reference
they need to act. Acceptance is due within thirty days. Nominations can be
declined, revoked, and are shown to both parties.

When the nominee invokes the nomination they name the **trigger event**,
`death` or `incapacity`, and the DPO evidences it before the request moves.
Death closes the principal's account; incapacity does not. The nomination
records which request invoked it.

**The nominee follows that request to the end.** Signed in, it reads to them
as it does to her: the state, the clock, the path, the response and the files
released with it. They are the person exercising the right, and every message
about the request already goes to them rather than to her, who may be exactly
as incapacitated as claimed. On an incapacity claim she is acknowledged as
well, because her account stays open and the request appears in her own list.

Reading is not acting. Being signed in is enough to see what became of the
request they raised; making another in her name still needs the nominee page
and a code to a contact she recorded, and so does disputing a response, which
makes a new request. A nomination revoked after it was invoked keeps its
request in the nominee's view, marked as no longer in effect: revocation stops
what comes next and does not unask the question they lawfully asked
([ADR 0014](../decisions/0014-a-nominee-follows-the-request-they-raised.md)).

## Grievances

A grievance is linked to the request it disputes, where there is one. A
grievance about the DPO's own handling is **escalated** to the administrator,
who assigns an independent reviewer; the reviewer, not the DPO, then acts on
it. The administrator's scope on the rights register is exactly those
escalations.

## What runs on its own

- The nightly **sweep** (02:30) closes unverified requests past seven days,
  marks tickets unreturned at their due date, and sends the reminders the
  checkpoints call for.
- **Notifications** go out through the Celery `notifications` queue and, in
  development, land in the outbox file.
- The **dashboard** shows the office the requests past a checkpoint, the
  tickets awaiting it, and the unread messages by request; it shows a
  respondent the tickets awaiting them.

## Finding a request

The console's requests list filters by status, kind, overdue and unread; it
has no search box. The API's `GET /requests?q=` takes a reference or part
of one, the contact on the request or on the matched account typed
**whole**, or three letters or more of the name on the form or on the
account. The contact and the name are sealed, so they are matched through
keyed hashes and never compared as text
([the DKMS field list](../dkms/pii-tables-and-fields.md#2-the-eight-lookup-columns-and-their-hash-columns)).
In the console today a request is found by name through the audit trail's
**About** picker, which runs the same match.

## Where this is enforced

| Rule | Where |
|---|---|
| A request may only walk forward, with the prerequisites met | `domain/rights/state_machine.py`, tested per transition |
| Due date fixed at receipt | column on `rights_request`, stamped in the service |
| One live nomination per person | partial unique index on `nomination` |
| A nominee needs a mobile | `trg_nominee_needs_mobile` |
| A nominee reaches the request they raised, and no other | `request_as_nominee`, joined through `nomination.nominee_user_id` |
| A ticket is answered by the respondent it names | scope on `ticket` is `OWN` for every staff role |
| A response file is hashed and time-boxed | `rights_response_file` |
| Every action audited | the audit chain, same transaction |

Open decisions taken as defaults, and how to change them, are listed at the
end of [rights.md](../architecture/rights-module.md) and in
[ADR 0010](../decisions/0010-rights-clock-and-defaults.md).
