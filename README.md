# HN Hiring Search

Search recent Hacker News **Ask HN: Who is Hiring?** threads by keyword, location, remote/onsite, and seniority.

## Why

HN hiring threads are high-signal but hard to search. This app pulls recent hiring threads from the HN Algolia API, parses top-level job comments, and gives you a clean search UI plus JSON API.

## Run locally

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
uvicorn src.app:app --reload
```

Open http://127.0.0.1:8000

## API

```bash
curl 'http://127.0.0.1:8000/api/search?q=python&remote=true&location=europe'
```

Response:

```json
{
  "count": 12,
  "thread_titles": ["Ask HN: Who is hiring? (June 2026)"],
  "results": [
    {"text": "...", "author": "...", "hn_url": "https://news.ycombinator.com/item?id=..."}
  ]
}
```

## Deploy

Designed for Render or any ASGI host:

```bash
uvicorn src.app:app --host 0.0.0.0 --port $PORT
```

## License

MIT