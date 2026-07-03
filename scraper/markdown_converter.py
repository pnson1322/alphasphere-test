"""HTML-to-Markdown conversion placeholders for support articles."""


def convert_html_to_markdown(html: str) -> str:
    """Convert an article HTML body into clean Markdown.

    This function will eventually strip noisy markup, preserve useful links and
    headings, normalize whitespace, and produce Markdown suitable for vector
    store ingestion.
    """
    raise NotImplementedError("Markdown conversion is not implemented yet.")


def build_article_markdown(article: dict) -> str:
    """Build a complete Markdown document for a Zendesk article.

    The final implementation should include article metadata such as title,
    source URL, article ID, and updated timestamp before the converted body.
    """
    raise NotImplementedError("Article Markdown assembly is not implemented yet.")

