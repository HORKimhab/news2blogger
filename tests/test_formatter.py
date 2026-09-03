from news2blogger.formatter import load_markdown_preview, render_markdown, render_post
from news2blogger.models import ConceptSection, GeneratedPost, SourceArticle


def test_render_post_escapes_content_and_credits_source() -> None:
    article = SourceArticle(
        url="https://example.com/story?a=1&b=2",
        title="Original <Story>",
        text="source",
        author="A & B",
        publisher="Example News",
    )
    post = GeneratedPost("Translated", "Summary <safe>", ("One", "Two & three"))

    html = render_post(article, post, "Khmer")

    assert "Summary &lt;safe&gt;" in html
    assert "A &amp; B — Example News" in html
    assert 'href="https://example.com/story?a=1&amp;b=2"' in html
    assert "Original &lt;Story&gt;" in html
    assert "translated summary" in html
    assert "family=Battambang:wght@400;700" in html
    assert "font-family: 'Battambang', 'Khmer OS Battambang', sans-serif" in html
    assert "rean-it.com" in html
    assert "#hkimhab #hkimhab22" in html
    assert "https://t.me/shareknowledge_toeveryone" in html


def test_render_concept_post_and_markdown() -> None:
    article = SourceArticle(
        "https://example.com/story", "Source", "source", publisher="Example News"
    )
    post = GeneratedPost(
        "Title",
        "Overview",
        ("Top-level point",),
        "សង្ខេបជាភាសាខ្មែរ",
        (
            ConceptSection("Google", "topic", "Explanation", ("Detail",)),
            ConceptSection("Risks", "concern", "Risk explanation", flow=("Find", "Exploit")),
            ConceptSection("Main Point", "main_point", "Takeaway"),
        ),
    )

    html = render_post(article, post, "Khmer")
    markdown = render_markdown(article, post)

    assert "<h2>សង្ខេបជាភាសាខ្មែរ</h2>" in html
    assert "<h3>1. Google</h3>" in html
    assert "<blockquote>Find → Exploit</blockquote>" in html
    assert "## សង្ខេបជាភាសាខ្មែរ" in markdown
    assert "### ⚠️ Risks" in markdown
    assert "[អត្ថបទដើម — Example News](https://example.com/story)" in markdown
    assert "រៀន coding: [rean-it.com](http://rean-it.com/)" in markdown
    assert "#hkimhab #hkimhab22" in markdown
    assert "[https://t.me/shareknowledge_toeveryone]" in markdown
    google_doc_id = "1X33-0Q9hYI-N7MdiwyLbF1_gIZHDmexVMv2abblJrYY"
    assert google_doc_id in markdown


def test_load_markdown_preview_extracts_title_and_converts_body(tmp_path) -> None:
    preview = tmp_path / "preview.md"
    preview.write_text("# Reviewed title\n\n## Summary\n\n- One\n- Two\n", encoding="utf-8")

    title, html = load_markdown_preview(preview)

    assert title == "Reviewed title"
    assert "<h2>Summary</h2>" in html
    assert "<li>One</li>" in html
    assert "family=Battambang:wght@400;700" in html
    assert '<div class="news2blogger" lang="km"' in html
