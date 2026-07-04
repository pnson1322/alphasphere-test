"""Small frontmatter parsing helpers for generated Markdown articles."""

import json


def parse_frontmatter(markdown_text: str) -> dict:
    """Parse simple YAML frontmatter from a Markdown document.

    Supports the generated ``key: "value"`` and ``key: 123`` shape used by the
    scraper. It intentionally avoids a full YAML dependency for now.
    """
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    metadata: dict[str, object] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break

        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue

        if value.startswith('"') and value.endswith('"'):
            try:
                metadata[key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass

        if value.isdigit():
            metadata[key] = int(value)
        else:
            metadata[key] = value

    return metadata
