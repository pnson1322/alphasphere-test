# Support Content Assistant

Scrapes Zendesk Help Center articles from OptiSigns, converts article bodies to Markdown, and uploads the Markdown files to a Google Gemini File Search store for RAG-style support answers.

## Folder Structure

```text
.
├── scraper/
│   ├── __init__.py
│   ├── zendesk_client.py
│   ├── markdown_converter.py
│   └── frontmatter.py
├── uploader/
│   ├── __init__.py
│   └── file_search_store.py
├── data/
│   ├── articles/
│   ├── ids.json
│   └── state.json
├── main.py
├── query_assistant.py
├── requirements.txt
├── .env.sample
├── .gitignore
├── Dockerfile
└── README.md
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.sample .env
```

Then fill in `.env`:

```env
GEMINI_API_KEY=
ZENDESK_SUBDOMAIN=support.optisigns.com
MAX_ARTICLES_TO_UPLOAD=
```

Set `MAX_ARTICLES_TO_UPLOAD` to a small number, such as `5`, for a test upload before running the full article set.

## Upload Articles

Run the scraper and Gemini File Search upload:

```powershell
python main.py
```

This will:

- Fetch Zendesk articles from `support.optisigns.com`.
- Convert each article body to Markdown in `data/articles/`.
- Create or reuse a Gemini File Search store named `optisigns-support-docs`.
- Upload the Markdown files to that store.
- Save the store resource name to `data/ids.json`.

## Query OptiBot

After `main.py` has uploaded at least one article, ask a test question:

```powershell
python query_assistant.py "How do I add a YouTube video?"
```

Gemini does not use a persistent Assistant object here. The OptiBot system prompt and File Search tool are passed on each `generate_content` call.

## Modules

- `scraper/zendesk_client.py`: fetches article data from the Zendesk Help Center API.
- `scraper/markdown_converter.py`: converts Zendesk article HTML into clean Markdown files.
- `scraper/frontmatter.py`: parses generated Markdown frontmatter for upload metadata.
- `uploader/file_search_store.py`: creates/reuses a Gemini File Search store and uploads Markdown files.
- `query_assistant.py`: sends manual test questions to Gemini using the uploaded File Search store.
- `data/articles/`: stores generated Markdown article files. Markdown output is git-ignored.
- `data/state.json`: reserved for future delta detection.
- `main.py`: orchestrates scrape, convert, upload, ID persistence, and logging.

Delta detection is still planned for a later implementation step.
