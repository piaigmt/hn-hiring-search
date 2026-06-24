"""Fetch and parse Hacker News 'Who is Hiring?' threads via Algolia API."""
from __future__ import annotations

import re
import httpx
from dataclasses import dataclass
ALGOLIA_STORY = "https://hn.algolia.com/api/v1/search_by_date"
ALGOLIA_COMMENTS = "https://hn.algolia.com/api/v1/items/{item_id}"

HIRING_RE = re.compile(r"^Ask HN:\s*Who is hiring\?", re.IGNORECASE)


@dataclass
class Job:
    text: str
    author: str
    created_at: str
    hn_url: str
    keywords_matched: list[str] | None = None


async def find_hiring_threads(client: httpx.AsyncClient, months: int = 3) -> list[dict]:
    """Find recent 'Ask HN: Who is Hiring?' story IDs."""
    results = []
    # Search by query for "Who is Hiring"
    r = await client.get(ALGOLIA_STORY, params={"query": "Ask HN: Who is Hiring", "hitsPerPage": 20})
    if r.status_code != 200:
        return results
    hits = r.json().get("hits", [])
    for hit in hits:
        title = hit.get("title", "")
        if HIRING_RE.search(title):
            results.append({
                "id": hit["objectID"],
                "title": title,
                "url": hit.get("url", ""),
                "created_at": hit.get("created_at", ""),
            })
    return results


async def fetch_comments(client: httpx.AsyncClient, story_id: str) -> list[Job]:
    """Fetch all top-level comments (job posts) from a hiring thread."""
    r = await client.get(ALGOLIA_COMMENTS.format(item_id=story_id), timeout=30)
    if r.status_code != 200:
        return []
    data = r.json()
    jobs: list[Job] = []
    for child in data.get("children", []):
        text = child.get("text", "")
        if not text:
            continue
        jobs.append(Job(
            text=text,
            author=child.get("author", ""),
            created_at=child.get("created_at", ""),
            hn_url=f"https://news.ycombinator.com/item?id={child.get('id', '')}",
        ))
    return jobs


def filter_jobs(jobs: list[Job], *, query: str = "", location: str = "", remote: bool = False, onsite: bool = False) -> list[Job]:
    """Filter job posts by keyword, location, and remote/onsite."""
    results = []
    q_lower = query.lower() if query else ""
    loc_lower = location.lower() if location else ""

    for job in jobs:
        text_lower = job.text.lower()

        if q_lower and q_lower not in text_lower:
            continue

        if loc_lower and loc_lower not in text_lower:
            continue

        if remote and "remote" not in text_lower:
            continue

        if onsite and "on-site" not in text_lower and "onsite" not in text_lower and "in office" not in text_lower and "in-office" not in text_lower:
            continue

        results.append(job)

    return results