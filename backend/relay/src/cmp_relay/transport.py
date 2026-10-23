"""The SQS and S3 calls both sides make, in one place.

Messages: the body is the sealed envelope, base64 (SQS bodies are text). Two
message attributes travel in the clear - `rid`, the request id, which the
bridge needs to find the key a reply was sealed under, and `kind` - and nothing
else; both are random or fixed values that say nothing about anybody.

Each receive also asks SQS for three of its own attributes, all on AWS's
clock: when the message was sent, when it was first received, and how many
times it has been received. The collector measures deadlines against AWS's
clock with them; the bridge uses the count to stop passing round a reply that
no bridge is waiting for.

Bodies too large for a message: a sealed object at `req/<rid>` or `res/<rid>`.
The reader deletes it as soon as it has read it, reads no more than its limit
allows whatever the object's size, and checks it against its hash; a lifecycle
rule on the bucket removes anything a crash left behind within a day
(deploy/cloudformation.yaml).

Every client is built with explicit timeouts and the SDK's standard retry
mode: a proxy or ISP failover must turn into a quick reconnect, not a hang.
Against the local emulator, S3 uses path-style addresses because a bucket name
cannot be a subdomain of 127.0.0.1; on AWS it is virtual-hosted, so the egress
allow-list names `<bucket>.s3.<region>.amazonaws.com` exactly.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config

from cmp_relay.config import Common

#: SQS long-poll wait. 20 seconds is the service's maximum.
LONG_POLL_S = 20

#: The SQS attributes asked for on every receive (`Received` carries them).
SYSTEM_ATTRIBUTES = ("SentTimestamp", "ApproximateFirstReceiveTimestamp", "ApproximateReceiveCount")

#: How much of a stored body is read at a time.
_READ_CHUNK = 1024 * 1024


def build_clients(common: Common, pool: int = 16) -> tuple[Any, Any]:
    """(sqs, s3) clients for this deployment."""
    config = Config(
        region_name=common.region,
        retries={"mode": "standard", "max_attempts": 3},
        connect_timeout=5,
        read_timeout=LONG_POLL_S + 10,
        max_pool_connections=pool,
        s3={"addressing_style": "path" if common.endpoint_url else "virtual"},
    )
    session = boto3.session.Session()
    sqs = session.client("sqs", endpoint_url=common.endpoint_url, config=config)
    s3 = session.client("s3", endpoint_url=common.endpoint_url, config=config)
    return sqs, s3


@dataclass(frozen=True)
class Received:
    """One message off a queue, with what SQS says about it: when it was sent
    and first received (milliseconds, AWS's clock) and how many times it has
    been received, this time included. Each is None when SQS did not say."""

    receipt: str
    request_id: str
    blob: bytes
    sent_ms: int | None = None
    first_receive_ms: int | None = None
    receive_count: int | None = None


def _number(attributes: dict[str, Any], name: str) -> int | None:
    try:
        return int(attributes[name])
    except (KeyError, TypeError, ValueError):
        return None


def send(sqs: Any, queue_url: str, request_id: str, kind: str, blob: bytes) -> None:
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=base64.b64encode(blob).decode(),
        MessageAttributes={
            "rid": {"DataType": "String", "StringValue": request_id},
            "kind": {"DataType": "String", "StringValue": kind},
        },
    )


def receive(
    sqs: Any, queue_url: str, max_messages: int = 1, wait_s: int | None = None
) -> list[Received]:
    """Long-poll a queue for up to `wait_s` seconds (default `LONG_POLL_S`, read at
    call time). Messages that are not ours (no request id, not base64) are
    deleted and skipped: nothing else should be writing here."""
    answer = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=LONG_POLL_S if wait_s is None else wait_s,
        MessageAttributeNames=["rid", "kind"],
        MessageSystemAttributeNames=list(SYSTEM_ATTRIBUTES),
    )
    out: list[Received] = []
    for message in answer.get("Messages", []):
        receipt = message["ReceiptHandle"]
        rid = message.get("MessageAttributes", {}).get("rid", {}).get("StringValue")
        try:
            blob = base64.b64decode(message.get("Body", ""), validate=True)
        except (binascii.Error, ValueError):
            blob = b""
        if not rid or not blob:
            delete(sqs, queue_url, receipt)
            continue
        attributes = message.get("Attributes", {})
        out.append(
            Received(
                receipt=receipt,
                request_id=rid,
                blob=blob,
                sent_ms=_number(attributes, "SentTimestamp"),
                first_receive_ms=_number(attributes, "ApproximateFirstReceiveTimestamp"),
                receive_count=_number(attributes, "ApproximateReceiveCount"),
            )
        )
    return out


def delete(sqs: Any, queue_url: str, receipt: str) -> None:
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)


def release(sqs: Any, queue_url: str, receipt: str) -> None:
    """Make a received message visible again at once, for another reader."""
    sqs.change_message_visibility(QueueUrl=queue_url, ReceiptHandle=receipt, VisibilityTimeout=0)


def body_key(direction: str, request_id: str) -> str:
    """`req/<id>` for a request body, `res/<id>` for a reply body."""
    if direction not in ("req", "res"):
        raise ValueError(direction)
    return f"{direction}/{request_id}"


def put_blob(s3: Any, bucket: str, key: str, blob: bytes) -> str:
    """Store a sealed body. Returns its SHA-256, which travels in the envelope."""
    s3.put_object(Bucket=bucket, Key=key, Body=blob)
    return hashlib.sha256(blob).hexdigest()


def _read_at_most(stream: Any, limit: int) -> bytes:
    """Up to `limit` bytes of a stream, whatever more it holds."""
    chunks: list[bytes] = []
    size = 0
    while size < limit:
        chunk: bytes = stream.read(min(_READ_CHUNK, limit - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks)


def take_blob(
    s3: Any,
    bucket: str,
    key: str,
    sha256: str,
    size_limit: int,
    expected_size: int | None = None,
) -> bytes:
    """Read a sealed body, delete it, and check it. Raises ValueError on a body
    larger than `size_limit`, of another size than `expected_size` (when
    given), or not matching its hash.

    One GET, read to at most `size_limit + 1` bytes: the object can be replaced
    between any check of its size and the read, so the read itself is bounded.
    The stream is closed rather than drained, so what is left unread is never
    fetched."""
    response = s3.get_object(Bucket=bucket, Key=key)
    stream = response["Body"]
    try:
        declared = int(response.get("ContentLength") or 0)
        blob = b"" if declared > size_limit else _read_at_most(stream, size_limit + 1)
    finally:
        stream.close()
        s3.delete_object(Bucket=bucket, Key=key)
    if declared > size_limit or len(blob) > size_limit:
        raise ValueError("stored body is larger than allowed")
    if expected_size is not None and len(blob) != expected_size:
        raise ValueError("stored body is not the size its envelope declares")
    if hashlib.sha256(blob).hexdigest() != sha256:
        raise ValueError("stored body does not match its hash")
    return blob
