# Support Content Assistant

Scrapes Zendesk Help Center articles from OptiSigns, converts article bodies to Markdown, and uploads only new or changed documents to a Google Gemini File Search store for RAG-style support answers.

## Folder Structure

```text
.
|-- scraper/
|   |-- __init__.py
|   |-- zendesk_client.py
|   |-- markdown_converter.py
|   |-- frontmatter.py
|   `-- state_tracker.py
|-- uploader/
|   |-- __init__.py
|   `-- file_search_store.py
|-- data/
|   |-- articles/
|   |-- ids.json
|   `-- state.json
|-- .github/workflows/daily-sync.yml
|-- main.py
|-- query_assistant.py
|-- requirements.txt
|-- Dockerfile
`-- README.md
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

## Delta Sync

`data/state.json` stores each article ID with its content hash, Markdown slug, and Gemini File Search document resource name. Each run:

- Fetches all current Zendesk articles.
- Hashes the raw article HTML body.
- Classifies articles as added, updated, or skipped.
- Deletes the previous Gemini document for updated articles.
- Uploads only added and updated Markdown files.
- Saves the new document names back to `data/state.json`.

## Run Locally

Run without Docker:

```powershell
python main.py
```

Run with Docker:

```powershell
docker build -t optibot-sync .
docker run --rm -e GEMINI_API_KEY=... -e ZENDESK_SUBDOMAIN=support.optisigns.com optibot-sync
```

To persist `data/state.json` and `data/ids.json` across Docker runs, mount the local data directory:

```powershell
docker run --rm -v ${PWD}/data:/app/data -e GEMINI_API_KEY=... -e ZENDESK_SUBDOMAIN=support.optisigns.com optibot-sync
```

## Query OptiBot

After `main.py` has uploaded at least one article, ask a test question:

```powershell
python query_assistant.py "How do I add a YouTube video?"
```

Gemini does not use a persistent Assistant object here. The OptiBot system prompt and File Search tool are passed on each `generate_content` call.

## GitHub Actions

The daily sync workflow is in `.github/workflows/daily-sync.yml`.

Set repository secrets in GitHub:

1. Open the repo on GitHub.
2. Go to `Settings > Secrets and variables > Actions`.
3. Add `GEMINI_API_KEY`.
4. Add `ZENDESK_SUBDOMAIN` with `support.optisigns.com`.

The workflow runs daily at `03:00 UTC` and can also be triggered manually from the repo's `Actions` tab using `workflow_dispatch`. Job logs are available from the same `Actions` tab by opening a workflow run.

The workflow caches `data/state.json` and `data/ids.json` between runs so delta detection does not reset every day.

## Modules

- `scraper/zendesk_client.py`: fetches article data from the Zendesk Help Center API.
- `scraper/markdown_converter.py`: converts Zendesk article HTML into clean Markdown files.
- `scraper/frontmatter.py`: parses generated Markdown frontmatter for upload metadata.
- `scraper/state_tracker.py`: loads state, computes content hashes, and classifies article deltas.
- `uploader/file_search_store.py`: creates/reuses a Gemini File Search store, uploads Markdown files, and deletes stale documents.
- `query_assistant.py`: sends manual test questions to Gemini using the uploaded File Search store.
- `main.py`: orchestrates scrape, delta detection, conversion, upload, ID persistence, and logging.
