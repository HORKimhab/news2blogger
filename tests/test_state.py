from pathlib import Path

from news2blogger.state import StateStore


def test_store_tracks_successful_url(tmp_path: Path) -> None:
    with StateStore(tmp_path / "state.db") as store:
        assert not store.has_processed("https://example.com/a")
        store.mark_success("https://example.com/a", "post-1")
        assert store.has_processed("https://example.com/a")
        assert not store.has_processed("https://example.com/b")

