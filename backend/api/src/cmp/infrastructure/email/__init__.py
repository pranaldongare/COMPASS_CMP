"""Email delivery.

`transport.py` is the seam a deployment replaces. The words live in
`cmp.core.messages`, and the only caller is `cmp.infrastructure.messaging`.
"""

from cmp.infrastructure.email.transport import (
    ConsoleEmailTransport,
    EmailTransport,
    NullEmailTransport,
    SmtpEmailTransport,
    build_email_transport,
)

__all__ = [
    "ConsoleEmailTransport",
    "EmailTransport",
    "NullEmailTransport",
    "SmtpEmailTransport",
    "build_email_transport",
]
