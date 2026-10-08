"""Turning a junction into words and handing them to a transport.

The one way anything in this codebase sends a message is `deliver(Message.X,
to=..., **variables)`. It looks the junction up in the catalogue, applies the
office's replacement words if there are any, renders, picks the channel from
the shape of the contact, and hands the result to the email or SMS transport.
Free text never reaches a transport, which is what makes the console's list
of messages complete by construction.

Replacement words are read by a Celery worker, which is synchronous and has
no request. They come from a Redis mirror of the `message_template` table,
refreshed from the database when absent and cleared by the API on every
change; if neither is reachable the defaults are used and the failure is
logged, because a sign-in code must go out whatever else is wrong.

Copies (2026-10-08) work the same way: who the office copies each message to
is mirrored from `message_copy`, sealed, and opened here like the recipient.
Only a message the catalogue marks copyable is ever copied, whatever the
table holds; only one it marks attachable may carry the files a caller hands
in (docs/notifications/README.md).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.core.messages import Channel, Junction, Message, junction, render_text
from cmp.db.redis import K_CACHE
from cmp.db.redis import key as rkey

if TYPE_CHECKING:
    from cmp.infrastructure.email import Attachment

log = get_logger("cmp.messaging")

#: Where the worker reads the office's replacements from, and what the API
#: clears when one changes.
MIRROR_KEY: Final = rkey(K_CACHE, "message_templates")
MIRROR_TTL_S: Final = 300
#: Who each message is copied to, sealed - the mirror of `message_copy`.
COPIES_KEY: Final = rkey(K_CACHE, "message_copies")

Overrides = dict[str, dict[str, str | None]]

_redis_client: Any = None


def _redis() -> Any:
    global _redis_client
    if _redis_client is None:
        import redis

        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
    return _redis_client


def _read_overrides_from_db() -> Overrides:
    import psycopg

    try:
        with psycopg.connect(settings.dsn, connect_timeout=3) as conn:
            rows = conn.execute(
                "SELECT key, channel, subject, body FROM message_template"
            ).fetchall()
    except Exception as exc:
        log.error("messages.overrides_unavailable", error=str(exc))
        return {}
    return {f"{k}:{c}": {"subject": s, "body": b} for k, c, s, b in rows}


def load_overrides() -> Overrides:
    """The office's replacement words, from the mirror or the table."""
    try:
        raw = _redis().get(MIRROR_KEY)
        if raw is not None:
            return dict(json.loads(raw))
    except Exception as exc:
        log.warning("messages.mirror_unavailable", error=str(exc))
    overrides = _read_overrides_from_db()
    try:
        _redis().set(MIRROR_KEY, json.dumps(overrides), ex=MIRROR_TTL_S)
    except Exception as exc:
        log.warning("messages.mirror_not_written", error=str(exc))
    return overrides


def _read_copies_from_db() -> dict[str, list[str]]:
    import psycopg

    try:
        with psycopg.connect(settings.dsn, connect_timeout=3) as conn:
            rows = conn.execute("SELECT key, address FROM message_copy ORDER BY copy_id").fetchall()
    except Exception as exc:
        log.error("messages.copies_unavailable", error=str(exc))
        return {}
    out: dict[str, list[str]] = {}
    for k, address in rows:
        out.setdefault(str(k), []).append(str(address))
    return out


def load_copies() -> dict[str, list[str]]:
    """Who the office copies each message to, sealed: from the mirror or the table."""
    try:
        raw = _redis().get(COPIES_KEY)
        if raw is not None:
            return dict(json.loads(raw))
    except Exception as exc:
        log.warning("messages.mirror_unavailable", error=str(exc))
    copies = _read_copies_from_db()
    try:
        _redis().set(COPIES_KEY, json.dumps(copies), ex=MIRROR_TTL_S)
    except Exception as exc:
        log.warning("messages.mirror_not_written", error=str(exc))
    return copies


def common_variables() -> dict[str, str]:
    """Available to every template, filled from configuration."""
    return {
        "organisation": settings.organisation_name,
        "portal_url": settings.public_base_url.rstrip("/"),
        "console_url": settings.console_base_url.rstrip("/"),
    }


def resolve(
    key: Message | str, channel: Channel | str, overrides: Overrides | None = None
) -> tuple[str | None, str]:
    """The template in force: the office's words if set, else the default."""
    j = junction(key)
    ch = Channel(channel)
    subject, body = j.default(ch)
    stored = (overrides if overrides is not None else load_overrides()).get(
        f"{j.key.value}:{ch.value}"
    )
    if stored and stored.get("body"):
        return (stored.get("subject") if ch is Channel.EMAIL else None), str(stored["body"])
    return subject, body


def render(
    key: Message | str,
    channel: Channel | str,
    variables: dict[str, Any],
    *,
    overrides: Overrides | None = None,
) -> tuple[str | None, str]:
    subject, body = resolve(key, channel, overrides)
    values = {**common_variables(), **variables}
    return (render_text(subject, values) if subject else None), render_text(body, values)


def channel_for(contact: str) -> Channel:
    return Channel.EMAIL if "@" in contact else Channel.SMS


