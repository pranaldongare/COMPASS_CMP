"""Messages to a person about their own record, and to staff about theirs.

Distinct from `tasks.authentication`, which carries the codes somebody is
actively waiting for. These are wanted promptly, not urgently, and route to the
`notifications` queue so they cannot delay a sign-in.

All dispatched optionally: the record they describe is already written, and the
message is a courtesy on top of it. Every one sends through a junction in
`cmp.core.messages`, which is what makes the office's list of editable
messages complete.
"""

from cmp.tasks.notifications.alerts import (
    send_breach_duty_due,
    send_breach_ticket_returned,
    send_delegation_arranged,
    send_project_approved,
    send_project_closed,
    send_project_collector_assigned,
    send_project_sent_back,
    send_project_submitted,
    send_rights_due_digest,
    send_rights_grievance_about_dpo,
    send_rights_request_received,
    send_staff_access_ended,
    send_staff_role_changed,
)
from cmp.tasks.notifications.batch import send_office_note
from cmp.tasks.notifications.breach import send_breach_notice
from cmp.tasks.notifications.breach_tickets import send_breach_ticket_waiting
from cmp.tasks.notifications.consent import send_consent_receipt
from cmp.tasks.notifications.rights import (
    send_holder_instruction,
    send_nomination_accepted,
    send_nomination_code,
    send_nomination_invitation,
    send_rights_acknowledgement,
    send_rights_closed,
    send_rights_response,
    send_rights_response_ready,
    send_rights_verification_code,
    send_ticket_message,
    send_ticket_reminder,
)
from cmp.tasks.notifications.staff import (
    send_breach_ticket_access,
    send_contact_added_for_you,
    send_staff_invitation,
)
from cmp.tasks.notifications.withdrawal import send_withdrawal_confirmation

# A module not imported here is a task the worker never registers: the API
# queues it by name, the worker answers "unregistered task", and the message is
# lost quietly. `tests/unit/tasks/test_registry.py` checks the roster.
__all__ = [
    "send_breach_duty_due",
    "send_breach_notice",
    "send_breach_ticket_access",
    "send_breach_ticket_returned",
    "send_breach_ticket_waiting",
    "send_consent_receipt",
    "send_contact_added_for_you",
    "send_delegation_arranged",
    "send_holder_instruction",
    "send_nomination_accepted",
    "send_nomination_code",
    "send_nomination_invitation",
    "send_office_note",
    "send_project_approved",
    "send_project_closed",
    "send_project_collector_assigned",
    "send_project_sent_back",
    "send_project_submitted",
    "send_rights_acknowledgement",
    "send_rights_closed",
    "send_rights_due_digest",
    "send_rights_grievance_about_dpo",
    "send_rights_request_received",
    "send_rights_response",
    "send_rights_response_ready",
    "send_rights_verification_code",
    "send_staff_access_ended",
    "send_staff_invitation",
    "send_staff_role_changed",
    "send_ticket_message",
    "send_ticket_reminder",
    "send_withdrawal_confirmation",
]
