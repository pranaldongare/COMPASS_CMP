"""Make the queues and the bucket on a local emulator, and print the settings.

    python -m cmp_relay.provision --endpoint-url http://127.0.0.1:5000 \\
        [--replies 2] [--prefix cmp-relay-local] [--region ap-south-1] \\
        [--keys-dir keys] [--env-dir var]

For development only. It refuses to run without `--endpoint-url`: on AWS the
same resources come from `deploy/cloudformation.yaml`, with the roles, the
trust anchor and the alarms that this does not make.

What it makes, with the attributes the CloudFormation stack sets:

* `<prefix>-requests` - the request queue. Visibility 180 s, so a request is
  never handed to a second collector while the first could still be working on
  it (longer than any deadline: uploads get 50 s by default, at most 600 s);
  retention 60 s, the service minimum, so a
  request nobody collected is gone soon after the browser gave up on it; long
  polling 20 s; messages up to 1 MiB; SSE-SQS.
* `<prefix>-replies-a`, `-b`, ... - one reply queue per bridge instance.
  Retention 60 s, visibility 30 s.
* `<prefix>-bodies` - the bucket for bodies too large for a message, with a
  lifecycle rule that expires `req/` and `res/` after a day.

It is idempotent: run it again and it changes nothing that is already right.
An emulator that ignores an attribute is tolerated and named in a warning.

It prints the environment lines for each bridge and for the collector, and with
`--env-dir` also writes them as `bridge-a.env`, ..., `collector.env` (mode 0600),
ready for `set -a; . var/collector.env; set +a`. Run `keys generate` first, so
the bridges' lines carry the collector's public key.
"""

from __future__ import annotations

import argparse
import os
import string
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

REQUEST_QUEUE_ATTRIBUTES: Mapping[str, str] = {
    "VisibilityTimeout": "180",
    "MessageRetentionPeriod": "60",
    "ReceiveMessageWaitTimeSeconds": "20",
    "MaximumMessageSize": "1048576",
    "SqsManagedSseEnabled": "true",
}

REPLY_QUEUE_ATTRIBUTES: Mapping[str, str] = {
    "VisibilityTimeout": "30",
    "MessageRetentionPeriod": "60",
    "ReceiveMessageWaitTimeSeconds": "20",
    "MaximumMessageSize": "1048576",
    "SqsManagedSseEnabled": "true",
}

#: Attributes an emulator may not know. A queue is still usable without them.
_OPTIONAL_ATTRIBUTES = frozenset({"SqsManagedSseEnabled", "MaximumMessageSize"})

LIFECYCLE: Mapping[str, Any] = {
    "Rules": [
        {
            "ID": f"expire-{prefix.rstrip('/')}",
            "Filter": {"Prefix": prefix},
            "Status": "Enabled",
            "Expiration": {"Days": 1},
            "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
        }
        for prefix in ("req/", "res/")
    ]
}

_MAX_REPLIES = 8


class ProvisionError(Exception):
    """A refusal or a failure the user can act on."""


@dataclass(frozen=True)
class Provisioned:
    request_queue_url: str
    reply_queue_urls: tuple[str, ...]
    bucket: str
    warnings: tuple[str, ...]


def _warn(warnings: list[str], text: str) -> None:
    warnings.append(text)
    print(f"warning: {text}", file=sys.stderr)


def _ensure_queue(sqs: Any, name: str, attributes: Mapping[str, str], warnings: list[str]) -> str:
    """Create the queue, or bring an existing one's attributes into line."""
    try:
        url: str = sqs.get_queue_url(QueueName=name)["QueueUrl"]
    except sqs.exceptions.QueueDoesNotExist:
        url = ""
    wanted = dict(attributes)
    if url:
        try:
            sqs.set_queue_attributes(QueueUrl=url, Attributes=wanted)
        except ClientError:
            core = {k: v for k, v in wanted.items() if k not in _OPTIONAL_ATTRIBUTES}
            sqs.set_queue_attributes(QueueUrl=url, Attributes=core)
    else:
        try:
            url = sqs.create_queue(QueueName=name, Attributes=wanted)["QueueUrl"]
        except ClientError:
            core = {k: v for k, v in wanted.items() if k not in _OPTIONAL_ATTRIBUTES}
            url = sqs.create_queue(QueueName=name, Attributes=core)["QueueUrl"]

    got = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["All"]).get("Attributes", {})
    ignored = sorted(k for k, v in wanted.items() if str(got.get(k, "")).lower() != v.lower())
    if ignored:
        _warn(warnings, f"the emulator did not keep {', '.join(ignored)} on {name}")
    return url


