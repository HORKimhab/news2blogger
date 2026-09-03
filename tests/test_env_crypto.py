from __future__ import annotations

import os

import pytest

from news2blogger.config import Settings
from news2blogger.env_crypto import (
    PASSPHRASE_ENV,
    decrypt_env_value,
    encrypt_env_file,
    encrypt_env_value,
)

PASSPHRASE = "correct horse battery staple"


def test_encrypted_value_round_trip_and_variable_binding(monkeypatch: pytest.MonkeyPatch) -> None:
    encrypted = encrypt_env_value("sk-test-secret", "OPENAI_API_KEY", PASSPHRASE)
    assert encrypted.startswith("ENC[v1:")
    assert "sk-test-secret" not in encrypted

    monkeypatch.setenv(PASSPHRASE_ENV, PASSPHRASE)
    assert decrypt_env_value(encrypted, "OPENAI_API_KEY") == "sk-test-secret"
    with pytest.raises(ValueError, match="wrong passphrase or damaged"):
        decrypt_env_value(encrypted, "ANOTHER_VARIABLE")


def test_wrong_passphrase_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    encrypted = encrypt_env_value("secret", "OPENAI_API_KEY", PASSPHRASE)
    monkeypatch.setenv(PASSPHRASE_ENV, "this is the wrong passphrase")

    with pytest.raises(ValueError, match="wrong passphrase or damaged"):
        decrypt_env_value(encrypted, "OPENAI_API_KEY")


def test_settings_loads_encrypted_dotenv(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / ".env"
    encrypted_file = tmp_path / ".env.encrypted"
    source.write_text(
        "OPENAI_API_KEY=sk-test-secret\n"
        "OPENAI_MODEL=gpt-5-mini\n"
        "TARGET_LANGUAGE=Khmer\n",
        encoding="utf-8",
    )
    encrypt_env_file(source, encrypted_file, {"OPENAI_API_KEY"}, PASSPHRASE)

    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "TARGET_LANGUAGE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(PASSPHRASE_ENV, PASSPHRASE)
    settings = Settings.from_env(encrypted_file)

    assert settings.openai_api_key == "sk-test-secret"
    assert settings.openai_model == "gpt-5-mini"
    assert settings.target_language == "Khmer"
    assert encrypted_file.stat().st_mode & 0o777 == 0o600
    assert os.getenv("OPENAI_API_KEY", "").startswith("ENC[v1:")


def test_encrypt_all_preserves_empty_values_and_comments(tmp_path) -> None:
    source = tmp_path / ".env"
    destination = tmp_path / ".env.encrypted"
    source.write_text(
        "# Keep this comment\nOPENAI_API_KEY=secret\nBLOGGER_BLOG_ID=\n",
        encoding="utf-8",
    )

    names = encrypt_env_file(source, destination, None, PASSPHRASE)
    encrypted_text = destination.read_text(encoding="utf-8")

    assert names == ["OPENAI_API_KEY"]
    assert "# Keep this comment" in encrypted_text
    assert "OPENAI_API_KEY=ENC[v1:" in encrypted_text
    assert "BLOGGER_BLOG_ID=\n" in encrypted_text
    assert "secret" not in encrypted_text


def test_encrypt_file_rejects_syntax_it_cannot_safely_rewrite(tmp_path) -> None:
    source = tmp_path / ".env"
    destination = tmp_path / ".env.encrypted"
    source.write_text("OPENAI_API_KEY secret-without-equals\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported dotenv syntax on line 1"):
        encrypt_env_file(source, destination, None, PASSPHRASE)
    assert not destination.exists()
