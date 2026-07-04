"""Manual Gemini File Search query script for OptiBot.

Usage:
    python query_assistant.py "How do I add a YouTube video?"
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from uploader.file_search_store import OPTIBOT_SYSTEM_PROMPT


IDS_FILE = Path("data") / "ids.json"


def _as_dict(value: Any) -> dict:
    """Convert SDK model objects to dictionaries when possible."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "to_json_dict"):
        return value.to_json_dict()
    return {}


def _find_source_value(value: Any) -> str | None:
    """Find a source URL or title inside a grounding metadata object."""
    data = _as_dict(value)
    if not data:
        return None

    custom_metadata = data.get("custom_metadata") or data.get("customMetadata") or []
    for item in custom_metadata:
        item_data = _as_dict(item)
        if item_data.get("key") == "source_url":
            return item_data.get("string_value") or item_data.get("stringValue")

    for key in ("source_url", "sourceUrl", "uri", "url", "title", "display_name", "displayName"):
        if data.get(key):
            return str(data[key])

    for nested_value in data.values():
        if isinstance(nested_value, list):
            for item in nested_value:
                found = _find_source_value(item)
                if found:
                    return found
        elif isinstance(nested_value, dict) or hasattr(nested_value, "model_dump"):
            found = _find_source_value(nested_value)
            if found:
                return found

    return None


def _grounding_sources(response) -> list[str]:
    """Extract unique grounding source labels from a Gemini response."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []

    grounding_metadata = getattr(candidates[0], "grounding_metadata", None)
    if not grounding_metadata:
        return []

    metadata = _as_dict(grounding_metadata)
    chunks = metadata.get("grounding_chunks") or metadata.get("groundingChunks") or []

    sources: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        source = _find_source_value(chunk)
        if source and source not in seen:
            sources.append(source)
            seen.add(source)

    return sources


def _load_file_search_store_name() -> str:
    """Load the Gemini File Search store resource name from data/ids.json."""
    if not IDS_FILE.is_file():
        raise SystemExit("data/ids.json not found. Run main.py to create/upload a store first.")

    ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    store_name = ids.get("file_search_store_name")
    if not store_name:
        raise SystemExit("data/ids.json is missing file_search_store_name. Run main.py again.")

    return str(store_name)


def main() -> None:
    """Ask a question against the uploaded Gemini File Search store."""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set. Add it to .env before querying.")

    if len(sys.argv) < 2:
        raise SystemExit('Usage: python query_assistant.py "How do I add a YouTube video?"')

    user_question = " ".join(sys.argv[1:])
    file_search_store_name = _load_file_search_store_name()
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_question,
        config=types.GenerateContentConfig(
            system_instruction=OPTIBOT_SYSTEM_PROMPT,
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[file_search_store_name],
                    ),
                ),
            ],
        ),
    )

    print(response.text)

    sources = _grounding_sources(response)
    if sources:
        print()
        print("Sources:")
        for source in sources:
            print(f"- {source}")


if __name__ == "__main__":
    main()
