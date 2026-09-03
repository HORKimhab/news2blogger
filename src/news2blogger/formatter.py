from __future__ import annotations

from html import escape
from pathlib import Path

import markdown

from .models import ConceptSection, GeneratedPost, SourceArticle

BLOGGER_FONT_FAMILY = "'Battambang', 'Khmer OS Battambang', sans-serif"
BLOGGER_FONT_STYLE = (
    '<style>@import url("https://fonts.googleapis.com/css2?'
    'family=Battambang:wght@400;700&display=swap");'
    f".news2blogger,.news2blogger *{{font-family:{BLOGGER_FONT_FAMILY} !important;}}"
    "</style>"
)

PROMO_HTML = (
    "  <hr>",
    '  <p>រៀន coding: <a href="http://rean-it.com/" rel="noopener noreferrer">'
    "rean-it.com</a></p>",
    "  <p>#hkimhab #hkimhab22</p>",
    "  <p>Join Telegram:</p>",
    "  <ul>",
    '    <li>IT Sharing Knowledge: <a href="https://t.me/shareknowledge_toeveryone" '
    'rel="noopener noreferrer">https://t.me/shareknowledge_toeveryone</a></li>',
    '    <li>Other Telegram: <a href="https://docs.google.com/document/d/'
    '1X33-0Q9hYI-N7MdiwyLbF1_gIZHDmexVMv2abblJrYY/edit?tab=t.0" '
    'rel="noopener noreferrer">https://docs.google.com/document/d/'
    '1X33-0Q9hYI-N7MdiwyLbF1_gIZHDmexVMv2abblJrYY/edit?tab=t.0</a></li>',
    "  </ul>",
)

PROMO_MARKDOWN = (
    "---",
    "",
    "រៀន coding: [rean-it.com](http://rean-it.com/)",
    "",
    "<span>#hkimhab #hkimhab22</span>",
    "",
    "Join Telegram:",
    "",
    "- IT Sharing Knowledge: "
    "[https://t.me/shareknowledge_toeveryone](https://t.me/shareknowledge_toeveryone)",
    "- Other Telegram: "
    "[https://docs.google.com/document/d/"
    "1X33-0Q9hYI-N7MdiwyLbF1_gIZHDmexVMv2abblJrYY/edit?tab=t.0]"
    "(https://docs.google.com/document/d/"
    "1X33-0Q9hYI-N7MdiwyLbF1_gIZHDmexVMv2abblJrYY/edit?tab=t.0)",
)


def _section_heading(section: ConceptSection, topic_number: int) -> str:
    if section.kind == "topic":
        return f"{topic_number}. {section.heading}"
    if section.kind == "concern":
        return f"⚠️ {section.heading}"
    return f"🎯 {section.heading}"


def render_post(article: SourceArticle, post: GeneratedPost, target_language: str) -> str:
    if post.sections:
        return _render_concept_post(article, post, target_language)
    points = "".join(f"<li>{escape(point)}</li>" for point in post.key_points)
    credit_parts = [part for part in (article.author, article.publisher) if part]
    credit = " — ".join(credit_parts) or "Original source"
    return "\n".join(
        [
            BLOGGER_FONT_STYLE,
            f'<div class="news2blogger" lang="{escape(target_language)}" '
            f'style="font-family: {BLOGGER_FONT_FAMILY};">',
            f"  <p>{escape(post.summary)}</p>",
            "  <h2>Key points</h2>",
            f"  <ul>{points}</ul>",
            "  <hr>",
            f"  <p><strong>Credit:</strong> {escape(credit)}</p>",
            "  <p><strong>Reference:</strong> "
            f'<a href="{escape(article.url, quote=True)}" rel="noopener noreferrer">'
            f"{escape(article.title)}</a></p>",
            "  <p><em>This post is an original translated summary of the referenced "
            "source. Please read the original article for complete context.</em></p>",
            *PROMO_HTML,
            "</div>",
        ]
    )


def _render_concept_post(
    article: SourceArticle, post: GeneratedPost, target_language: str
) -> str:
    lines = [
        BLOGGER_FONT_STYLE,
        f'<div class="news2blogger" lang="{escape(target_language)}" '
        f'style="font-family: {BLOGGER_FONT_FAMILY};">',
        f"  <h2>{escape(post.summary_heading)}</h2>",
        f"  <p>{escape(post.summary)}</p>",
    ]
    topic_number = 0
    for section in post.sections:
        if section.kind == "topic":
            topic_number += 1
        heading = _section_heading(section, topic_number)
        summary = escape(section.summary)
        if section.kind == "main_point":
            summary = f"<strong>{summary}</strong>"
        lines.extend((f"  <h3>{escape(heading)}</h3>", f"  <p>{summary}</p>"))
        if section.key_points:
            items = "".join(f"<li>{escape(point)}</li>" for point in section.key_points)
            lines.append(f"  <ul>{items}</ul>")
        if section.flow:
            lines.append(f"  <blockquote>{escape(' → '.join(section.flow))}</blockquote>")
    credit_parts = [part for part in (article.author, article.publisher) if part]
    credit = " — ".join(dict.fromkeys(credit_parts)) or "Original source"
    lines.extend(
        (
            "  <hr>",
            f"  <p><strong>Credit:</strong> {escape(credit)}</p>",
            "  <p><strong>Reference:</strong> "
            f'<a href="{escape(article.url, quote=True)}" rel="noopener noreferrer">'
            f"{escape(article.title)}</a></p>",
            *PROMO_HTML,
            "</div>",
        )
    )
    return "\n".join(lines)


def render_markdown(article: SourceArticle, post: GeneratedPost) -> str:
    lines = [f"# {post.title}", "", f"## {post.summary_heading}", "", post.summary]
    topic_number = 0
    for section in post.sections:
        if section.kind == "topic":
            topic_number += 1
        summary = f"**{section.summary}**" if section.kind == "main_point" else section.summary
        lines.extend(("", f"### {_section_heading(section, topic_number)}", "", summary))
        for point in section.key_points:
            lines.extend(("", f"- {point}"))
        if section.flow:
            lines.extend(("", f"> {' → '.join(section.flow)}"))
    publisher = article.publisher or "Original source"
    lines.extend(("", f"[អត្ថបទដើម — {publisher}]({article.url})", "", *PROMO_MARKDOWN, ""))
    return "\n".join(lines)


def load_markdown_preview(path: Path) -> tuple[str, str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not read Markdown preview {path}: {exc}") from exc
    lines = source.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"Markdown preview must start with '# Title': {path}")
    title = lines[0][2:].strip()
    if not title:
        raise ValueError(f"Markdown preview title is empty: {path}")
    body = "\n".join(lines[1:]).strip()
    if not body:
        raise ValueError(f"Markdown preview body is empty: {path}")
    converted = markdown.markdown(body, extensions=("extra", "sane_lists"))
    html = "\n".join(
        (
            BLOGGER_FONT_STYLE,
            '<div class="news2blogger" lang="km" '
            f'style="font-family: {BLOGGER_FONT_FAMILY};">',
            converted,
            "</div>",
        )
    )
    return title, html
