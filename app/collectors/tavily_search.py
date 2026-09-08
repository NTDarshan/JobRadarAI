from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

import httpx

from app.config.settings import SearchConfig
from app.domain.models import JobPosting
from app.utils.logging import get_logger

logger = get_logger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"
_TIMEOUT_SECONDS = 20.0


def _source_name(url: str) -> str:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return host or "web search"


async def _run_query(client: httpx.AsyncClient, api_key: str, query: str, config: SearchConfig) -> list[JobPosting]:
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_domains": config.trusted_domains,
        "max_results": config.max_results_per_query,
        "include_raw_content": True,
    }
    try:
        response = await client.post(_TAVILY_URL, json=payload, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Tavily search failed for query '%s': %s", query, exc)
        return []

    postings: list[JobPosting] = []
    for result in data.get("results", []):
        url = result.get("url", "").strip()
        title = result.get("title", "").strip()
        if not url or not title:
            continue
        description = result.get("raw_content") or result.get("content") or ""
        postings.append(
            JobPosting(
                title=title,
                url=url,
                source=_source_name(url),
                description=description,
            )
        )
    logger.info("Tavily search '%s' returned %d results", query, len(postings))
    return postings


async def search_trusted_job_boards(api_key: str, config: SearchConfig) -> list[JobPosting]:
    """Search trusted job boards via Tavily. A single failed query never aborts the run."""
    if not api_key:
        logger.warning("TAVILY_API_KEY not set — skipping trusted-site job search")
        return []

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(_run_query(client, api_key, query, config) for query in config.queries),
            return_exceptions=True,
        )

    postings: list[JobPosting] = []
    for query, result in zip(config.queries, results):
        if isinstance(result, Exception):
            logger.warning("Unexpected error searching '%s': %s", query, result)
            continue
        postings.extend(result)
    return postings
