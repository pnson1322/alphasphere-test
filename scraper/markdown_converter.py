"""HTML-to-Markdown conversion helpers for support articles."""

import json
import re

from bs4 import BeautifulSoup
from markdownify import markdownify as markdownify_html


def html_to_markdown(html_body: str) -> str:
    """Convert Zendesk article HTML body to clean Markdown.

    Script, style, and nav tags are removed before conversion. Markdownify
    preserves useful structure such as headings, code blocks, bullet lists, and
    links, while relative links are left untouched.
    """
    soup = BeautifulSoup(html_body or "", "html.parser")
    for tag in soup.find_all(["script", "style", "nav"]):
        tag.decompose()

    markdown = markdownify_html(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=["script", "style", "nav"],
    )
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def slugify(title: str) -> str:
    """Convert an article title into a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-") or "untitled"


def _yaml_string(value: object) -> str:
    """Return a JSON-escaped string, which is valid for YAML frontmatter."""
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def build_markdown_file(article: dict) -> str:
    """Build the final Markdown file content for one Zendesk article.

    The output includes YAML frontmatter with title, source URL, updated
    timestamp, and article ID, followed by the converted Markdown article body.
    """
    body = html_to_markdown(str(article.get("body") or ""))
    frontmatter = [
        "---",
        f"title: {_yaml_string(article.get('title'))}",
        f"url: {_yaml_string(article.get('html_url'))}",
        f"updated_at: {_yaml_string(article.get('updated_at'))}",
        f"article_id: {article.get('id')}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + body + "\n"


def convert_html_to_markdown(html: str) -> str:
    """Convert an article HTML body into clean Markdown.

    Kept as a compatibility wrapper around ``html_to_markdown``.
    """
    return html_to_markdown(html)


def build_article_markdown(article: dict) -> str:
    """Build a complete Markdown document for a Zendesk article.

    Kept as a compatibility wrapper around ``build_markdown_file``.
    """
    return build_markdown_file(article)
