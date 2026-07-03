# Support Content Assistant

Initial scaffold for a support-content assistant that will scrape Zendesk Help Center articles, convert article bodies to Markdown, detect daily deltas, and upload changed content to an OpenAI vector store.

## Folder Structure

```text
.
├── scraper/
│   ├── __init__.py
│   ├── zendesk_client.py
│   └── markdown_converter.py
├── uploader/
│   ├── __init__.py
│   └── vector_store.py
├── data/
│   ├── articles/
│   └── state.json
├── main.py
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

Then fill in the values in `.env`.

## Modules

- `scraper/zendesk_client.py`: will fetch article data from the Zendesk Help Center API.
- `scraper/markdown_converter.py`: will convert Zendesk article HTML into clean Markdown files.
- `uploader/vector_store.py`: will upload generated Markdown files to an OpenAI vector store.
- `data/articles/`: stores generated Markdown article files. Markdown output is git-ignored.
- `data/state.json`: stores sync metadata for delta detection.
- `main.py`: will orchestrate scrape, convert, delta detection, upload, and logging.

Business logic is intentionally not implemented yet. Functions currently contain docstrings describing their intended responsibilities.
