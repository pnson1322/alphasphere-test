"""OpenAI vector store upload placeholders."""

from pathlib import Path


def upload_markdown_file(file_path: Path, vector_store_id: str | None = None) -> dict:
    """Upload one Markdown article file to an OpenAI vector store.

    This function will eventually create or reuse a vector store, upload the
    file, and return metadata needed for logging and later reconciliation.
    """
    raise NotImplementedError("Single-file vector store upload is not implemented yet.")


def upload_markdown_directory(
    directory: Path,
    vector_store_id: str | None = None,
) -> list[dict]:
    """Upload all changed Markdown files from a directory to an OpenAI vector store.

    The final implementation should iterate over generated Markdown files,
    report progress, and return upload results for observability.
    """
    raise NotImplementedError("Directory vector store upload is not implemented yet.")

