"""FastAPI app for HN Hiring Search."""
from __future__ import annotations

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .hn_api import find_hiring_threads, fetch_comments, filter_jobs, Job

app = FastAPI(title="HN Hiring Search", description="Search Hacker News 'Who is Hiring?' threads")

# In-memory cache
_cache: dict[str, list[Job]] = {}
_cache_keys: list[str] = []

_static = Path(__file__).parent.parent / "static"
_templates = Path(__file__).parent.parent / "templates"

if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Search UI."""
    html = (_templates / "index.html").read_text() if (_templates / "index.html").exists() else "<h1>HN Hiring Search</h1>"
    return HTMLResponse(html)


@app.get("/api/search")
async def search(
    q: str = Query("", description="Keyword search"),
    location: str = Query("", description="Location filter"),
    remote: bool = Query(False, description="Remote only"),
    onsite: bool = Query(False, description="On-site only"),
    threads: int = Query(3, description="Number of recent hiring threads to search (1-6)", ge=1, le=6),
):
    """Search HN hiring threads. Returns JSON."""
    cache_key = f"{threads}"

    async with httpx.AsyncClient(timeout=30) as client:
        hiring_threads = await find_hiring_threads(client, months=3)

        if not hiring_threads:
            return JSONResponse({"results": [], "error": "No hiring threads found"})

        all_jobs: list[Job] = []
        for thread in hiring_threads[:threads]:
            tid = thread["id"]
            if tid in _cache:
                all_jobs.extend(_cache[tid])
            else:
                jobs = await fetch_comments(client, tid)
                _cache[tid] = jobs
                _cache_keys.append(tid)
                # Keep cache under 6 threads
                if len(_cache_keys) > 6:
                    old = _cache_keys.pop(0)
                    _cache.pop(old, None)
                all_jobs.extend(jobs)

    filtered = filter_jobs(all_jobs, query=q, location=location, remote=remote, onsite=onsite)

    return {
        "count": len(filtered),
        "thread_titles": [t["title"] for t in hiring_threads[:threads]],
        "results": [
            {
                "text": job.text[:2000],
                "author": job.author,
                "hn_url": job.hn_url,
            }
            for job in filtered[:100]
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)