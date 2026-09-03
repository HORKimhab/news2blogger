from __future__ import annotations

import importlib.util
from pathlib import Path

from news2blogger.env_crypto import PASSPHRASE_ENV

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "encrypt_env.py"
SPEC = importlib.util.spec_from_file_location("encrypt_env_script", SCRIPT_PATH)
assert SPEC and SPEC.loader
encrypt_env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(encrypt_env)

PASSPHRASE = "correct horse battery staple"


def test_script_requires_matching_confirmation(tmp_path, monkeypatch, capsys) -> None:
    source = tmp_path / ".env"
    destination = tmp_path / ".env.encrypted"
    source.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
    monkeypatch.setenv(PASSPHRASE_ENV, PASSPHRASE)
    monkeypatch.setattr(encrypt_env.getpass, "getpass", lambda _prompt: "wrong passphrase")

    result = encrypt_env.main(
        ["--source", str(source), "--output", str(destination)]
    )

    assert result == 2
    assert not destination.exists()
    assert "does not match" in capsys.readouterr().err


def test_script_encrypts_after_confirmation(tmp_path, monkeypatch) -> None:
    source = tmp_path / ".env"
    destination = tmp_path / ".env.encrypted"
    source.write_text("OPENAI_API_KEY=secret\n", encoding="utf-8")
    monkeypatch.setenv(PASSPHRASE_ENV, PASSPHRASE)
    monkeypatch.setattr(encrypt_env.getpass, "getpass", lambda _prompt: PASSPHRASE)

    result = encrypt_env.main(
        ["--source", str(source), "--output", str(destination)]
    )

    assert result == 0
    assert "OPENAI_API_KEY=ENC[v1:" in destination.read_text(encoding="utf-8")