def deliver(
    key: Message,
    *,
    to: str,
    attachments: Sequence[Attachment] = (),
    **variables: Any,
) -> dict[str, Any]:
    """Render one junction for one contact and send it. Failure raises.

    A transport that swallowed an error and returned quietly would turn a
    retryable outage into silent loss, so nothing is caught here; the task's
    retry policy decides what happens next.

    By email, the copies the office set for this message go with it, if the
    catalogue lets it be copied; `attachments` go only on a message the
    catalogue lets carry files. By SMS, neither: a text has no copy and no file.
    """
    # Whatever a caller hands in - a name for the greeting, the contact a ticket
    # is addressed to - may be sealed at rest. It is opened here, once, at the
    # one point every message passes through, rather than at every call site
    # that might have read it from a row.
    from cmp.infrastructure.dkms import unseal_values_sync, unseal_variables_sync
    from cmp.infrastructure.dkms.client import DkmsUnavailable, SealedValueUnreadable
    from cmp.infrastructure.dkms.fields import PREFIX

    try:
        variables = unseal_variables_sync(variables)
        if to.startswith(PREFIX):
            to = unseal_values_sync([to])[0]
    except (DkmsUnavailable, SealedValueUnreadable) as exc:
        # The one failure that is invisible from the outside: the request that
        # asked for this message answered "a code has been sent", because it
        # had queued one. It cannot be sent, because the address it goes to is
        # sealed and cannot be opened. Said plainly, once, with the service
        # named and no value quoted. An outage (`DkmsUnavailable`) is then
        # retried by the task; a value no retry will open is not.
        log.error(
            "message.not_sent",
            message=str(getattr(key, "value", key)),
            reason="the key service could not open the recipient",
            retried=isinstance(exc, DkmsUnavailable),
            error=str(exc),
        )
        raise

    if to.startswith(PREFIX):
        # Belt to the brace above. Nothing should reach here sealed, and if
        # something does, the next line would read it as a number - there is
        # no `@` in ciphertext - and refuse the message for the wrong reason.
        # This says the real one.
        raise SealedValueUnreadable(
            f"the recipient of '{getattr(key, 'value', key)}' is still sealed after "
            "opening, so there is nothing to address it to. Check DKMS_ENABLED and "
            "DKMS_URL in this process's environment."
        )

    j: Junction = junction(key)
    ch = channel_for(to)
    if ch not in j.channels:
        raise ValueError(f"'{j.key.value}' is not sent by {ch.value}; contact is {to[:3]}…")

    if attachments and not j.attachable:
        raise ValueError(f"'{j.key.value}' does not carry files")

    subject, body = render(key, ch, variables)
    if settings.email_redirect_to:
        # Test mode (EMAIL_REDIRECT_TO): nobody real is written to.
        result = _redirected(j, ch, to=to, subject=subject, body=body, attachments=attachments)
    elif ch is Channel.SMS:
        from cmp.infrastructure.sms import build_sms_transport

        result = dict(build_sms_transport().send(to=to, body=body))
    else:
        from cmp.infrastructure.email import build_email_transport

        assert subject is not None
        result = dict(
            build_email_transport().send(
                to=to, subject=subject, body=body, cc=_copies(j, to), attachments=attachments
            )
        )
    result["message"] = j.key.value
    return result


def _copies(j: Junction, to: str) -> list[str]:
    """Who an email is copied to: nobody, unless the catalogue lets it be
    copied; then the office's copies, then the deployment's own
    (EMAIL_CC_ADDRESSES), each once and never the recipient."""
    if not j.copyable:
        return []
    from cmp.infrastructure.dkms import unseal_values_sync
    from cmp.infrastructure.dkms.client import DkmsUnavailable, SealedValueUnreadable

    cc: list[str] = []
    sealed = load_copies().get(j.key.value, [])
    if sealed:
        try:
            cc = [c for c in unseal_values_sync(sealed) if c and c != to]
        except (DkmsUnavailable, SealedValueUnreadable) as exc:
            log.error(
                "message.not_sent",
                message=j.key.value,
                reason="the key service could not open a copy address",
                retried=isinstance(exc, DkmsUnavailable),
                error=str(exc),
            )
            raise
    for address in settings.email_cc_addresses:
        if address != to.lower() and address not in cc:
            cc.append(address)
    return cc


def _redirected(
    j: Junction,
    ch: Channel,
    *,
    to: str,
    subject: str | None,
    body: str,
    attachments: Sequence[Attachment],
) -> dict[str, Any]:
    """Test mode (EMAIL_REDIRECT_TO, refused in production): every message -
    every email and every text - goes only to the configured addresses, by
    email, and says at its top whom it was for. The recipient and anybody it
    would have been copied to are written to by nobody."""
    from cmp.infrastructure.email import build_email_transport

    inbox = list(settings.email_redirect_to)
    if ch is Channel.SMS:
        subject = f"[TEST] Text message for {to}: {j.title}"
        note = f"This text message was for {to}. It would have read:"
        files: Sequence[Attachment] = ()
    else:
        copies = _copies(j, to)
        subject = f"[TEST] {subject}"
        note = f"This email was for {to}" + (f", copied to {', '.join(copies)}." if copies else ".")
        files = attachments
    body = (
        "TEST MODE - this message was redirected by EMAIL_REDIRECT_TO. "
        f"{note}\n\n{'-' * 60}\n\n{body}"
    )
    result = dict(
        build_email_transport().send(
            to=inbox[0], subject=subject, body=body, cc=inbox[1:], attachments=files
        )
    )
    result["redirected"] = True
    log.info("message.redirected", message=j.key.value, channel=ch.value)
    return result


__all__ = [
    "COPIES_KEY",
    "MIRROR_KEY",
    "Overrides",
    "channel_for",
    "common_variables",
    "deliver",
    "load_copies",
    "load_overrides",
    "render",
    "resolve",
]
