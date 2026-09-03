from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

from .models import ConceptSection, GeneratedPost, SourceArticle

SYSTEM_PROMPT = """You are an accurate news editor, translator, and explainer.
Create an original concept summary in the requested target language. Organize it
like a high-quality ChatGPT explanation: a short overview, separate sections for
the major subjects or concepts, a section about implications or concerns, and a
clear main takeaway. Use familiar English technical terms alongside translations
when that improves clarity for the target audience.
Never copy long phrases or reproduce the source article. Do not invent facts,
opinions, quotations, names, numbers, or context. Preserve uncertainty and
attribution from the source. Return only data matching the requested schema.
The summary must stand on its own, while the publisher and link will be shown
separately by the application."""

POST_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary_heading": {"type": "string"},
        "summary": {"type": "string"},
        "topic_sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "summary": {"type": "string"},
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 6,
                    },
                },
                "required": ["heading", "summary", "key_points"],
                "additionalProperties": False,
            },
            "minItems": 2,
            "maxItems": 5,
        },
        "concern": {
            "type": "object",
            "properties": {
                "heading": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 5,
                },
                "flow": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "maxItems": 6,
                },
            },
            "required": ["heading", "summary", "key_points", "flow"],
            "additionalProperties": False,
        },
        "main_point": {
            "type": "object",
            "properties": {
                "heading": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                },
            },
            "required": ["heading", "summary", "key_points"],
            "additionalProperties": False,
        },
    },
    "required": [
        "title",
        "summary_heading",
        "summary",
        "topic_sections",
        "concern",
        "main_point",
    ],
    "additionalProperties": False,
}


class PostGenerator:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        provider: str = "codex",
        codex_command: str = "codex",
        codex_model: str | None = None,
        codex_timeout_seconds: int = 300,
    ) -> None:
        if provider not in {"codex", "openai"}:
            raise ValueError("GENERATOR_PROVIDER must be 'codex' or 'openai'")
        if provider == "openai" and not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self.provider = provider
        self.client = OpenAI(api_key=api_key) if provider == "openai" else None
        self.model = model
        self.codex_command = codex_command
        self.codex_model = codex_model
        self.codex_timeout_seconds = codex_timeout_seconds

    def generate(
        self, article: SourceArticle, target_language: str, max_words: int
    ) -> GeneratedPost:
        request = f"""Target language: {target_language}
Maximum length for the entire generated concept summary: {max_words} words.
Return 2-5 topic sections followed by exactly one concern and one main point.
Keep topic headings concise and do not include numbering or emoji in headings.
If the target language is Khmer, use exactly "សង្ខេបជាភាសាខ្មែរ" as the
summary heading. Put a flow only in the concern section.
Original title: {article.title}
Original publisher: {article.publisher or "Unknown"}
Original author: {article.author or "Unknown"}

SOURCE ARTICLE:
{article.text}"""
        if self.provider == "codex":
            output_text = self._generate_with_codex(request)
        else:
            assert self.client is not None
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=request,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "translated_article_summary",
                        "strict": True,
                        "schema": POST_SCHEMA,
                    }
                }
            )
            output_text = response.output_text
        return self._parse_output(output_text)

    def _generate_with_codex(self, request: str) -> str:
        prompt = f"""{SYSTEM_PROMPT}

Do not use tools, browse the web, inspect files, or modify anything. Work only
from the source article included below. Return only the JSON object required by
the supplied output schema.

{request}"""
        with tempfile.TemporaryDirectory(prefix="news2blogger-codex-") as directory:
            workdir = Path(directory)
            schema_file = workdir / "post-schema.json"
            output_file = workdir / "post.json"
            schema_file.write_text(json.dumps(POST_SCHEMA), encoding="utf-8")
            command = [
                self.codex_command,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--color",
                "never",
                "--output-schema",
                str(schema_file),
                "--output-last-message",
                str(output_file),
                "--cd",
                str(workdir),
            ]
            if self.codex_model:
                command.extend(("--model", self.codex_model))
            command.append("-")
            environment = os.environ.copy()
            for secret_name in (
                "OPENAI_API_KEY",
                "CODEX_API_KEY",
                "NEWS2BLOGGER_ENV_PASSPHRASE",
            ):
                environment.pop(secret_name, None)
            try:
                result = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=self.codex_timeout_seconds,
                    env=environment,
                )
            except FileNotFoundError as exc:
                raise RuntimeError(
                    f"Codex CLI was not found: {self.codex_command}. "
                    "Install it and run codex login."
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"Codex generation timed out after {self.codex_timeout_seconds} seconds"
                ) from exc
            if result.returncode != 0:
                detail = result.stderr.strip().splitlines()
                message = detail[-1] if detail else f"exit status {result.returncode}"
                raise RuntimeError(f"Codex generation failed: {message}")
            if not output_file.exists():
                raise RuntimeError("Codex generation did not produce an output file")
            return output_file.read_text(encoding="utf-8")

    @staticmethod
    def _parse_output(output_text: str) -> GeneratedPost:
        try:
            payload = json.loads(output_text)
            title = str(payload["title"]).strip()
            summary_heading = str(payload["summary_heading"]).strip()
            summary = str(payload["summary"]).strip()
            topic_sections = tuple(
                ConceptSection(
                    heading=str(section["heading"]).strip(),
                    kind="topic",
                    summary=str(section["summary"]).strip(),
                    key_points=tuple(
                        str(point).strip() for point in section["key_points"]
                    ),
                )
                for section in payload["topic_sections"]
            )
            concern_payload = payload["concern"]
            concern = ConceptSection(
                heading=str(concern_payload["heading"]).strip(),
                kind="concern",
                summary=str(concern_payload["summary"]).strip(),
                key_points=tuple(
                    str(point).strip() for point in concern_payload["key_points"]
                ),
                flow=tuple(str(step).strip() for step in concern_payload["flow"]),
            )
            main_payload = payload["main_point"]
            main_point = ConceptSection(
                heading=str(main_payload["heading"]).strip(),
                kind="main_point",
                summary=str(main_payload["summary"]).strip(),
                key_points=tuple(
                    str(point).strip() for point in main_payload["key_points"]
                ),
            )
            sections = (*topic_sections, concern, main_point)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError("The model returned an invalid post structure") from exc
        if (
            not title
            or not summary_heading
            or not summary
            or not sections
            or any(
                not section.heading
                or not section.summary
                or not all(section.key_points)
                or not all(section.flow)
                for section in sections
            )
        ):
            raise RuntimeError("The model returned an incomplete post")
        return GeneratedPost(
            title=title,
            summary=summary,
            key_points=(),
            summary_heading=summary_heading,
            sections=sections,
        )
