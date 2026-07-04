"""State tracking helpers for article delta syncs."""

import hashlib
import json
from pathlib import Path


def compute_content_hash(article: dict) -> str:
    """Compute a SHA-256 hash of an article's raw HTML body."""
    body = str(article.get("body") or "")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_state(state_path: str) -> dict:
    """Load sync state from disk, or return an empty state if missing."""
    path = Path(state_path)
    if not path.is_file():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state_path: str, state: dict) -> None:
    """Save sync state as pretty JSON."""
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify_articles(articles: list[dict], state: dict) -> dict:
    """Classify articles as added, updated, or skipped based on content hash."""
    added: list[dict] = []
    updated: list[dict] = []
    skipped: list[dict] = []

    for article in articles:
        article_id = str(article.get("id") or "")
        if not article_id:
            added.append(article)
            continue

        current_hash = compute_content_hash(article)
        previous = state.get(article_id)
        if previous is None:
            added.append(article)
        elif previous.get("content_hash") != current_hash:
            updated.append(article)
        else:
            skipped.append(article)

    return {"added": added, "updated": updated, "skipped": skipped}
