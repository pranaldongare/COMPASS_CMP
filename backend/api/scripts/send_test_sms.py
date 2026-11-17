"""Send one test text through the platform's own SMS transport.

    .venv/bin/python scripts/send_test_sms.py --to 9876543210

The quickest way to know a deployment's SMS settings work, before anybody
waits on a sign-in code. It reads SMS_TRANSPORT and its settings from `.env`
the way the workers do, prints what it will use (never a credential), and
sends one short text through the same transport every platform message uses.

Run it as the workers run: for `sns`, with the same AWS_PROFILE,
AWS_SHARED_CREDENTIALS_FILE, HTTPS_PROXY and NO_PROXY in the environment, or
it proves something about this shell and nothing about them. While the AWS
account is in the SNS sandbox, only a number verified there receives a text.

Exits 0 when the transport accepted the text, 1 when it did not, with the
reason: a refusal that a retry would not change (no credentials, a number SNS
will not send to, a key that may not publish) is said as such; anything else
is the gateway unreachable or busy. "Accepted" is not "received": whether the
phone got it is in the provider's delivery logs.
"""

from __future__ import annotations

import argparse
import os
import sys

from cmp.core.config import settings
from cmp.infrastructure.sms import build_sms_transport
from cmp.infrastructure.sms.transport import to_e164


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--to", required=True, help="The mobile to send the test to")
    args = parser.parse_args()

    kind = settings.sms_transport
    print(f"Transport : {kind}")
    if kind == "sns":
        print(f"Region    : {settings.sms_sns_region}")
        print(f"Sender ID : {settings.sms_sns_sender_id or '(none: the carrier shows a number)'}")
        # Which variables are set, never what they hold.
        for name in ("AWS_PROFILE", "AWS_SHARED_CREDENTIALS_FILE", "HTTPS_PROXY", "NO_PROXY"):
            print(f"{name:<28}: {'set' if os.environ.get(name) else 'not set'}")
        try:
            print(f"To        : {to_e164(args.to, settings.sms_default_country_code)}")
        except ValueError:
            print(f"To        : {args.to} is not a number SNS can send to")
            return 1
    else:
        if kind == "http":
            print(f"Gateway   : {settings.sms_http_url}")
        print(f"To        : {args.to}")
    print("-" * 60)

    body = (
        f"{settings.organisation_name}: this is a test text from the consent management "
        "platform. Nothing needs doing."
    )
    try:
        result = build_sms_transport().send(to=args.to, body=body)
    except (ConnectionError, TimeoutError, OSError) as exc:
        print(f"Not sent  : the gateway is unreachable or busy - {type(exc).__name__}: {exc}")
        return 1
    except RuntimeError as exc:
        print(f"Refused   : {exc}")
        print("A retry will not change this: check the settings and credentials named above.")
        return 1
    if kind == "console":
        print("Written to var/outbox.log: SMS_TRANSPORT=console sends nothing.")
    else:
        print(f"Accepted  : {result.get('message_id') or '(no message id)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
