"""Gemini File Search store helpers."""

import logging
import time
from pathlib import Path
from typing import Any

from tqdm import tqdm

from scraper.frontmatter import parse_frontmatter
from scraper.markdown_converter import slugify


OPTIBOT_SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

POLL_INTERVAL_SECONDS = 2.0
MAX_UPLOAD_ATTEMPTS = 3
INITIAL_UPLOAD_BACKOFF_SECONDS = 2.0
LOGGER = logging.getLogger(__name__)


def _iter_items(collection: Any):
    """Yield items from a google-genai list response or iterable."""
    items = getattr(collection, "items", None)
    if items is not None and not callable(items):
        yield from items
        return

    yield from collection


def get_or_create_file_search_store(client, display_name: str) -> str:
    """Return an existing Gemini File Search store name, or create it.

    The script may run repeatedly, so matching by display name avoids creating
    duplicate stores during daily sync runs.
    """
    for store in _iter_items(client.file_search_stores.list()):
        if getattr(store, "display_name", None) == display_name:
            return store.name

    store = client.file_search_stores.create(config={"display_name": display_name})
    return store.name


def _poll_operation(client, operation):
    """Poll a Gemini long-running operation until it finishes."""
    while not getattr(operation, "done", False):
        time.sleep(POLL_INTERVAL_SECONDS)
        operation = client.operations.get(operation)

    error = getattr(operation, "error", None)
    if error:
        raise RuntimeError(f"File upload operation failed: {error}")

    return operation


def _document_name_from_operation(operation) -> str | None:
    """Extract a created document resource name from an upload operation."""
    response = getattr(operation, "response", None)
    if response is None:
        return None

    return getattr(response, "document_name", None)


def _source_url_from_markdown(path: Path) -> str:
    """Read a Markdown file and return its frontmatter source URL."""
    metadata = parse_frontmatter(path.read_text(encoding="utf-8"))
    return str(metadata.get("url") or "")


def _upload_file_with_retries(
    client,
    store_name: str,
    path: Path,
    config: dict[str, Any],
):
    """Upload one file, retrying transient upload-call exceptions only."""
    delay = INITIAL_UPLOAD_BACKOFF_SECONDS
    last_error: Exception | None = None

    for attempt in range(1, MAX_UPLOAD_ATTEMPTS + 1):
        try:
            return client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store_name,
                file=str(path),
                config=config,
            )
        except Exception as exc:
            last_error = exc
            if attempt == MAX_UPLOAD_ATTEMPTS:
                break

            LOGGER.warning(
                "Upload call failed for %s on attempt %s/%s; retrying in %.0fs: %s",
                path,
                attempt,
                MAX_UPLOAD_ATTEMPTS,
                delay,
                exc,
            )
            time.sleep(delay)
            delay *= 2

    raise last_error or RuntimeError(f"Upload call failed for {path}")


def upload_articles_to_store(
    client,
    store_name: str,
    file_paths: list[str],
) -> dict:
    """Upload Markdown article files into a Gemini File Search store.

    Each file is uploaded directly to the store and tagged with ``source_url``
    custom metadata parsed from the Markdown frontmatter, so later answers can
    cite the original support article.
    """
    files_uploaded = 0
    files_failed = 0
    documents: list[dict[str, str]] = []

    for file_path in tqdm(file_paths, desc="Uploading articles", unit="file"):
        path = Path(file_path)
        if not path.is_file():
            files_failed += 1
            tqdm.write(f"Skipping missing file: {path}")
            continue

        display_name = slugify(path.stem)
        source_url = _source_url_from_markdown(path)
        config: dict[str, Any] = {
            "display_name": display_name,
            "custom_metadata": [
                {"key": "source_url", "string_value": source_url},
            ],
        }

        try:
            operation = _upload_file_with_retries(client, store_name, path, config)
            operation = _poll_operation(client, operation)
            document_name = _document_name_from_operation(operation)
            if not document_name:
                raise RuntimeError("Upload completed without a document resource name.")

            documents.append(
                {
                    "file_path": str(path),
                    "document_name": document_name,
                }
            )
            files_uploaded += 1
        except Exception as exc:
            files_failed += 1
            tqdm.write(f"Failed to upload {path}: {exc}")

    return {
        "files_uploaded": files_uploaded,
        "files_failed": files_failed,
        "documents": documents,
    }


def delete_document(client, document_name: str) -> bool:
    """Delete a Gemini File Search document by resource name."""
    try:
        client.file_search_stores.documents.delete(name=document_name)
        return True
    except Exception as exc:
        LOGGER.warning("Failed to delete file search document %s: %s", document_name, exc)
        return False
