"""Generate tailored outreach packets from live HN hiring posts.

This is not a search UI. It pulls real HN jobs and drafts concrete outbound
messages for piaigmt automation/data tooling services.
"""
from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

import httpx

from .hn_api import fetch_comments, filter_jobs, find_hiring_threads

CAPABILITIES = [
    "Python automation and CLI tools",
    "FastAPI web apps and JSON APIs",
    "data cleanup, scraping, and pipeline repair",
    "LLM-context tooling and repo summarization",
    "small, self-contained deliverables with runnable receipts",
]


def clean_html(text: str) -> str:
    text = re.sub(r"<p>|<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def infer_fit(text: str) -> list[str]:
    t = text.lower()
    fits = []
    if any(k in t for k in ["python", "fastapi", "django", "flask", "backend"]):
        fits.append("backend Python/API automation")
    if any(k in t for k in ["data", "etl", "pipeline", "scraping", "crawler", "analytics"]):
        fits.append("data pipeline / scraping cleanup")
    if any(k in t for k in ["llm", "ai", "agent", "rag", "prompt"]):
        fits.append("LLM workflow tooling")
    if any(k in t for k in ["ops", "cron", "monitor", "workflow", "internal tools"]):
        fits.append("internal tool automation")
    return fits or ["small automation deliverable"]


def extract_contacts(text: str) -> dict:
    clean = clean_html(text)
    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", clean)))
    urls = sorted(set(re.findall(r"https?://[^\s)\]<>]+", clean)))
    return {"emails": emails, "urls": urls}


def draft_pitch(job_text: str, hn_url: str) -> str:
    clean = clean_html(job_text)
    company_line = clean.splitlines()[0][:120] if clean else "your HN hiring post"
    fit = infer_fit(clean)
    return f"""Subject: Small automation/API help for {company_line}

Hi — saw your HN hiring post: {hn_url}

The part that looks relevant to me: {', '.join(fit)}.

I build small, evidence-first Python/FastAPI/data tooling deliverables under the piaigmt identity. Recent public receipts:
- git-context: repo summaries for LLM workflows — https://github.com/piaigmt/git-context
- hn-hiring-search: HN hiring search API/UI — https://github.com/piaigmt/hn-hiring-search
- meal-prep-automator: live recipe API → grocery/prep plan — https://github.com/piaigmt/meal-prep-automator

If you have a messy internal process, scrape, one-off admin tool, or API glue task, I can usually turn it into a runnable artifact first and discuss after the receipt exists.

Contact: piaigmt@proton.me
Portfolio: https://piaigmt.github.io
"""


async def build_packets(query: str, remote: bool, limit: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        threads = await find_hiring_threads(client)
        jobs = []
        for thread in threads[:2]:
            jobs.extend(await fetch_comments(client, thread["id"]))
    filtered = filter_jobs(jobs, query=query, remote=remote)
    packets = []
    for job in filtered[:limit]:
        packets.append({
            "hn_url": job.hn_url,
            "author": job.author,
            "fit": infer_fit(clean_html(job.text)),
            "contacts": extract_contacts(job.text),
            "excerpt": clean_html(job.text)[:700],
            "pitch": draft_pitch(job.text, job.hn_url),
        })
    return packets


def render_markdown(packets: list[dict]) -> str:
    out = ["# HN Outreach Packets", ""]
    for i, p in enumerate(packets, 1):
        contacts = p.get("contacts", {})
        contact_line = ""
        if contacts.get("emails"):
            contact_line += "**Emails:** " + ", ".join(contacts["emails"]) + "\n\n"
        if contacts.get("urls"):
            contact_line += "**URLs:** " + ", ".join(contacts["urls"][:3]) + "\n\n"
        out += [f"## {i}. {p['hn_url']}", "", f"**Fit:** {', '.join(p['fit'])}", "", contact_line.rstrip(), "", "**Excerpt:**", "", p["excerpt"], "", "**Pitch:**", "", "```", p["pitch"].strip(), "```", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="python")
    ap.add_argument("--remote", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default="outreach_packets.md")
    args = ap.parse_args()
    packets = asyncio.run(build_packets(args.query, args.remote, args.limit))
    Path(args.out).write_text(render_markdown(packets))
    print(f"wrote {len(packets)} packets to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
