from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceArticle:
    url: str
    title: str
    text: str
    author: str | None = None
    publisher: str | None = None
    published_at: str | None = None


@dataclass(frozen=True, slots=True)
class ConceptSection:
    heading: str
    kind: str
    summary: str
    key_points: tuple[str, ...] = ()
    flow: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratedPost:
    title: str
    summary: str
    key_points: tuple[str, ...]
    summary_heading: str = "Summary"
    sections: tuple[ConceptSection, ...] = ()
