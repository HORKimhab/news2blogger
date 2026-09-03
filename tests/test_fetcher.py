from news2blogger.fetcher import ArticleFetcher


def test_metadata_extracts_open_graph_fields() -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        """<html><head>
        <meta property="og:title" content="A title">
        <meta name="author" content="A writer">
        <meta property="og:site_name" content="A publisher">
        </head></html>""",
        "html.parser",
    )

    assert ArticleFetcher._metadata(soup) == {
        "title": "A title",
        "author": "A writer",
        "publisher": "A publisher",
    }


def test_article_text_prefers_real_article_body_over_article_cards() -> None:
    from bs4 import BeautifulSoup

    story_paragraph = "This is the real article text with enough detail for extraction. " * 5
    soup = BeautifulSoup(
        f"""<html><body>
        <article><h2>Recommendation card</h2></article>
        <main>
          <article><h2>Another card</h2></article>
          <div class="articlebody">
            <p>{story_paragraph}</p>
            <p>{story_paragraph}</p>
          </div>
        </main>
        </body></html>""",
        "html.parser",
    )

    text = ArticleFetcher._article_text(soup)

    assert text.count("This is the real article text") == 10
    assert "Recommendation card" not in text
