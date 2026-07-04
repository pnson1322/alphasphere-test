"""Entrypoint for the support-content assistant sync pipeline."""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from scraper.markdown_converter import build_markdown_file, slugify
from scraper.state_tracker import (
    classify_articles,
    compute_content_hash,
    load_state,
    save_state,
)
from scraper.zendesk_client import fetch_all_articles
from uploader.file_search_store import (
    delete_document,
    get_or_create_file_search_store,
    upload_articles_to_store,
)


DATA_DIR = Path("data")
ARTICLES_DIR = DATA_DIR / "articles"
STATE_FILE = DATA_DIR / "state.json"
IDS_FILE = DATA_DIR / "ids.json"
FILE_SEARCH_STORE_DISPLAY_NAME = "optisigns-support-docs"
LOGGER = logging.getLogger(__name__)


def _read_optional_positive_int(name: str) -> int | None:
    """Read an optional positive integer setting from the environment."""
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return None

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive integer when set.") from exc

    if value <= 0:
        raise SystemExit(f"{name} must be greater than zero when set.")

    return value


def _slug_for_article(article: dict, state: dict, used_slugs: set[str]) -> str:
    """Return a stable, unique slug for an article."""
    article_id = str(article.get("id") or "")
    previous_slug = state.get(article_id, {}).get("slug")
    if previous_slug:
        used_slugs.add(previous_slug)
        return previous_slug

    base_slug = slugify(str(article.get("title") or article_id or "untitled"))
    slug = base_slug
    suffix = 2
    while slug in used_slugs:
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    used_slugs.add(slug)
    return slug


def _save_markdown(article: dict, slug: str) -> Path:
    """Save one article as Markdown and return its output path."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ARTICLES_DIR / f"{slug}.md"
    output_path.write_text(build_markdown_file(article), encoding="utf-8")
    return output_path


def run() -> None:
    """Fetch Zendesk articles, save Markdown files, and upload them to Gemini.

    Only new or changed articles are uploaded. State is persisted so daily runs
    can skip unchanged articles.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    load_dotenv()

    subdomain = os.getenv("ZENDESK_SUBDOMAIN")
    if not subdomain:
        raise SystemExit("ZENDESK_SUBDOMAIN is not set. Copy .env.sample to .env first.")

    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set. Add it to .env before uploading.")

    max_articles_to_upload = _read_optional_positive_int("MAX_ARTICLES_TO_UPLOAD")

    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    articles = fetch_all_articles(subdomain)
    state = load_state(str(STATE_FILE))
    classified = classify_articles(articles, state)

    failed_count = 0
    changed_articles = classified["added"] + classified["updated"]
    total_changed_count = len(changed_articles)

    if max_articles_to_upload is not None:
        changed_articles = changed_articles[:max_articles_to_upload]
        print(
            "MAX_ARTICLES_TO_UPLOAD is set; "
            f"limited test run will process {len(changed_articles)} "
            f"of {total_changed_count} changed article(s)."
        )

    updated_ids = {str(article.get("id") or "") for article in classified["updated"]}
    used_slugs = {
        entry.get("slug")
        for entry in state.values()
        if isinstance(entry, dict) and entry.get("slug")
    }
    upload_items: list[dict] = []

    for article in changed_articles:
        try:
            article_id = str(article.get("id") or "")
            slug = _slug_for_article(article, state, used_slugs)
            output_path = _save_markdown(article, slug)

            upload_items.append(
                {
                    "article": article,
                    "slug": slug,
                    "path": output_path,
                }
            )
        except Exception as exc:
            failed_count += 1
            LOGGER.warning("Failed to save article %s: %s", article.get("id"), exc)

    print(f"Fetched articles: {len(articles)}")
    print(f"Changed articles queued: {len(upload_items)}")

    client = genai.Client()
    file_search_store_name = get_or_create_file_search_store(
        client,
        FILE_SEARCH_STORE_DISPLAY_NAME,
    )

    for item in upload_items:
        article_id = str(item["article"].get("id") or "")
        if article_id not in updated_ids:
            continue

        old_document_name = state.get(article_id, {}).get("file_search_document_name")
        if old_document_name and not delete_document(client, old_document_name):
            item["delete_failed"] = True
            failed_count += 1
        elif old_document_name:
            state.setdefault(article_id, {}).pop("file_search_document_name", None)

    upload_items = [item for item in upload_items if not item.get("delete_failed")]
    upload_file_paths = [str(item["path"]) for item in upload_items]
    upload_summary = upload_articles_to_store(
        client,
        file_search_store_name,
        upload_file_paths,
    )
    failed_count += upload_summary["files_failed"]

    document_names_by_path = {
        Path(document["file_path"]).resolve(): document["document_name"]
        for document in upload_summary.get("documents", [])
    }

    for item in upload_items:
        path = Path(item["path"]).resolve()
        document_name = document_names_by_path.get(path)
        if not document_name:
            LOGGER.warning("Upload did not return a document name for %s", path)
            continue

        article = item["article"]
        article_id = str(article.get("id") or "")
        state[article_id] = {
            "content_hash": compute_content_hash(article),
            "slug": item["slug"],
            "file_search_document_name": document_name,
        }

    save_state(str(STATE_FILE), state)

    IDS_FILE.write_text(
        json.dumps(
            {
                "file_search_store_name": file_search_store_name,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("Daily Sync Summary")
    print("------------------")
    print(f"File Search Store Name: {file_search_store_name}")
    print(f"Added: {len(classified['added'])}")
    print(f"Updated: {len(classified['updated'])}")
    print(f"Skipped: {len(classified['skipped'])}")
    print(f"Failed: {failed_count}")
    print(f"Files uploaded: {upload_summary['files_uploaded']}")


if __name__ == "__main__":
    try:
        run()
    except SystemExit:
        raise
    except Exception:
        LOGGER.exception("Daily sync failed.")
        sys.exit(1)
