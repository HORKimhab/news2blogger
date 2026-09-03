from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS processed_articles (
                source_hash TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                blogger_post_id TEXT,
                status TEXT NOT NULL,
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self.connection.commit()

    @staticmethod
    def source_hash(url: str) -> str:
        return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()

    def has_processed(self, url: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM processed_articles WHERE source_hash = ? AND status = 'success'",
            (self.source_hash(url),),
        ).fetchone()
        return row is not None

    def mark_success(self, url: str, blogger_post_id: str | None) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO processed_articles
               (source_hash, source_url, blogger_post_id, status)
               VALUES (?, ?, ?, 'success')""",
            (self.source_hash(url), url, blogger_post_id),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> StateStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

