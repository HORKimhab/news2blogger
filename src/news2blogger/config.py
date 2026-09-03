from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .env_crypto import decrypt_env_value


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str = "") -> str:
    return decrypt_env_value(os.getenv(name, default), name)


@dataclass(frozen=True, slots=True)
class Settings:
    generator_provider: str
    openai_api_key: str
    openai_model: str
    codex_command: str
    codex_model: str | None
    codex_timeout_seconds: int
    target_language: str
    summary_max_words: int
    blogger_blog_id: str | None
    blogger_client_secrets: Path
    blogger_token_file: Path
    blogger_publish: bool
    database_path: Path
    log_level: str
    http_user_agent: str

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> Settings:
        load_dotenv(env_file)
        return cls(
            generator_provider=_env("GENERATOR_PROVIDER", "codex").strip().lower(),
            openai_api_key=_env("OPENAI_API_KEY"),
            openai_model=_env("OPENAI_MODEL", "gpt-5-mini"),
            codex_command=_env("CODEX_COMMAND", "codex"),
            codex_model=_env("CODEX_MODEL") or None,
            codex_timeout_seconds=int(_env("CODEX_TIMEOUT_SECONDS", "300")),
            target_language=_env("TARGET_LANGUAGE", "Khmer"),
            summary_max_words=int(_env("SUMMARY_MAX_WORDS", "350")),
            blogger_blog_id=_env("BLOGGER_BLOG_ID") or None,
            blogger_client_secrets=Path(
                _env("BLOGGER_CLIENT_SECRETS", "credentials.json")
            ),
            blogger_token_file=Path(_env("BLOGGER_TOKEN_FILE", "token.json")),
            blogger_publish=_as_bool(_env("BLOGGER_PUBLISH", "false")),
            database_path=Path(_env("DATABASE_PATH", "data/news2blogger.db")),
            log_level=_env("LOG_LEVEL", "INFO").upper(),
            http_user_agent=_env(
                "HTTP_USER_AGENT", "news2blogger/0.1 (+https://www.blogger.com/)"
            ),
        )
