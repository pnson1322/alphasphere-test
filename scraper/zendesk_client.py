"""Zendesk Help Center API client."""

import logging
import time
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT_SECONDS = 20
REQUEST_DELAY_SECONDS = 0.3


def _normalize_subdomain(subdomain: str) -> str:
    """Return a Zendesk host without scheme or trailing slash."""
    return subdomain.removeprefix("https://").removeprefix("http://").strip("/")


def _get_json_with_retry(url: str) -> dict[str, Any] | None:
    """Fetch JSON from a URL, retrying once before returning None."""
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt == 0:
                LOGGER.warning("Request failed for %s; retrying once: %s", url, exc)
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            LOGGER.warning("Request failed for %s after retry; skipping page: %s", url, exc)
            return None

    return None


def fetch_all_articles(subdomain: str) -> list[dict]:
    """Fetch all articles from the Zendesk Help Center API.

    The public endpoint is paginated through the ``next_page`` field. This
    function follows each page, waits briefly between requests, and returns the
    raw article dictionaries from Zendesk. If a page fails twice, the page is
    skipped with a warning and articles fetched so far are returned.
    """
    host = _normalize_subdomain(subdomain)
    next_page = f"https://{host}/api/v2/help_center/en-us/articles.json"
    articles: list[dict] = []

    while next_page:
        payload = _get_json_with_retry(next_page)
        if payload is None:
            break

        page_articles = payload.get("articles", [])
        if not isinstance(page_articles, list):
            LOGGER.warning("Unexpected articles payload at %s; skipping page", next_page)
            break

        articles.extend(page_articles)
        next_page = payload.get("next_page")

        if next_page:
            time.sleep(REQUEST_DELAY_SECONDS)

    return articles


def fetch_articles(subdomain: str) -> list[dict]:
    """Fetch all articles for the given Zendesk Help Center subdomain.

    Kept as a compatibility wrapper around ``fetch_all_articles``.
    """
    return fetch_all_articles(subdomain)


def fetch_article_by_id(subdomain: str, article_id: str) -> dict:
    """Fetch a single Zendesk Help Center article by its article ID.

    This will be useful for targeted refreshes, retries, and debugging a
    specific article without running a full sync.
    """
    raise NotImplementedError("Single-article fetching is not implemented yet.")
