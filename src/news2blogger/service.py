from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .blogger import BloggerClient
from .config import Settings
from .fetcher import ArticleFetcher
from .formatter import load_markdown_preview, render_post
from .generator import PostGenerator
from .models import GeneratedPost, SourceArticle
from .state import StateStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    article: SourceArticle
    post: GeneratedPost
    html: str
    blogger_post_id: str | None
    skipped: bool = False


class PublishingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.fetcher = ArticleFetcher(settings.http_user_agent)
        self.generator = PostGenerator(
            settings.openai_api_key,
            settings.openai_model,
            provider=settings.generator_provider,
            codex_command=settings.codex_command,
            codex_model=settings.codex_model,
            codex_timeout_seconds=settings.codex_timeout_seconds,
        )

    def process_url(
        self,
        url: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        publish: bool | None = None,
    ) -> ProcessResult:
        with StateStore(self.settings.database_path) as state:
            if state.has_processed(url) and not force:
                logger.info("Skipping duplicate source: %s", url)
                placeholder = SourceArticle(url=url, title="", text="")
                return ProcessResult(
                    article=placeholder,
                    post=GeneratedPost("", "", ()),
                    html="",
                    blogger_post_id=None,
                    skipped=True,
                )

            article = self.fetcher.fetch(url)
            if state.has_processed(article.url) and not force:
                logger.info("Skipping duplicate canonical source: %s", article.url)
                return ProcessResult(
                    article=article,
                    post=GeneratedPost("", "", ()),
                    html="",
                    blogger_post_id=None,
                    skipped=True,
                )
            post = self.generator.generate(
                article,
                target_language=self.settings.target_language,
                max_words=self.settings.summary_max_words,
            )
            html = render_post(article, post, self.settings.target_language)
            if dry_run:
                return ProcessResult(article, post, html, None)

            should_publish = self.settings.blogger_publish if publish is None else publish
            blogger = BloggerClient(
                self.settings.blogger_client_secrets, self.settings.blogger_token_file
            )
            blog_id = blogger.resolve_blog_id(self.settings.blogger_blog_id)
            if not self.settings.blogger_blog_id:
                logger.info("Automatically selected the only accessible Blogger blog: %s", blog_id)
            result = blogger.create_post(
                blog_id,
                post.title,
                html,
                draft=not should_publish,
            )
            post_id = str(result.get("id", "")) or None
            state.mark_success(article.url, post_id)
            if article.url != url:
                state.mark_success(url, post_id)
            return ProcessResult(article, post, html, post_id)

    def publish_markdown(
        self, url: str, path: Path, *, force: bool = False
    ) -> ProcessResult:
        title, html = load_markdown_preview(path)
        with StateStore(self.settings.database_path) as state:
            if state.has_processed(url) and not force:
                logger.info("Skipping duplicate source: %s", url)
                article = SourceArticle(url=url, title=title, text="")
                return ProcessResult(
                    article,
                    GeneratedPost(title, "", ()),
                    html,
                    None,
                    skipped=True,
                )
            blogger = BloggerClient(
                self.settings.blogger_client_secrets, self.settings.blogger_token_file
            )
            blog_id = blogger.resolve_blog_id(self.settings.blogger_blog_id)
            if not self.settings.blogger_blog_id:
                logger.info("Automatically selected the only accessible Blogger blog: %s", blog_id)
            result = blogger.create_post(blog_id, title, html, draft=False)
            post_id = str(result.get("id", "")) or None
            state.mark_success(url, post_id)
        article = SourceArticle(url=url, title=title, text="")
        return ProcessResult(article, GeneratedPost(title, "", ()), html, post_id)
