"""Zendesk Help Center API client placeholders."""


def fetch_articles(subdomain: str) -> list[dict]:
    """Fetch articles from the Zendesk Help Center API for the given subdomain.

    This function will eventually handle pagination, locale/category filtering,
    authentication if needed, and normalization of Zendesk article payloads.
    """
    raise NotImplementedError("Zendesk article fetching is not implemented yet.")


def fetch_article_by_id(subdomain: str, article_id: str) -> dict:
    """Fetch a single Zendesk Help Center article by its article ID.

    This will be useful for targeted refreshes, retries, and debugging a
    specific article without running a full sync.
    """
    raise NotImplementedError("Single-article fetching is not implemented yet.")

