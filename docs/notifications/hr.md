# HR track: the messages it sends

[Notification strategy](README.md) · the design these junctions were built
from. `hr_reconsent_request` and `hr_withdrawal_notice` are in
`core/messages.py` and generated into [consent.md](consent.md) (increments
4 and 6); `rights_transfer_received` follows with increment 7. Where this
page and the generated one differ, the generated one is what is sent.

The HR track adds three junctions and widens two. Every one is email only
unless stated, copyable by the office except where it carries a link, and
never names a participant in a message to a holder: the person is referred
to by employee ID or principal ID.

## 1. Withdrawal notice to the activity's respondents · `hr_withdrawal_notice`

| | |
|---|---|
| When | after a withdrawal on a notice of the `hr` office commits |
| To | each respondent of the activity: the HR PoC (the site's owner) and the default respondent of every live `category_processor` (HRMS owner, HR database owner, vendor contact with an account); one email each, deduplicated by account |
| CC | the office may add copies (copyable) |
| Attachment | none |
| Channels | email |
| Subject | `Consent withdrawn on {activity_name} - stop processing for {principal_ref}` |
| Body | the activity and category, the participant's reference (`EMP-…` when an employee ID is on the account, else the principal ID), the purposes withdrawn and those still in force, "stop processing the data collected under the withdrawn purposes; withdrawal does not by itself erase what was collected", the link to the activity's register in the console, the consent reference |
| Variables | `activity_name`, `category_name`, `principal_ref`, `stopped`, `continuing`, `consent_reference`, `register_url` |
| Sent by | `tasks/notifications/withdrawal.py::send_hr_withdrawal_notice`, dispatched from `domain/consent/service.withdraw` through `dispatch_optional` |

## 2. Re-consent request · `hr_reconsent_request`

| | |
|---|---|
| When | an activity is upgraded to a template version flagged `reconsent_required`; one per participant holding a current artefact on the activity |
| To | the participant (her preferred contact) |
| CC | never (carries a link) |
| Attachment | none |
| Channels | email, SMS |
| Subject | `Your consent for {activity_name} needs renewing` |
| Body | what changed, in Legal's words from the version's `change_summary` (add this column to `template_version` in 0053 if Legal wants its own words; otherwise the version's title), that her existing consent stands until she decides, the link |
| Variables | `activity_name`, `change_summary`, `link_url` |
| Sent by | `tasks/notifications/consent.py::send_reconsent_request`, dispatched from `domain/hr/activities.upgrade` |

## 3. A request moved between offices · `rights_transfer_received`

| | |
|---|---|
| When | `POST /requests/{uuid}/transfer` commits |
| To | every officer of the receiving office (`legal` for `hr`, `dpo` for `rnd`) |
| CC | copyable |
| Attachment | none |
| Channels | email |
| Subject | `Rights request {reference} transferred to your office` |
| Body | the reference, the type, D0 and the due date (unchanged), who transferred it, the reason, the link |
| Variables | `reference`, `request_type`, `received_at`, `due_at`, `from_office`, `reason`, `request_url` |

## Widened

| Junction | Change |
|---|---|
| `rights_request_received` | goes to the officers of the request's office; for a request in the shared intake, to both offices |
| `rights_due_digest` (the daily list) | one per office, listing that office's requests |
| `breach_duty_due`, `breach_ticket_returned` | to the officers of the breach's office |

## Unchanged, and why

The participant's own confirmation of a withdrawal (`withdrawal_confirmation`)
and her consent receipt (`consent_receipt`, with her PDF attached) are the
same on both tracks: the record is hers whichever office governs it.
