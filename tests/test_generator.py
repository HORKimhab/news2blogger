from __future__ import annotations

import json
import subprocess

import pytest

from news2blogger.generator import POST_SCHEMA, PostGenerator
from news2blogger.models import SourceArticle


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        PostGenerator("", "gpt-5-mini", provider="openai")


def test_codex_provider_uses_local_cli_auth(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        captured["prompt"] = kwargs["input"]
        schema_path = command[command.index("--output-schema") + 1]
        assert json.loads(open(schema_path, encoding="utf-8").read()) == POST_SCHEMA
        output_path = command[command.index("--output-last-message") + 1]
        with open(output_path, "w", encoding="utf-8") as output:
            json.dump(
                {
                    "title": "Translated title",
                    "summary_heading": "Summary in Khmer",
                    "summary": "Translated summary",
                    "topic_sections": [
                        {
                            "heading": "First concept",
                            "summary": "Concept explanation",
                            "key_points": ["Detail one"],
                        },
                        {
                            "heading": "Second concept",
                            "summary": "Another explanation",
                            "key_points": ["Detail two"],
                        },
                    ],
                    "concern": {
                        "heading": "Concern",
                        "summary": "A concern",
                        "key_points": [],
                        "flow": ["Discover", "Act"],
                    },
                    "main_point": {
                        "heading": "Main point",
                        "summary": "The takeaway",
                        "key_points": [],
                    },
                },
                output,
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-codex")
    monkeypatch.setenv("CODEX_API_KEY", "must-not-reach-codex")
    monkeypatch.setenv("NEWS2BLOGGER_ENV_PASSPHRASE", "must-not-reach-codex")
    monkeypatch.setattr(subprocess, "run", fake_run)
    generator = PostGenerator(
        "",
        "gpt-5-mini",
        provider="codex",
        codex_command="codex-test",
        codex_model="codex-model-test",
    )

    post = generator.generate(
        SourceArticle(
            url="https://example.com/story",
            title="Original title",
            text="Article text long enough for this generator unit test.",
        ),
        target_language="Khmer",
        max_words=350,
    )

    assert post.title == "Translated title"
    assert post.key_points == ()
    assert post.sections[0].heading == "First concept"
    assert captured["command"][0] == "codex-test"
    assert "codex-model-test" in captured["command"]
    assert "Original title" in captured["prompt"]
    environment = captured["environment"]
    assert "OPENAI_API_KEY" not in environment
    assert "CODEX_API_KEY" not in environment
    assert "NEWS2BLOGGER_ENV_PASSPHRASE" not in environment
