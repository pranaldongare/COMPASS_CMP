"""Messages to a person about their own record, and to staff about theirs.

Distinct from `tasks.authentication`, which carries the codes somebody is
actively waiting for. These are wanted promptly, not urgently, and route to the
`notifications` queue so they cannot delay a sign-in.

All dispatched optionally: the record they describe is already written, and the
message is a courtesy on top of it. Every one sends through a junction in
`cmp.core.messages`, which is what makes the office's list of editable
messages complete.
"""

from cmp.tasks.notifications.batch import send_office_note
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
from cmp.tasks.notifications.withdrawal import send_withdrawal_confirmation

# A module not imported here is a task the worker never registers: the API
# queues it by name, the worker answers "unregistered task", and the message is
# lost quietly. `tests/unit/tasks/test_registry.py` checks the roster.
__all__ = [
    "send_consent_receipt",
    "send_holder_instruction",
    "send_nomination_accepted",
    "send_nomination_code",
    "send_nomination_invitation",
    "send_office_note",
    "send_rights_acknowledgement",
    "send_rights_closed",
    "send_rights_response",
    "send_rights_response_ready",
    "send_rights_verification_code",
    "send_ticket_message",
    "send_ticket_reminder",
    "send_withdrawal_confirmation",
]
