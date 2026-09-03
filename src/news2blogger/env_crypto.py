from __future__ import annotations

import argparse
import base64
import getpass
import os
import re
import sys
import tempfile
from io import StringIO
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from dotenv import dotenv_values

PASSPHRASE_ENV = "NEWS2BLOGGER_ENV_PASSPHRASE"
TOKEN_PREFIX = "ENC[v1:"
TOKEN_SUFFIX = "]"
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32
MIN_PASSPHRASE_LENGTH = 12

_ASSIGNMENT_RE = re.compile(
    r"^(?P<prefix>\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)"
    r"(?P<value>.*?)(?P<newline>\r?\n)?$"
)


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < MIN_PASSPHRASE_LENGTH:
        raise ValueError(
            f"Encryption passphrase must contain at least {MIN_PASSPHRASE_LENGTH} characters"
        )
    return Scrypt(salt=salt, length=KEY_BYTES, n=2**15, r=8, p=1).derive(
        passphrase.encode("utf-8")
    )


def encrypt_env_value(value: str, variable_name: str, passphrase: str) -> str:
    """Encrypt one value and bind it to its environment-variable name."""
    if value.startswith(TOKEN_PREFIX) and value.endswith(TOKEN_SUFFIX):
        return value
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(
        nonce,
        value.encode("utf-8"),
        variable_name.encode("utf-8"),
    )
    payload = base64.urlsafe_b64encode(salt + nonce + ciphertext).decode("ascii")
    return f"{TOKEN_PREFIX}{payload}{TOKEN_SUFFIX}"


def decrypt_env_value(value: str, variable_name: str) -> str:
    """Decrypt an ENC value, or return an ordinary environment value unchanged."""
    if not (value.startswith(TOKEN_PREFIX) and value.endswith(TOKEN_SUFFIX)):
        return value

    passphrase = os.getenv(PASSPHRASE_ENV)
    if not passphrase:
        raise ValueError(
            f"{variable_name} is encrypted; export {PASSPHRASE_ENV} before running the app"
        )

    encoded = value[len(TOKEN_PREFIX) : -len(TOKEN_SUFFIX)]
    try:
        payload = base64.b64decode(encoded, altchars=b"-_", validate=True)
        minimum_length = SALT_BYTES + NONCE_BYTES + 16
        if len(payload) < minimum_length:
            raise ValueError("encrypted payload is too short")
        salt = payload[:SALT_BYTES]
        nonce = payload[SALT_BYTES : SALT_BYTES + NONCE_BYTES]
        ciphertext = payload[SALT_BYTES + NONCE_BYTES :]
        key = _derive_key(passphrase, salt)
        return AESGCM(key).decrypt(
            nonce,
            ciphertext,
            variable_name.encode("utf-8"),
        ).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(
            f"Cannot decrypt {variable_name}: wrong passphrase or damaged encrypted value"
        ) from exc


def encrypt_env_file(
    source: Path,
    destination: Path,
    variable_names: set[str] | None,
    passphrase: str,
) -> list[str]:
    if source.resolve() == destination.resolve():
        raise ValueError(
            "Source and destination must differ; refusing to overwrite the plaintext file"
        )
    if not source.is_file():
        raise FileNotFoundError(f"Environment file not found: {source}")

    text = source.read_text(encoding="utf-8")
    parsed = dotenv_values(stream=StringIO(text), interpolate=False)
    seen_names: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ASSIGNMENT_RE.match(line)
        if not match:
            raise ValueError(
                f"Unsupported dotenv syntax on line {line_number}; "
                "only one-line NAME=VALUE assignments are accepted"
            )
        name = match.group("name")
        if name in seen_names:
            raise ValueError(f"Duplicate variable {name} on line {line_number}")
        seen_names.add(name)

    selected = {
        name
        for name, value in parsed.items()
        if value not in (None, "") and (variable_names is None or name in variable_names)
    }
    if PASSPHRASE_ENV in selected:
        raise ValueError(f"Refusing to encrypt or store the master variable {PASSPHRASE_ENV}")
    if variable_names is not None:
        missing = sorted(variable_names - set(parsed))
        if missing:
            raise ValueError(f"Variables not found in {source}: {', '.join(missing)}")
        empty = sorted(name for name in variable_names if parsed.get(name) in (None, ""))
        if empty:
            raise ValueError(f"Variables have empty values in {source}: {', '.join(empty)}")

    output_lines: list[str] = []
    encrypted_names: list[str] = []
    for line in text.splitlines(keepends=True):
        match = _ASSIGNMENT_RE.match(line)
        if not match or match.group("name") not in selected:
            output_lines.append(line)
            continue
        name = match.group("name")
        value = parsed[name]
        assert value is not None
        encrypted = encrypt_env_value(value, name, passphrase)
        newline = match.group("newline") or ""
        output_lines.append(f"{match.group('prefix')}{encrypted}{newline}")
        encrypted_names.append(name)

    if not encrypted_names:
        raise ValueError("No non-empty values were selected for encryption")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary:
            temporary.write("".join(output_lines))
            temporary_path = Path(temporary.name)
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
    return encrypted_names


def _encryption_passphrase() -> str:
    from_environment = os.getenv(PASSPHRASE_ENV)
    if from_environment:
        return from_environment
    passphrase = getpass.getpass("New encryption passphrase: ")
    confirmation = getpass.getpass("Confirm passphrase: ")
    if passphrase != confirmation:
        raise ValueError("Passphrases do not match")
    return passphrase


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news2blogger-env",
        description="Encrypt selected values in a dotenv file using AES-256-GCM.",
    )
    parser.add_argument("source", type=Path, help="Plaintext dotenv file, such as .env")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file (default: SOURCE.encrypted)",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--key",
        action="append",
        dest="keys",
        metavar="NAME",
        help="Variable to encrypt; repeat for multiple variables",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        help="Encrypt every non-empty value",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    destination = args.output or args.source.with_name(f"{args.source.name}.encrypted")
    if destination.exists() and not args.force:
        print(
            f"Error: output already exists: {destination} (use --force to replace it)",
            file=sys.stderr,
        )
        return 2
    try:
        encrypted_names = encrypt_env_file(
            args.source,
            destination,
            None if args.all else set(args.keys),
            _encryption_passphrase(),
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Encrypted {', '.join(encrypted_names)} into {destination}")
    print(f"Export {PASSPHRASE_ENV} before using that file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