def _ensure_bucket(s3: Any, bucket: str, region: str, warnings: list[str]) -> None:
    """Create the bucket if needed, then set what the stack sets on it."""
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        create: dict[str, Any] = {"Bucket": bucket}
        if region != "us-east-1":
            create["CreateBucketConfiguration"] = {"LocationConstraint": region}
        try:
            s3.create_bucket(**create)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
                raise
    s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=LIFECYCLE)
    extras: tuple[tuple[str, dict[str, Any]], ...] = (
        (
            "put_public_access_block",
            {
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                }
            },
        ),
        (
            "put_bucket_encryption",
            {
                "ServerSideEncryptionConfiguration": {
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                }
            },
        ),
    )
    for call, kwargs in extras:
        try:
            getattr(s3, call)(Bucket=bucket, **kwargs)
        except (ClientError, BotoCoreError):
            _warn(warnings, f"the emulator refused {call} on {bucket}; carrying on")


def _clients(endpoint_url: str, region: str) -> tuple[Any, Any]:
    # Any credentials do for an emulator. Dummy ones are passed explicitly so a
    # real profile on this machine is never picked up and sent to it.
    session = boto3.session.Session(
        aws_access_key_id="testing",
        aws_secret_access_key="testing",  # noqa: S106 - an emulator's dummy pair
        region_name=region,
    )
    config = Config(
        connect_timeout=5,
        read_timeout=30,
        retries={"mode": "standard", "max_attempts": 2},
        s3={"addressing_style": "path"},
    )
    return (
        session.client("sqs", endpoint_url=endpoint_url, config=config),
        session.client("s3", endpoint_url=endpoint_url, config=config),
    )


def provision(endpoint_url: str, *, prefix: str, replies: int, region: str) -> Provisioned:
    """Make (or check) every resource. Returns their names and URLs."""
    if not endpoint_url:
        raise ProvisionError(
            "provision is for a local emulator only: pass --endpoint-url."
            " On AWS, deploy deploy/cloudformation.yaml instead."
        )
    if not 1 <= replies <= _MAX_REPLIES:
        raise ProvisionError(f"--replies must be between 1 and {_MAX_REPLIES}")
    sqs, s3 = _clients(endpoint_url, region)
    warnings: list[str] = []
    try:
        request_url = _ensure_queue(sqs, f"{prefix}-requests", REQUEST_QUEUE_ATTRIBUTES, warnings)
        reply_urls = tuple(
            _ensure_queue(sqs, f"{prefix}-replies-{suffix}", REPLY_QUEUE_ATTRIBUTES, warnings)
            for suffix in string.ascii_lowercase[:replies]
        )
        bucket = f"{prefix}-bodies"
        _ensure_bucket(s3, bucket, region, warnings)
    except (ClientError, BotoCoreError) as exc:
        raise ProvisionError(f"the emulator at {endpoint_url} refused: {exc}") from exc
    return Provisioned(request_url, reply_urls, bucket, tuple(warnings))


