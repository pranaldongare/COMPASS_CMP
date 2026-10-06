"""Send one test email through the platform's own email transport.

    .venv/bin/python scripts/send_test_email.py --to you@organisation.example

The quickest way to know a deployment's mail settings work, before anybody
waits on a sign-in code. It reads the five email settings from `.env` the way
the API and the worker do - SMTP_SERVER, SMTP_PORT, SMTP_USERNAME,
SMTP_PASSWORD, SENDER_EMAIL - prints what it will use (never the password),
and sends a sample through the same transport and layout every platform
message uses: header, a code, a button, the footer.

Exits 0 when the server accepted the message, 1 when it did not, with the
reason: a refusal that a retry would not change (a wrong login, a sender or
address refused, a certificate that does not verify) is said as such; anything
else is the server unreachable or busy. With SMTP_SERVER empty it writes to the
local outbox instead, and says where to open the laid-out email.
"""

from __future__ import annotations

import argparse
import sys

from cmp.core.config import settings
from cmp.infrastructure.email import EmailRejected, build_email_transport
from cmp.infrastructure.email.transport import connection_for, sender_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--to", required=True, help="The address to send the test to")
    parser.add_argument("--subject", default=f"{settings.organisation_name}: a test email")
    args = parser.parse_args()

    mode = settings.email_mode
    where = "the mail server" if mode == "smtp" else "the local outbox (SMTP_SERVER is empty)"
    print(f"Sends to  : {where}")
    if mode == "smtp":
        connection = connection_for(settings.smtp_port)
        print(f"Server    : {settings.smtp_host}:{settings.smtp_port} ({connection})")
        print(f"Login     : {settings.smtp_username or '(none)'}")
    print(f"From      : {sender_name()} <{settings.notification_email_from}>")
    print(f"To        : {args.to}")
    print("-" * 60)

    body = (
        f"This is a test email from the {settings.organisation_name} consent management "
        "platform, sent to check its mail settings. Nothing needs doing.\n\n"
        "A code looks like this:\n\n    482913\n\n"
        "And a link like this:\n"
        f"{settings.public_base_url}\n\n"
        f"If you were not expecting this message, please tell the Privacy Office at "
        f"{settings.organisation_name}."
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
    if mode == "smtp":
        print(f"Accepted  : {result.get('message_id', '')}")
    else:
        print("Written to var/outbox.log.")
        if result.get("preview"):
            print(f"Open it   : {result['preview']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
