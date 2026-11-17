"""Where an SMS actually goes.

The same shape as the email transport, and separate for a reason that is not
symmetry: a data subject signing in with a mobile number gets their one-time
code this way, and SMS has failure modes email does not — silent drops, carrier
filtering, per-country delivery rules. Keeping it a distinct seam means a
deployment can use a real SMS provider without touching how email is sent, and
an SMS outage cannot take email down with it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Final, Protocol, runtime_checkable

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.infrastructure.email.transport import obscure
from cmp.validation.contacts import normalise_mobile

log = get_logger("cmp.infrastructure.sms")


class GatewayBusy(ConnectionError):
    """The gateway is there but cannot take the message now: 429 or 5xx.

    A ConnectionError, so every message task's retry policy covers it.
    """


@runtime_checkable
class SmsTransport(Protocol):
    def send(self, *, to: str, body: str) -> dict[str, object]:
        """Deliver, or raise. Failure is an exception, never a return value."""
        ...


class ConsoleSmsTransport:
    """Development. Writes to the same outbox the email transport uses.

    One file rather than two: a developer completing a sign-in does not care
    which channel the code came over, and hunting across two files for it is
    exactly the friction this exists to remove.
    """

    def __init__(self, outbox_path: str | None = None) -> None:
        from pathlib import Path

        self._path = (
            Path(outbox_path) if outbox_path else Path(settings.upload_root).parent / "outbox.log"
        )

    def send(self, *, to: str, body: str) -> dict[str, object]:
        if settings.is_production or settings.environment == "staging":
            # Before September 2026 this returned `delivered: True` here while
            # writing nothing, which is the one thing a transport must not do.
            raise RuntimeError("The console SMS transport does not deliver outside local/test")
        try:
            from datetime import UTC, datetime

            self._path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).isoformat(timespec="seconds")
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(f"\n{'=' * 78}\n{stamp}  [sms]  to: {to}\n{'-' * 78}\n{body}\n")
        except OSError as exc:  # pragma: no cover
            log.warning("sms.outbox_unavailable", error=str(exc))

        from cmp.infrastructure import devcodes

        devcodes.record(channel="sms", to=to, text=body)
        log.info("sms.delivered", to=obscure(to), transport="console")
        return {"channel": "sms", "transport": "console", "delivered": True}


class HttpSmsTransport:
    """A JSON POST to an SMS gateway, with a bearer token.

    The body is `{"to", "body", "from"}`. Anything provider-specific lives in a
    small adapter in front of the gateway, so this code holds no provider SDK
    and the platform's secrets stay one token. The gateway answers 2xx for
    accepted; anything else is a failure and the task retries.
    """

    def __init__(self, *, url: str, token: str, sender: str, timeout_s: float) -> None:
        self._url = url
        self._token = token
        self._sender = sender
        self._timeout_s = timeout_s

    def send(self, *, to: str, body: str) -> dict[str, object]:
        import httpx

        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        payload: dict[str, str] = {"to": to, "body": body}
        if self._sender:
            payload["from"] = self._sender
        # Every message task retries ConnectionError, TimeoutError and OSError,
        # and nothing else. httpx raises its own classes, and a non-2xx used
        # to be a RuntimeError, so a gateway that hiccuped lost the message
        # the first time (review SCALE-2). Passing trouble is said in the
        # tasks' terms; a refusal no retry will mend stays a RuntimeError.
        try:
            response = httpx.post(self._url, json=payload, headers=headers, timeout=self._timeout_s)
        except httpx.TimeoutException as exc:
            log.warning("sms.gateway_timeout", to=obscure(to))
            raise TimeoutError(f"SMS gateway timed out: {type(exc).__name__}") from exc
        except httpx.TransportError as exc:
            log.warning("sms.gateway_unreachable", to=obscure(to))
            raise ConnectionError(f"SMS gateway unreachable: {type(exc).__name__}") from exc
        if response.status_code == 429 or response.status_code >= 500:
            log.warning("sms.gateway_busy", to=obscure(to), status=response.status_code)
            raise GatewayBusy(f"SMS gateway answered {response.status_code}")
        if response.status_code >= 300:
            log.error("sms.gateway_refused", to=obscure(to), status=response.status_code)
            raise RuntimeError(f"SMS gateway answered {response.status_code}")

        message_id: object = None
        try:
            data = response.json()
            if isinstance(data, dict):
                message_id = data.get("id") or data.get("message_id")
        except ValueError:
            message_id = None
        log.info("sms.delivered", to=obscure(to), transport="http", message_id=message_id)
        return {"channel": "sms", "transport": "http", "delivered": True, "message_id": message_id}


#: What SNS takes for a phone number: a plus, then 8 to 15 digits, the first
#: not a zero (E.164).
_E164: Final = re.compile(r"\+[1-9][0-9]{7,14}")

#: How long a national number is where the default country code is India's.
_NATIONAL_DIGITS: Final = 10


def to_e164(stored: str, country_code: str) -> str:
    """A stored mobile as SNS takes it, or `ValueError`.

    A mobile is stored as it was typed, less its punctuation: with a plus if
    one was typed, and with no country code assumed if none was
    (`normalise_mobile`). SNS takes E.164 only. A number with a plus is taken
    as it is. One without loses its leading zeros - a trunk prefix (`098…`) or
    an international one (`0091…`) - and gets `country_code` in front, unless
    it carries it already: it starts with the code and is exactly ten digits
    longer, the length of India's national number. So `9198765432`, ten digits
    that happen to start with 91, is a national number and gets the code;
    `919876543210` has it.
    """
    number = normalise_mobile(stored)
    if not number.startswith("+"):
        digits = number.lstrip("0")
        carries_code = (
            digits.startswith(country_code) and len(digits) == len(country_code) + _NATIONAL_DIGITS
        )
        number = "+" + (digits if carries_code else country_code + digits)
    if not _E164.fullmatch(number):
        raise ValueError("not a phone number SNS can send to")
    return number


#: `ClientError` codes that say "not now" whatever the HTTP status: SNS's own
#: throttle, the account's, and a key service or endpoint that blinked.
_SNS_BUSY: Final = frozenset(
    {
        "Throttled",
        "ThrottledException",
        "Throttling",
        "ThrottlingException",
        "TooManyRequestsException",
        "RequestThrottled",
        "RequestTimeout",
        "RequestTimeoutException",
        "KMSThrottling",
        "InternalError",
        "InternalFailure",
        "ServiceUnavailable",
    }
)


@lru_cache(maxsize=4)
def _sns_client(region: str, timeout_s: float) -> Any:
    """One SNS client per process, made on the first text and kept.

    Made lazily, so building the transport - the API at startup, `deliver()`
    for every message - needs no credentials and opens nothing, and each
    Celery child makes its own after the fork rather than sharing a parent's
    sockets. botocore alone, not boto3: the workers publish and do nothing
    else, and boto3 would bring the S3 transfer manager with it.

    botocore tries once more itself; the task's backoff does the real
    retrying. The proxy is HTTPS_PROXY and NO_PROXY, which botocore reads.
    """
    import botocore.session
    from botocore.config import Config

    return botocore.session.get_session().create_client(
        "sns",
        region_name=region,
        config=Config(
            connect_timeout=timeout_s,
            read_timeout=timeout_s,
            retries={"mode": "standard", "total_max_attempts": 2},
            user_agent_extra="compass-cmp",
        ),
    )


class SnsSmsTransport:
    """Amazon SNS, publishing straight to the phone number (ADR 0043).

    No topic and no subscription: one `Publish` per text, as Transactional,
    the route SNS keeps for one-time codes. Credentials are the standard AWS
    chain of the worker's environment and the proxy is HTTPS_PROXY: neither
    is read here. "Delivered" means SNS accepted the text, as a 2xx does for
    the HTTP gateway; what the carrier did with it is in SNS's delivery logs
    in CloudWatch, not here.
    """

    def __init__(self, *, region: str, sender_id: str, country_code: str, timeout_s: float) -> None:
        self._region = region
        self._sender_id = sender_id
        self._country_code = country_code
        self._timeout_s = timeout_s

    def send(self, *, to: str, body: str) -> dict[str, object]:
        # botocore is imported here, like httpx above: a process that sends
        # through another transport never loads it.
        from botocore import exceptions as aws

        who = obscure(to)
        try:
            number = to_e164(to, self._country_code)
        except ValueError as exc:
            log.error("sms.gateway_refused", to=who, code="bad_number")
            raise RuntimeError("SNS cannot send to this number: not E.164") from exc

        attributes: dict[str, dict[str, str]] = {
            "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
        }
        if self._sender_id:
            attributes["AWS.SNS.SMS.SenderID"] = {
                "DataType": "String",
                "StringValue": self._sender_id,
            }
        # The HTTP transport's contract (review SCALE-2): passing trouble is
        # said in the tasks' terms, and a refusal no retry will mend stays a
        # RuntimeError. The mapping is needed, not tidiness: botocore's
        # connection errors are not OSError subclasses, so unmapped, a proxy
        # or endpoint outage would lose the sign-in code on the first try.
        # The order matters: the timeouts and the TLS failure are subclasses
        # of botocore's ConnectionError and HTTPClientError.
        try:
            response = _sns_client(self._region, self._timeout_s).publish(
                PhoneNumber=number, Message=body, MessageAttributes=attributes
            )
        except (aws.ConnectTimeoutError, aws.ReadTimeoutError) as exc:
            log.warning("sms.gateway_timeout", to=who)
            raise TimeoutError(f"SNS timed out: {type(exc).__name__}") from exc
        except aws.SSLError as exc:
            log.warning(
                "sms.gateway_tls_failed",
                to=who,
                hint=f"is the proxy inspecting sns.{self._region}.amazonaws.com?",
            )
            raise ConnectionError("SNS could not be reached: the TLS handshake failed") from exc
        except (aws.ConnectionError, aws.HTTPClientError) as exc:
            log.warning("sms.gateway_unreachable", to=who)
            raise ConnectionError(f"SNS unreachable: {type(exc).__name__}") from exc
        except aws.ClientError as exc:
            status = int(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") or 0)
            code = str(exc.response.get("Error", {}).get("Code") or "")
            if status == 429 or status >= 500 or code in _SNS_BUSY:
                log.warning("sms.gateway_busy", to=who, status=status, code=code)
                raise GatewayBusy(f"SNS answered {status} {code}") from exc
            # A bad number, a number that opted out, a key that may not
            # publish: SNS's words can quote the number, so only its code.
            log.error("sms.gateway_refused", to=who, status=status, code=code)
            raise RuntimeError(f"SNS refused the text: {status} {code}") from exc
        except (
            aws.NoCredentialsError,
            aws.PartialCredentialsError,
            aws.CredentialRetrievalError,
            aws.ProfileNotFound,
            aws.ConfigNotFound,
            aws.TokenRetrievalError,
            aws.SSOError,
        ) as exc:
            log.error(
                "sms.not_configured",
                reason=type(exc).__name__,
                hint="this process found no usable AWS credentials: check AWS_PROFILE and "
                "AWS_SHARED_CREDENTIALS_FILE in its environment",
            )
            raise RuntimeError(f"SNS has no credentials: {type(exc).__name__}") from exc
        except aws.BotoCoreError as exc:
            log.error("sms.gateway_refused", to=who, code=type(exc).__name__)
            raise RuntimeError(f"SNS could not send the text: {type(exc).__name__}") from exc

        message_id = response.get("MessageId")
        log.info("sms.delivered", to=who, transport="sns", message_id=message_id)
        return {"channel": "sms", "transport": "sns", "delivered": True, "message_id": message_id}


class NullSmsTransport:
    """Accepts and discards, keeping what it was given for assertions."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, body: str) -> dict[str, object]:
        self.sent.append({"to": to, "body": body})
        return {"channel": "sms", "transport": "null", "delivered": True}


def build_sms_transport() -> SmsTransport:
    """Console unless configured otherwise — the same reasoning as email.

    A gateway that starts texting real numbers because an environment variable
    was missing is a worse outcome than one that quietly writes to a file.
    """
    if settings.sms_transport == "null":
        return NullSmsTransport()
    if settings.sms_transport == "http":
        return HttpSmsTransport(
            url=settings.sms_http_url,
            token=settings.sms_http_token.get_secret_value(),
            sender=settings.sms_http_sender,
            timeout_s=settings.external_http_timeout_s,
        )
    if settings.sms_transport == "sns":
        return SnsSmsTransport(
            region=settings.sms_sns_region.strip(),
            sender_id=settings.sms_sns_sender_id,
            country_code=settings.sms_default_country_code,
            timeout_s=settings.external_http_timeout_s,
        )
    return ConsoleSmsTransport()
