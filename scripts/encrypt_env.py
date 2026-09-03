#!/usr/bin/env python3
"""Encrypt every non-empty value from .env into .env.encrypted."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

# Allow this repository script to work before an editable package install.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from news2blogger.env_crypto import PASSPHRASE_ENV, encrypt_env_file  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Encrypt all non-empty .env values using NEWS2BLOGGER_ENV_PASSPHRASE."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / ".env",
        help="Plaintext input (default: project .env)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / ".env.encrypted",
        help="Encrypted output (default: project .env.encrypted)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Atomically replace an existing output file",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip interactive passphrase confirmation (for trusted automation only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    passphrase = os.getenv(PASSPHRASE_ENV)
    if not passphrase:
        print(
            f"Error: export {PASSPHRASE_ENV} before running this script.",
            file=sys.stderr,
        )
        return 2
    if not args.no_confirm:
        try:
            confirmation = getpass.getpass("Confirm encryption passphrase: ")
        except (EOFError, KeyboardInterrupt):
            print("\nError: passphrase confirmation cancelled.", file=sys.stderr)
            return 2
        if confirmation != passphrase:
            print("Error: passphrase confirmation does not match.", file=sys.stderr)
            return 2
    if args.output.exists() and not args.force:
        print(
            f"Error: {args.output} already exists; use --force to replace it.",
            file=sys.stderr,
        )
        return 2

    try:
        encrypted_names = encrypt_env_file(
            args.source,
            args.output,
            variable_names=None,
            passphrase=passphrase,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(f"Created {args.output}")
    print(f"Encrypted {len(encrypted_names)} values: {', '.join(encrypted_names)}")
    print("Empty values and comments were preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
