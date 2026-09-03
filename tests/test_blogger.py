from __future__ import annotations

import pytest

from news2blogger.blogger import select_single_blog_id


def test_selects_the_only_accessible_blog() -> None:
    blogs = [{"id": "123", "name": "My Blog"}]

    assert select_single_blog_id(blogs) == "123"


def test_rejects_missing_accessible_blog() -> None:
    with pytest.raises(ValueError, match="no accessible blogs"):
        select_single_blog_id([])


def test_rejects_ambiguous_blog_selection() -> None:
    blogs = [
        {"id": "123", "name": "First"},
        {"id": "456", "name": "Second"},
    ]

    with pytest.raises(ValueError, match="multiple blogs") as error:
        select_single_blog_id(blogs)
    assert "First (123)" in str(error.value)
    assert "Second (456)" in str(error.value)