def env_files(
    result: Provisioned, *, endpoint_url: str, region: str, keys_dir: Path, public_key: str | None
) -> dict[str, str]:
    """The environment of each bridge and of the collector, by name: `bridge-a`,
    `bridge-b`, ..., `collector`. Each is a file `set -a; . FILE` can load."""
    common = [
        "RELAY_ENVIRONMENT=local",
        f"RELAY_REGION={region}",
        f"RELAY_ENDPOINT_URL={endpoint_url}",
        f"RELAY_REQUEST_QUEUE_URL={result.request_queue_url}",
        f"RELAY_BUCKET={result.bucket}",
        "RELAY_ALLOW_DEV_ROUTES=true",
        "AWS_ACCESS_KEY_ID=testing",
        "AWS_SECRET_ACCESS_KEY=testing",
    ]
    key = (
        f"RELAY_COLLECTOR_PUBLIC_KEY={public_key}"
        if public_key
        else f"# RELAY_COLLECTOR_PUBLIC_KEY= missing: run `keys generate --out {keys_dir}` first,"
        " then provision again"
    )
    files: dict[str, str] = {}
    for index, reply in enumerate(result.reply_queue_urls):
        port = 8080 + index
        letter = string.ascii_lowercase[index]
        lines = [
            f"# --- bridge {letter.upper()} (127.0.0.1:{port}) ---",
            *common,
            "RELAY_BRIDGE_HOST=127.0.0.1",
            f"RELAY_BRIDGE_PORT={port}",
            f"RELAY_REPLY_QUEUE_URL={reply}",
            key,
        ]
        files[f"bridge-{letter}"] = "\n".join(lines) + "\n"
    lines = [
        "# --- collector ---",
        *common,
        f"RELAY_REPLY_QUEUE_URLS={','.join(result.reply_queue_urls)}",
        f"RELAY_COLLECTOR_PRIVATE_KEY_FILE={keys_dir}/collector.key",
        f"RELAY_INGRESS_KEY_FILE={keys_dir}/ingress.key",
        "RELAY_API_ORIGIN=http://127.0.0.1:8000",
    ]
    files["collector"] = "\n".join(lines) + "\n"
    return files


def env_lines(
    result: Provisioned, *, endpoint_url: str, region: str, keys_dir: Path, public_key: str | None
) -> str:
    """The same environments as one text, a section each."""
    files = env_files(
        result, endpoint_url=endpoint_url, region=region, keys_dir=keys_dir, public_key=public_key
    )
    return "\n".join(files.values())


def write_env_files(directory: Path, files: Mapping[str, str]) -> list[Path]:
    """Write each environment to `directory/<name>.env`, mode 0600, replacing
    what a previous run wrote. Returns the paths."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    written = []
    for name, content in files.items():
        path = directory / f"{name}.env"
        if path.is_symlink():
            raise ProvisionError(f"{path} is a symbolic link; refusing to write through it")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            os.write(descriptor, content.encode())
        finally:
            os.close(descriptor)
        written.append(path)
    return written


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cmp_relay.provision",
        description="Make the relay's queues and bucket on a LOCAL emulator (moto, LocalStack).",
    )
    parser.add_argument(
        "--endpoint-url", default="", help="the emulator, e.g. http://127.0.0.1:5000 (required)"
    )
    parser.add_argument("--replies", type=int, default=2, help="reply queues, one per bridge")
    parser.add_argument("--prefix", default="cmp-relay-local", help="name prefix")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--keys-dir",
        type=Path,
        default=Path("keys"),
        help="where `keys generate` wrote collector.key/.pub (default: keys)",
    )
    parser.add_argument(
        "--env-dir",
        type=Path,
        default=None,
        help="also write bridge-a.env, bridge-b.env, ..., collector.env here (mode 0600)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.endpoint_url:
        print(
            "error: provision is for a local emulator only: pass --endpoint-url."
            " On AWS, deploy deploy/cloudformation.yaml instead.",
            file=sys.stderr,
        )
        return 2
    if not args.prefix or not all(c.isalnum() or c == "-" for c in args.prefix):
        print("error: --prefix may hold only letters, digits and hyphens", file=sys.stderr)
        return 2
    try:
        result = provision(
            args.endpoint_url, prefix=args.prefix.lower(), replies=args.replies, region=args.region
        )
    except ProvisionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    keys_dir = args.keys_dir.resolve()
    public_file = keys_dir / "collector.pub"
    public = public_file.read_text().strip() if public_file.is_file() else None
    files = env_files(
        result,
        endpoint_url=args.endpoint_url,
        region=args.region,
        keys_dir=keys_dir,
        public_key=public,
    )
    sys.stdout.write("\n".join(files.values()))
    if args.env_dir is not None:
        try:
            written = write_env_files(args.env_dir, files)
        except (ProvisionError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {', '.join(str(p) for p in written)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
