"""Key tools: the collector's key pair and the API's ingress secret.

    python -m cmp_relay.keys generate --out DIR [--force]
    python -m cmp_relay.keys public --key-file FILE
    python -m cmp_relay.keys ingress-key --out FILE [--force]

`generate` makes the collector's X25519 key pair: `DIR/collector.key` (the
private half, base64, mode 0600) and `DIR/collector.pub` (the public half). It
prints the public key, which is what the bridge is configured with
(`RELAY_COLLECTOR_PUBLIC_KEY`). The private key never leaves the inside.

`public` prints the public key that goes with a private key file, for when
only the private half was kept.

`ingress-key` writes a random 48-character URL-safe secret (mode 0600). The
collector sends it to the API (`RELAY_INGRESS_KEY_FILE`), and the API opens
sealed values in a relayed reply only when it matches (`RELAY_INGRESS_KEY` on
the API).

Nothing is overwritten unless `--force` is given: overwriting a live collector
key strands every request already sealed to it, and overwriting the ingress
secret makes the API stop opening values until both sides are changed.

Rotating the collector key: generate a new pair into a new directory; give the
collector the new private key as `RELAY_COLLECTOR_PRIVATE_KEY_FILE` and the old
one as `RELAY_COLLECTOR_PREVIOUS_KEY_FILE`; restart it; then give the bridges
the new public key; once every bridge has restarted, drop the previous key.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from collections.abc import Sequence
from pathlib import Path

from cmp_relay import sealing

#: 36 random bytes, URL-safe base64, no padding: exactly 48 characters.
_INGRESS_BYTES = 36


class KeyToolError(Exception):
    """A refusal the user can act on. The message says what to do."""


def _write(path: Path, content: str, *, mode: int, force: bool) -> None:
    """Write `content` to `path` with `mode`, refusing to replace a file unless
    `force`. The file is created with its final mode, so a secret is never
    readable by anyone else, not even for a moment."""
    if path.is_symlink():
        raise KeyToolError(f"{path} is a symbolic link; refusing to write a key through it")
    if path.exists() and not force:
        raise KeyToolError(f"{path} exists; pass --force to replace it")
    if path.exists() and not path.is_file():
        raise KeyToolError(f"{path} exists and is not a file")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | (0 if force else os.O_EXCL)
    try:
        descriptor = os.open(path, flags, mode)
    except OSError as exc:
        raise KeyToolError(f"cannot write {path}: {exc.strerror}") from exc
    try:
        os.fchmod(descriptor, mode)  # an existing file keeps its old mode otherwise
        os.write(descriptor, content.encode())
    finally:
        os.close(descriptor)


def generate(out: Path, *, force: bool = False) -> str:
    """Write a new collector key pair into `out`. Returns the public key."""
    private_file, public_file = out / "collector.key", out / "collector.pub"
    if not force:
        for file in (private_file, public_file):
            if file.exists():
                raise KeyToolError(f"{file} exists; pass --force to replace it")
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    private, public = sealing.generate_keypair()
    _write(private_file, private + "\n", mode=0o600, force=force)
    _write(public_file, public + "\n", mode=0o644, force=force)
    return public


def public_from_file(key_file: Path) -> str:
    """The public key that goes with the private key in `key_file`."""
    try:
        value = key_file.read_text()
    except OSError as exc:
        raise KeyToolError(f"cannot read {key_file}: {exc.strerror}") from exc
    try:
        return sealing.public_of(sealing.load_private(value))
    except ValueError as exc:
        raise KeyToolError(f"{key_file}: {exc}") from exc


def ingress_key(out: Path, *, force: bool = False) -> None:
    """Write a new ingress secret to `out`."""
    if not out.parent.is_dir():
        raise KeyToolError(f"{out.parent} is not a directory")
    secret = secrets.token_urlsafe(_INGRESS_BYTES)
    _write(out, secret + "\n", mode=0o600, force=force)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cmp_relay.keys",
        description="The relay's keys: the collector's key pair and the API's ingress secret.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    gen = commands.add_parser("generate", help="make the collector's key pair")
    gen.add_argument("--out", required=True, type=Path, help="directory for collector.key/.pub")
    gen.add_argument("--force", action="store_true", help="replace existing files")

    pub = commands.add_parser("public", help="print the public key of a private key file")
    pub.add_argument("--key-file", required=True, type=Path)

    ing = commands.add_parser("ingress-key", help="write a new ingress secret")
    ing.add_argument("--out", required=True, type=Path, help="file to write (mode 0600)")
    ing.add_argument("--force", action="store_true", help="replace an existing file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "generate":
            public = generate(args.out, force=args.force)
            print(public)
            print(
                f"wrote {args.out / 'collector.key'} (0600) and {args.out / 'collector.pub'};"
                " the bridge's RELAY_COLLECTOR_PUBLIC_KEY is the line above",
                file=sys.stderr,
            )
        elif args.command == "public":
            print(public_from_file(args.key_file))
        else:
            ingress_key(args.out, force=args.force)
            print(
                f"wrote {args.out} (0600): the collector's RELAY_INGRESS_KEY_FILE;"
                " the API's RELAY_INGRESS_KEY is its contents",
                file=sys.stderr,
            )
    except KeyToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
