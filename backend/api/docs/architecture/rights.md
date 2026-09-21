# Rights requests

Sections 11 to 14 of the DPDP Act give a data principal four things to ask for
and one person to name: access, correction, erasure, a grievance, and a
nominee. This module is the record of the asking - received when, verified
how, what every holder of her data was told to do, what was decided about each
thing held, and what she was told in reply - all against a clock that starts
on receipt.

The flows follow the five Privacy Engineering diagrams (access, erasure,
redaction of assets holding more than one person, nomination, grievance).
Where a diagram left a question open, the default taken is stated in
[Open decisions](#open-decisions) so it can be changed deliberately.

## The clock

Every date is relative to two fixed points: **D0**, receipt, and **D**, the
published response period after it. Rule 14 sets an outer limit of ninety days
and requires the period to be published, so `RIGHTS_RESPONSE_PERIOD_DAYS`
defaults to 90 and the rights page states it. Grievances have their own
setting with the same default.

| Checkpoint | When | Setting |
|---|---|---|
| Acknowledge | D0 + 2 | `RIGHTS_ACKNOWLEDGE_WITHIN_DAYS` |
| Tickets issued | D0 + 5 | `RIGHTS_TICKETS_WITHIN_DAYS` |
| Halfway | D0 + (D − D0) / 2 | derived |
| Collate | D − 5 | `RIGHTS_COLLATE_BEFORE_DAYS` |
| Respond | D | `RIGHTS_RESPONSE_PERIOD_DAYS` |

Two decisions carry the weight:

* **The clock starts on receipt, not on verification.** A slow verification
  would otherwise quietly eat the window.
* **`due_at` is stored on the row at receipt.** A period changed in
  configuration applies to the next request, never to one already running.

`cmp.domain.rights.clock` computes the checkpoints; the API returns them on
every request so the console, the acknowledgement email and the dashboard
cannot disagree.

## The state machine

Five states, walked forward. Closure carries an outcome.

| From | To | Actor | Requires |
|---|---|---|---|
| `received` | `in_progress` | DPO | verified; classified; erasure: intent confirmed; nominee: event evidenced; grievance about the DPO: reviewer assigned |
| `in_progress` | `awaiting_holders` | DPO | a ticket issued |
| `in_progress` | `collating` | DPO | no ticket outstanding |
| `awaiting_holders` | `collating` | DPO | every outstanding ticket returned, or escalated once |
| `collating` | `closed` | DPO, via `respond` | erasure: every scope item decided |

The early exits on the diagrams - not verified, not a rights request, she
meant withdrawal, the event not evidenced - are **actions** that close the
request with an outcome, permitted from any state before collation. They are
not transitions, because a request is not "moved to not verified" the way it
is moved to in progress.

The administrator is an actor only where the grievance is about the DPO.
`cmp.domain.rights.state_machine` is pure and tested over all 175 (from, to,
role) combinations.

## Identity

Three methods, recorded on the row: `session` (she is signed in), `code` (a
one-time code to the channel already on file - never to a contact typed on
the form), `manual` (the DPO records how, with a reason). The public form
replies with one neutral sentence whether or not the contact matched anyone,
and the verification step says "invalid or expired code" whether the code was
wrong or never issued. A public-form request that never verifies is closed by
the nightly sweep after `RIGHTS_UNVERIFIED_CLOSE_DAYS`.

## Holders and tickets

Holders are derived from the records - `export_line` says who received a file
with her in it, `asset_consent` says whose data source captured her - and
confirmed by the DPO, who adds what the records miss. One ticket per confirmed
holder, addressed to one of the processor's **respondents** (0016): an account
on the platform for an in-house team, who sees the ticket on the dashboard and
the console's tickets page, or a name and an address for a third party, who
is written to. A ticket is a **thread** (0017) that opens with the brief and on
which either side writes, with files; unread messages are counted at both ends
and the office's count is `GET /requests/attention`. A ticket can be
withdrawn, reassigned or reminded (0018), and a returned one sent back with a
reason (0020). Each has a due date that defaults to
halfway. A holder that misses its date is escalated once; the transition to
collation then opens, and the response goes out **partial and on time**, with
the gap named. The server refuses to call a response with an unreturned
ticket "complete".

## Erasure and redaction

The scope is one row per active appearance of her in a collected asset
(`asset_consent`). Each row gets a decision and its basis:

* **erase** - only where nobody else appears in the asset;
* **redact** - the asset also holds other people, whose validly given consent
  would be destroyed by deleting it (decision D-09);
* **retain** - a retention floor binds even against her request (Rule 6, Rule
  8(3)); stated in the response, and the sweep notes the day it passes;
* **quarantine** - removal cannot be assured, so the asset is held back from
  release while the DPO decides.

Applying a decision sets **her junction row's disposition** and never touches
`data_asset`. Erasure and redaction wait for the holder's returned ticket:
the platform records erasure, it does not perform it. Consent artefacts are
never erased - s.6(4) depends on their surviving.

## Grievance

Linked to the request it is about where there is one. A complaint about the
DPO is escalated: the DPO is locked out of deciding it and the administrator,
as the independent reviewer, assigns a reviewer and decides. Not upheld is a
legitimate outcome and carries the Board route. Upheld names a remedy and can
re-run the original request as a new one, linked to the decision.

## Nomination

She names a nominee while well: name, mobile, an optional email, and which of her rights he may exercise. When he invokes it he names the trigger event, death or incapacity, and the nomination records the request that invoked it (0022); death closes her account, incapacity does not. Pending until he accepts, revocable by her at any time; one live nomination per person. The acceptance link goes to every contact she recorded, and the link alone accepts nothing: the nominee chooses one of those contacts, shown masked, receives a code there, and enters it to accept or to decline - so a link-holder cannot answer on his behalf either way. When the time comes he identifies himself with whichever recorded contact he types, and the code goes to that one. The nominee is written to, not her.

## Surface

| Audience | Routes |
|---|---|
| Public | `POST /rights/requests`, `POST /rights/requests/verify`, `GET /rights/nominations/{token}`, `POST /rights/nominations/{token}[/code|/accept|/decline]`, `POST /rights/nominee/start`, `POST /rights/nominee/requests` |
| Data principal | `GET/POST /me/requests`, `GET /me/requests/{uuid}[/trail|/download|/files/{uuid}]`, `POST /me/requests/{uuid}/dispute`, `POST /me/consents/{uuid}/erasure-request` (0019), `GET/POST/DELETE /me/nominations` |
| Respondent (any staff role) | `GET /tickets`, `GET /tickets/{uuid}`, `POST /tickets/{uuid}/messages`, `POST /tickets/{uuid}/respond`, files on messages |
| DPO (administrator: escalated grievances only) | `GET/POST /requests`, `GET /requests/attention`, `GET /requests/{uuid}[/transitions|/trail|/download]`, one action route per step on the path, the ticket routes (issue, message, send back, withdraw, reassign, remind, escalate), and `POST /requests/{uuid}/files` for what is released with the response (0021) |

Every write is audited with the request reference in its detail, so
`GET /requests/{uuid}/trail` reads one request's story across the four tables
that make it up, and the data principal reads the same rows on her own page.

## Open decisions

Taken as defaults, and changeable without unwinding a record:

| Question | Default here |
|---|---|
| D, the response period | 90 days, the Rule 14 outer limit; `RIGHTS_RESPONSE_PERIOD_DAYS` |
| A separate grievance period | Same default; `GRIEVANCE_RESPONSE_PERIOD_DAYS` |
| Who reviews a complaint about the DPO | The administrator role |
| More than one nominee | No - one live nomination per person |
| Partial scope for a nominee | Yes - per right |
| A nomination when she withdraws all consent | Survives; it is about her rights, not her consent |
| The standard of proof for death or incapacity | Recorded as the DPO's note; the standard itself is Legal's to publish |
| Evidence accepted from a third-party lab | A file and a summary, kept with the ticket and hashed |
| Quarantine's time limit | None; it persists until the DPO decides |
| Backups | Out of scope; not restored or scrubbed by any of this |

## Since the first cut

The module shipped with migration 0013 and grew through 0016 to 0022 without
changing the meaning of a stored record: respondents per processor, the
ticket thread, ticket robustness, a request confined to one consent, send-back,
response files, and the invoked nomination. The workflow as people experience
it, with the console and portal pages, is in
[docs/domain/rights-requests.md](../../../docs/domain/rights-requests.md); the
defaults above are recorded as
[ADR 0010](../../../docs/decisions/0010-rights-clock-and-defaults.md).
