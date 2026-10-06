"""Send one test email through the platform's own email transport.

    .venv/bin/python scripts/send_test_email.py --to you@organisation.example

The quickest way to know a deployment's mail settings work, before anybody
waits on a sign-in code: it reads `.env` the way the API and the worker do,
prints what it will use - the server, the port, how the connection is
protected, the sender and the login name, never the password - and sends
through the same `SmtpEmailTransport` every platform message goes through.

Exits 0 when the server accepted the message, 1 when it did not, with the
reason: a refusal that a retry would not change (a wrong login, a sender or
address refused, a certificate that does not verify) is said as such; anything
else is the server unreachable or busy. With EMAIL_TRANSPORT=console it
writes to var/outbox.log instead, and says so.
"""

from __future__ import annotations

import argparse
import sys

from cmp.core.config import settings
from cmp.infrastructure.email import EmailRejected, build_email_transport
from cmp.infrastructure.email.transport import sender_name, smtp_security


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", required=True, help="The address to send the test to")
    parser.add_argument("--subject", default=f"{settings.organisation_name}: test email")
    args = parser.parse_args()

    print(f"Transport : {settings.email_transport}")
    if settings.email_transport == "smtp":
        print(f"Server    : {settings.smtp_host}:{settings.smtp_port} ({smtp_security()})")
        print(f"Login     : {settings.smtp_username or '(none - an open relay)'}")
        print(f"CA file   : {settings.smtp_ca_file or '(system authorities)'}")
    print(f"From      : {sender_name()} <{settings.notification_email_from}>")
    print(f"To        : {args.to}")
    print("-" * 60)

    body = (
        "Hello,\n\n"
        f"This is a test email from the {settings.organisation_name} consent management "
        "platform, sent to check its mail settings. Nothing needs doing.\n"
    )
    try:
        result = build_email_transport().send(to=args.to, subject=args.subject, body=body)
    except EmailRejected as exc:
        print(f"Refused   : {exc}")
        print("A retry will not change this: check the settings named above.")
        return 1
    except OSError as exc:
        print(f"Not sent  : the server is unreachable or busy - {type(exc).__name__}: {exc}")
        return 1
    if settings.email_transport == "console":
        print("Written to var/outbox.log (EMAIL_TRANSPORT=console delivers nothing).")
    else:
        print(f"Accepted  : {result.get('message_id', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
