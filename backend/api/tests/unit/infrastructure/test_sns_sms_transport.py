"""Texts through Amazon SNS (ADR 0043).

One `Publish` per text, straight to the phone number, as Transactional. No
network here: botocore's own `Stubber` answers for SNS, and it also checks
each request against SNS's API model, so a parameter SNS would refuse is
refused here.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import botocore.session
import pytest
from botocore import exceptions as aws
from botocore.stub import Stubber
from structlog.testing import capture_logs

from cmp.core.config import settings
from cmp.infrastructure.sms import SnsSmsTransport, build_sms_transport, transport
from cmp.tasks.authentication.otp import RETRY_KW as CODE_RETRY
from cmp.tasks.notifications.breach import RETRYABLE as BREACH_RETRY

CODE = "482913"
BODY = f"{CODE} is your sign-in code."
TRANSACTIONAL = {"AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}}


def _sns(sender_id: str = "") -> SnsSmsTransport:
    return SnsSmsTransport(region="ap-south-1", sender_id=sender_id, country_code="91", timeout_s=1)


def _retried(exc: BaseException) -> bool:
    return isinstance(exc, tuple(CODE_RETRY["autoretry_for"])) and isinstance(exc, BREACH_RETRY)


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[Stubber]:
    """A real SNS client with made-up credentials, answered by the Stubber."""
    client = botocore.session.get_session().create_client(
        "sns",
        region_name="ap-south-1",
        aws_access_key_id="AKIAEXAMPLE",
        aws_secret_access_key="not-a-secret",
    )
    monkeypatch.setattr(transport, "_sns_client", lambda *_: client)
    with Stubber(client) as stubber:
        yield stubber


class TestATextIsPublishedToThePhone:
    def test_it_goes_as_transactional_and_the_message_id_comes_back(self, stub: Stubber) -> None:
        stub.add_response(
            "publish",
            {"MessageId": "m-1"},
            {
                "PhoneNumber": "+919876543210",
                "Message": BODY,
                "MessageAttributes": TRANSACTIONAL,
            },
        )
        with capture_logs() as logs:
            result = _sns().send(to="9876543210", body=BODY)
        assert result == {
            "channel": "sms",
            "transport": "sns",
            "delivered": True,
            "message_id": "m-1",
        }
        [line] = logs
        assert line["event"] == "sms.delivered" and line["message_id"] == "m-1"
        assert line["to"] == "***210" and line["transport"] == "sns"
        stub.assert_no_pending_responses()

    def test_a_sender_id_goes_only_when_one_is_set(self, stub: Stubber) -> None:
        stub.add_response(
            "publish",
            {"MessageId": "m-2"},
            {
                "PhoneNumber": "+919876543210",
                "Message": BODY,
                "MessageAttributes": {
                    **TRANSACTIONAL,
                    "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": "COMPASS"},
                },
            },
        )
        assert _sns("COMPASS").send(to="+91 98765 43210", body=BODY)["delivered"] is True
        stub.assert_no_pending_responses()


class TestAStoredNumberBecomesE164:
    @pytest.mark.parametrize(
        ("stored", "sent"),
        [
            ("9876543210", "+919876543210"),
            ("09876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
            ("00919876543210", "+919876543210"),
            ("+91 98765 43210", "+919876543210"),
            ("(+91) 98765-43210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            # Ten digits that happen to start with 91: a national number.
            ("9198765432", "+919198765432"),
            # A plus is taken at its word, whatever the default.
            ("+12065550101", "+12065550101"),
        ],
    )
    def test_it_is_sent_as(self, stored: str, sent: str) -> None:
        assert transport.to_e164(stored, "91") == sent

    def test_another_default_country_code(self) -> None:
        assert transport.to_e164("2065550101", "1") == "+12065550101"
        assert transport.to_e164("12065550101", "1") == "+12065550101"

    @pytest.mark.parametrize("stored", ["12345", "", "+0123456789", "+9198765432109876543"])
    def test_what_is_no_phone_number_is_refused(self, stored: str) -> None:
        with pytest.raises(ValueError):
            transport.to_e164(stored, "91")

    @pytest.mark.parametrize(
        ("stored", "sent"),
        [
            # Review SEC-5: `00` is the international prefix. A UK number
            # (Ofcom's drama range) went to India as +9144...
            ("00447700900123", "+447700900123"),
            ("0044 7700 900123", "+447700900123"),
            ("+447700900123", "+447700900123"),
        ],
    )
    def test_an_explicit_foreign_code_is_kept_whatever_the_default(
        self, stored: str, sent: str
    ) -> None:
        assert transport.to_e164(stored, "91") == sent

    @pytest.mark.parametrize(
        ("stored", "default"),
        [
            # A national number of the wrong length is refused, never sent to
            # some other number: nine, eleven and thirteen digits for India...
            ("987654321", "91"),
            ("98765432101", "91"),
            ("9198765432101", "91"),
            # ...and a seven-digit local number where the default is 1.
            ("5550101", "1"),
        ],
    )
    def test_a_national_number_of_the_wrong_length_is_refused(
        self, stored: str, default: str
    ) -> None:
        with pytest.raises(ValueError):
            transport.to_e164(stored, default)

    def test_a_refused_length_never_reaches_publish(self, stub: Stubber) -> None:
        with pytest.raises(RuntimeError):
            _sns().send(to="98765432101", body=BODY)
        stub.assert_no_pending_responses()

    def test_a_refused_number_publishes_nothing_and_is_not_retried(self, stub: Stubber) -> None:
        with capture_logs() as logs, pytest.raises(RuntimeError) as raised:
            _sns().send(to="12345", body=BODY)
        assert not _retried(raised.value)
        assert [(line["event"], line["code"]) for line in logs] == [
            ("sms.gateway_refused", "bad_number")
        ]
        # The Stubber had no answer queued: a publish would have raised its
        # own error, not this one.
        stub.assert_no_pending_responses()


def _raising(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    class Client:
        def publish(self, **_: Any) -> dict[str, Any]:
            raise exc

    monkeypatch.setattr(transport, "_sns_client", lambda *_: Client())


URL = "https://sns.ap-south-1.amazonaws.com/"

PASSING = [
    (aws.ConnectTimeoutError(endpoint_url=URL), TimeoutError, "sms.gateway_timeout"),
    (aws.ReadTimeoutError(endpoint_url=URL), TimeoutError, "sms.gateway_timeout"),
    (
        aws.SSLError(endpoint_url=URL, error="bad certificate"),
        ConnectionError,
        "sms.gateway_tls_failed",
    ),
    (aws.EndpointConnectionError(endpoint_url=URL), ConnectionError, "sms.gateway_unreachable"),
    (
        aws.ProxyConnectionError(proxy_url="http://proxy:8080"),
        ConnectionError,
        "sms.gateway_unreachable",
    ),
    (aws.ConnectionClosedError(endpoint_url=URL), ConnectionError, "sms.gateway_unreachable"),
    (aws.HTTPClientError(error="something else"), ConnectionError, "sms.gateway_unreachable"),
]

NOT_CONFIGURED = [
    aws.NoCredentialsError(),
    aws.PartialCredentialsError(provider="env", cred_var="AWS_SECRET_ACCESS_KEY"),
    aws.ProfileNotFound(profile="cmp-sms"),
    aws.ConfigNotFound(path="/etc/cmp/aws-credentials"),
]


class TestPassingTroubleIsRetriedAndARefusalIsNot:
    """The HTTP transport's contract (review SCALE-2), in SNS's exceptions."""

    @pytest.mark.parametrize(
        ("raised_by_botocore", "becomes", "event"),
        PASSING,
        ids=[type(e).__name__ for e, _, _ in PASSING],
    )
    def test_the_network_failing_is_retried(
        self,
        monkeypatch: pytest.MonkeyPatch,
        raised_by_botocore: Exception,
        becomes: type[Exception],
        event: str,
    ) -> None:
        _raising(monkeypatch, raised_by_botocore)
        with capture_logs() as logs, pytest.raises(becomes) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert _retried(raised.value), type(raised.value)
        assert [line["event"] for line in logs] == [event]

    @pytest.mark.parametrize(
        ("code", "status"),
        [
            ("Throttled", 429),
            ("ThrottlingException", 400),
            ("Throttling", 400),
            ("KMSThrottling", 400),
            ("InternalError", 500),
            ("ServiceUnavailable", 503),
            ("SomethingNew", 502),
        ],
    )
    def test_sns_saying_not_now_is_retried(self, stub: Stubber, code: str, status: int) -> None:
        stub.add_client_error("publish", service_error_code=code, http_status_code=status)
        with capture_logs() as logs, pytest.raises(transport.GatewayBusy) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert _retried(raised.value)
        [line] = logs
        assert (line["event"], line["code"], line["status"]) == ("sms.gateway_busy", code, status)

    @pytest.mark.parametrize(
        ("code", "status"),
        [
            ("InvalidParameter", 400),
            ("ParameterValueInvalid", 400),
            ("AuthorizationError", 403),
            ("InvalidClientTokenId", 403),
            ("SignatureDoesNotMatch", 403),
            ("OptedOut", 400),
        ],
    )
    def test_sns_saying_no_is_not_retried(self, stub: Stubber, code: str, status: int) -> None:
        stub.add_client_error(
            "publish",
            service_error_code=code,
            service_message="Invalid parameter: PhoneNumber +919876543210",
            http_status_code=status,
        )
        with capture_logs() as logs, pytest.raises(RuntimeError) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert not _retried(raised.value), code
        [line] = logs
        assert (line["event"], line["code"], line["status"]) == (
            "sms.gateway_refused",
            code,
            status,
        )
        # SNS's own words can quote the number: neither the log nor the error
        # carries them.
        assert "9876543210" not in str(line) and "9876543210" not in str(raised.value)

    @pytest.mark.parametrize("exc", NOT_CONFIGURED, ids=[type(e).__name__ for e in NOT_CONFIGURED])
    def test_no_credentials_is_said_once_and_not_retried(
        self, monkeypatch: pytest.MonkeyPatch, exc: Exception
    ) -> None:
        _raising(monkeypatch, exc)
        with capture_logs() as logs, pytest.raises(RuntimeError) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert not _retried(raised.value)
        [line] = logs
        assert line["event"] == "sms.not_configured" and line["log_level"] == "error"
        assert "AWS_PROFILE" in line["hint"] and "AWS_SHARED_CREDENTIALS_FILE" in line["hint"]
        # It names the variables, never what a variable held.
        assert "not-a-secret" not in str(line) and "cmp-sms" not in str(line)

    def test_anything_else_botocore_raises_is_a_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _raising(monkeypatch, aws.ParamValidationError(report="Message too long"))
        with capture_logs() as logs, pytest.raises(RuntimeError) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert not _retried(raised.value)
        assert [(line["event"], line["code"]) for line in logs] == [
            ("sms.gateway_refused", "ParamValidationError")
        ]


class TestTheCodeIsInNoLogLine:
    @pytest.mark.parametrize(
        "outcome",
        ["delivered", "busy", "refused", "unreachable", "no-credentials", "bad-number"],
    )
    def test_neither_the_body_nor_the_whole_number(
        self, monkeypatch: pytest.MonkeyPatch, stub: Stubber, outcome: str
    ) -> None:
        to = "9876543210"
        if outcome == "delivered":
            stub.add_response("publish", {"MessageId": "m-3"})
        elif outcome == "busy":
            stub.add_client_error("publish", "Throttled", BODY, 429)
        elif outcome == "refused":
            stub.add_client_error("publish", "InvalidParameter", BODY, 400)
        elif outcome == "unreachable":
            _raising(monkeypatch, aws.EndpointConnectionError(endpoint_url=URL))
        elif outcome == "no-credentials":
            _raising(monkeypatch, aws.NoCredentialsError())
        else:
            to = "12345"
        with capture_logs() as logs:
            try:
                _sns().send(to=to, body=BODY)
            except (RuntimeError, ConnectionError, TimeoutError) as exc:
                assert CODE not in str(exc) and to not in str(exc)
        assert logs
        assert CODE not in str(logs) and to not in str(logs)


class TestTheClientIsMadeOnceAndLate:
    @pytest.fixture
    def made(self, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
        calls: list[dict[str, Any]] = []

        class Client:
            def publish(self, **_: Any) -> dict[str, Any]:
                return {"MessageId": "m"}

        class Session:
            def create_client(self, service: str, **kwargs: Any) -> Client:
                calls.append({"service": service, **kwargs})
                return Client()

        monkeypatch.setattr(botocore.session, "get_session", lambda: Session())
        transport._sns_client.cache_clear()
        yield calls
        transport._sns_client.cache_clear()

    def test_building_the_transport_makes_no_client(
        self, monkeypatch: pytest.MonkeyPatch, made: list[dict[str, Any]]
    ) -> None:
        monkeypatch.setattr(settings, "sms_transport", "sns")
        built = build_sms_transport()
        assert isinstance(built, SnsSmsTransport)
        assert made == []

    def test_two_texts_through_two_transports_make_one_client(
        self, monkeypatch: pytest.MonkeyPatch, made: list[dict[str, Any]]
    ) -> None:
        # `deliver()` builds a transport per message.
        monkeypatch.setattr(settings, "sms_transport", "sns")
        build_sms_transport().send(to="9876543210", body=BODY)
        build_sms_transport().send(to="9876543211", body=BODY)
        [call] = made
        assert call["service"] == "sns" and call["region_name"] == settings.sms_sns_region
        config = call["config"]
        assert config.connect_timeout == settings.external_http_timeout_s
        assert config.read_timeout == settings.external_http_timeout_s
        # One try more by botocore; the task's backoff does the rest.
        assert config.retries == {"mode": "standard", "total_max_attempts": 2}

    def test_the_other_transports_are_still_built_for_their_names(
        self, monkeypatch: pytest.MonkeyPatch, made: list[dict[str, Any]]
    ) -> None:
        for name, kind in (
            ("console", transport.ConsoleSmsTransport),
            ("http", transport.HttpSmsTransport),
            ("null", transport.NullSmsTransport),
        ):
            monkeypatch.setattr(settings, "sms_transport", name)
            assert isinstance(build_sms_transport(), kind)


class TestCredentialsThatBlinkAreRetried:
    """Review SCALE-6: a credential process or the metadata endpoint that did
    not answer this time is passing trouble, retried like an endpoint outage;
    configuration that is plainly missing stays terminal (above)."""

    @pytest.mark.parametrize(
        "exc",
        [
            aws.CredentialRetrievalError(provider="custom-process", error_msg="exit 1"),
            aws.MetadataRetrievalError(error_msg="timed out"),
        ],
        ids=["credential-process", "metadata"],
    )
    def test_it_is_retried_and_the_next_try_sends(
        self, monkeypatch: pytest.MonkeyPatch, exc: Exception
    ) -> None:
        tries: list[int] = []

        class Client:
            def publish(self, **_: Any) -> dict[str, Any]:
                tries.append(1)
                if len(tries) == 1:
                    raise exc
                return {"MessageId": "m-after"}

        monkeypatch.setattr(transport, "_sns_client", lambda *_: Client())
        with capture_logs() as logs, pytest.raises(ConnectionError) as raised:
            _sns().send(to="9876543210", body=BODY)
        assert _retried(raised.value)
        assert [line["event"] for line in logs] == ["sms.credentials_unavailable"]
        assert _sns().send(to="9876543210", body=BODY)["message_id"] == "m-after"


class TestTheProviderErrorIsNotChained:
    """Review SEC-7: a worker's traceback renders the exception's cause, and
    SNS's own words can quote the number. Every error the transport raises
    stands alone."""

    @pytest.mark.parametrize("outcome", ["refused", "busy", "unreachable", "credentials"])
    def test_no_cause_carries_the_providers_words(
        self, monkeypatch: pytest.MonkeyPatch, stub: Stubber, outcome: str
    ) -> None:
        import traceback

        quoted = "Invalid parameter: PhoneNumber +919876543210"
        if outcome == "refused":
            stub.add_client_error("publish", "InvalidParameter", quoted, 400)
        elif outcome == "busy":
            stub.add_client_error("publish", "Throttled", quoted, 429)
        elif outcome == "unreachable":
            _raising(monkeypatch, aws.EndpointConnectionError(endpoint_url=URL))
        else:
            _raising(monkeypatch, aws.CredentialRetrievalError(provider="p", error_msg=quoted))
        with pytest.raises(Exception) as raised:
            _sns().send(to="9876543210", body=BODY)
        # The chain as a worker log renders it, less the frames (which hold
        # this test's own source).
        err = raised.value
        rendered = "".join(traceback.format_exception(type(err), err, None))
        assert raised.value.__cause__ is None
        assert "9876543210" not in rendered and CODE not in rendered


def test_botocore_never_logs_a_request_at_debug() -> None:
    """Review SEC-7: botocore logs request parameters at DEBUG."""
    import logging

    from cmp.core.logging import configure_logging

    configure_logging()
    assert logging.getLogger("botocore").getEffectiveLevel() >= logging.WARNING
