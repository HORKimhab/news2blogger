from pathlib import Path
from types import SimpleNamespace

import pytest

import news2blogger.cli as cli
from news2blogger.cli import _show_result, main
from news2blogger.models import ConceptSection, GeneratedPost, SourceArticle
from news2blogger.service import ProcessResult


def test_show_result_writes_markdown_preview(tmp_path: Path) -> None:
    output = tmp_path / "preview.md"
    article = SourceArticle("https://example.com/story", "Source title", "Source text")
    post = GeneratedPost(
        "Generated title",
        "Overview",
        ("First", "Second"),
        "Summary in Khmer",
        (
            ConceptSection("Google", "topic", "Google summary", ("Detail",)),
            ConceptSection("Concern", "concern", "Concern summary", flow=("Find", "Fix")),
            ConceptSection("Main Point", "main_point", "Takeaway"),
        ),
    )
    result = ProcessResult(article, post, "<p>Summary</p>", None)

    _show_result(result, output)

    markdown = output.read_text(encoding="utf-8")
    assert "# Generated title" in markdown
    assert "## Summary in Khmer" in markdown
    assert "### 1. Google" in markdown
    assert "### ⚠️ Concern" in markdown
    assert "> Find → Fix" in markdown
    assert "[អត្ថបទដើម — Original source](https://example.com/story)" in markdown


def test_output_requires_dry_run_or_publish(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["url", "https://example.com/story", "--output", str(tmp_path / "preview.md")])

    assert exc_info.value.code == 2


def test_dry_run_and_publish_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["url", "https://example.com/story", "--dry-run", "--publish"])

    assert exc_info.value.code == 2


def test_publish_with_existing_output_reuses_markdown(tmp_path: Path, monkeypatch) -> None:
    preview = tmp_path / "reviewed.md"
    preview.write_text("# Reviewed title\n\nReviewed body\n", encoding="utf-8")
    calls: list[tuple[str, Path, bool]] = []

    class FakeService:
        def __init__(self, settings) -> None:
            pass

        def publish_markdown(self, url: str, path: Path, *, force: bool = False):
            calls.append((url, path, force))
            article = SourceArticle(url, "Reviewed title", "")
            post = GeneratedPost("Reviewed title", "", ())
            return ProcessResult(article, post, "<p>Reviewed body</p>", "post-123")

        def process_url(self, *args, **kwargs):
            raise AssertionError("existing Markdown must not be generated again")

    monkeypatch.setattr(
        cli.Settings,
        "from_env",
        lambda env_file: SimpleNamespace(log_level="INFO"),
    )
    monkeypatch.setattr(cli, "PublishingService", FakeService)

    result = main(
        [
            "url",
            "https://example.com/story",
            "--output",
            str(preview),
            "--publish",
        ]
    )

    assert result == 0
    assert calls == [("https://example.com/story", preview, False)]
