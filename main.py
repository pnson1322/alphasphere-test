"""Entrypoint for the support-content assistant sync pipeline."""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from scraper.markdown_converter import build_markdown_file, slugify
from scraper.zendesk_client import fetch_all_articles
from uploader.file_search_store import (
    get_or_create_file_search_store,
    upload_articles_to_store,
)


DATA_DIR = Path("data")
ARTICLES_DIR = DATA_DIR / "articles"
STATE_FILE = DATA_DIR / "state.json"
IDS_FILE = DATA_DIR / "ids.json"
FILE_SEARCH_STORE_DISPLAY_NAME = "optisigns-support-docs"
LOGGER = logging.getLogger(__name__)


def load_state(state_file: Path = STATE_FILE) -> dict:
    """Load the persisted sync state from disk.

    The state will track article IDs, content hashes, updated timestamps, and
    upload metadata so future runs can perform delta syncs.
    """
    raise NotImplementedError("State loading is not implemented yet.")


def save_state(state: dict, state_file: Path = STATE_FILE) -> None:
    """Persist sync state to disk after a successful run.

    The final implementation should write state atomically to avoid corrupting
    delta-sync metadata if a process exits early.
    """
    raise NotImplementedError("State saving is not implemented yet.")


def detect_delta(articles: list[dict], state: dict) -> list[dict]:
    """Identify articles that are new or changed since the previous sync.

    This will compare Zendesk updated timestamps and/or content hashes against
    the persisted state.
    """
    raise NotImplementedError("Delta detection is not implemented yet.")


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


def run() -> None:
    """Fetch Zendesk articles, save Markdown files, and upload them to Gemini.

    Delta detection is intentionally left for a later implementation step.
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

    saved_count = 0
    failed_count = 0
    saved_file_paths: list[Path] = []
    seen_slugs: dict[str, int] = {}

    for article in articles:
        try:
            base_slug = slugify(str(article.get("title") or article.get("id") or "untitled"))
            slug_count = seen_slugs.get(base_slug, 0)
            seen_slugs[base_slug] = slug_count + 1
            slug = base_slug if slug_count == 0 else f"{base_slug}-{slug_count + 1}"

            output_path = ARTICLES_DIR / f"{slug}.md"
            output_path.write_text(build_markdown_file(article), encoding="utf-8")
            saved_file_paths.append(output_path)
            saved_count += 1
        except Exception as exc:
            failed_count += 1
            LOGGER.warning("Failed to save article %s: %s", article.get("id"), exc)

    print(f"Fetched articles: {len(articles)}")
    print(f"Saved markdown files: {saved_count}")
    print(f"Failed articles: {failed_count}")

    upload_file_paths = [str(path) for path in saved_file_paths]
    if max_articles_to_upload is not None:
        upload_file_paths = upload_file_paths[:max_articles_to_upload]
        print(
            "MAX_ARTICLES_TO_UPLOAD is set; "
            f"limited test run will upload {len(upload_file_paths)} file(s)."
        )

    client = genai.Client()
    file_search_store_name = get_or_create_file_search_store(
        client,
        FILE_SEARCH_STORE_DISPLAY_NAME,
    )
    upload_summary = upload_articles_to_store(
        client,
        file_search_store_name,
        upload_file_paths,
    )

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
    print("Gemini Upload Summary")
    print("---------------------")
    print(f"File Search Store Name: {file_search_store_name}")
    print(f"Files uploaded: {upload_summary['files_uploaded']}")
    print(f"Files failed: {upload_summary['files_failed']}")


if __name__ == "__main__":
    run()
