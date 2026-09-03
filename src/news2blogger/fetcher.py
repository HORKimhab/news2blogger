from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import SourceArticle

MAX_ARTICLE_CHARS = 60_000


class FetchError(RuntimeError):
    pass


class ArticleFetcher:
    def __init__(self, user_agent: str, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def fetch(self, url: str) -> SourceArticle:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise FetchError(f"Invalid HTTP(S) URL: {url}")

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Could not download {url}: {exc}") from exc

        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            raise FetchError(f"Expected an HTML page, received {content_type or 'unknown type'}")

        soup = BeautifulSoup(response.text, "html.parser")
        metadata = self._metadata(soup)
        for unwanted in soup.select("script, style, nav, footer, header, aside, form, noscript"):
            unwanted.decompose()

        text = self._article_text(soup)
        if len(text) < 200:
            raise FetchError("The page did not contain enough readable article text")

        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        canonical_url = urljoin(url, canonical.get("href")) if canonical else url
        return SourceArticle(
            url=canonical_url,
            title=metadata.get("title") or self._title(soup) or "Untitled article",
            text=text[:MAX_ARTICLE_CHARS],
            author=metadata.get("author"),
            publisher=metadata.get("publisher") or parsed.netloc.removeprefix("www."),
            published_at=metadata.get("published_at"),
        )

    def feed_urls(self, feed_url: str, limit: int = 10) -> list[str]:
        try:
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Could not download feed {feed_url}: {exc}") from exc
        feed = feedparser.loads(response.content)
        if feed.bozo and not feed.entries:
            raise FetchError(f"Could not parse feed {feed_url}: {feed.bozo_exception}")
        return [entry.link for entry in feed.entries[:limit] if entry.get("link")]

    @staticmethod
    def _title(soup: BeautifulSoup) -> str | None:
        heading = soup.find("h1")
        if heading:
            return heading.get_text(" ", strip=True)
        return soup.title.get_text(" ", strip=True) if soup.title else None

    @staticmethod
    def _article_text(soup: BeautifulSoup) -> str:
        # Prefer explicit article-body containers. Some publishers use <article>
        # for small recommendation cards before the real story content.
        selectors = (
            '[itemprop="articleBody"]',
            ".articlebody",
            ".post-body",
            "article",
            "main",
            "body",
        )
        for selector in selectors:
            candidate_texts: list[str] = []
            for container in soup.select(selector):
                paragraphs = [
                    node.get_text(" ", strip=True) for node in container.find_all("p")
                ]
                candidate_texts.append(
                    "\n\n".join(part for part in paragraphs if len(part) >= 40)
                )
            if candidate_texts:
                text = max(candidate_texts, key=len)
                if len(text) >= 200:
                    return text
        return ""

    @staticmethod
    def _metadata(soup: BeautifulSoup) -> dict[str, str]:
        result: dict[str, str] = {}
        mappings = {
            "og:title": "title",
            "author": "author",
            "article:published_time": "published_at",
            "og:site_name": "publisher",
        }
        for key, output_key in mappings.items():
            node = soup.find("meta", attrs={"property": key}) or soup.find(
                "meta", attrs={"name": key}
            )
            if node and node.get("content"):
                result[output_key] = str(node["content"]).strip()

        for node in soup.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(node.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            candidates = payload if isinstance(payload, list) else [payload]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                if not result.get("author"):
                    author = item.get("author")
                    if isinstance(author, dict):
                        result["author"] = str(author.get("name", "")).strip()
                if not result.get("publisher"):
                    publisher = item.get("publisher")
                    if isinstance(publisher, dict):
                        result["publisher"] = str(publisher.get("name", "")).strip()
        return {key: value for key, value in result.items() if value}
