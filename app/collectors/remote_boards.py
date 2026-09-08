from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import mktime

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.config.settings import RemoteBoardConfig
from app.domain.enums import WorkMode
from app.domain.models import JobPosting
from app.utils.logging import get_logger

logger = get_logger(__name__)

_USER_AGENT = "JobRadarAI/1.0 (personal job search assistant)"
_TIMEOUT_SECONDS = 15.0
_MAX_RETRIES = 2


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "html.parser").get_text(separator=" ", strip=True)


def _parse_remoteok(payload: list, source: str, cap: int) -> list[JobPosting]:
    postings = []
    for entry in payload:
        if "position" not in entry:
            continue  # first element is RemoteOK's API-terms notice, not a job
        posted_at = None
        if entry.get("date"):
            try:
                posted_at = datetime.fromisoformat(entry["date"].replace("Z", "+00:00"))
            except ValueError:
                pass
        postings.append(
            JobPosting(
                title=entry.get("position", ""),
                company=entry.get("company", ""),
                location=entry.get("location", ""),
                url=entry.get("apply_url") or entry.get("url", ""),
                source=source,
                posted_at=posted_at,
                description=_strip_html(entry.get("description", "")),
                work_mode=WorkMode.REMOTE,
            )
        )
        if len(postings) >= cap:
            break
    return postings


def _parse_arbeitnow(payload: dict, source: str, cap: int) -> list[JobPosting]:
    postings = []
    for entry in payload.get("data", []):
        posted_at = None
        if entry.get("created_at"):
            try:
                posted_at = datetime.fromtimestamp(int(entry["created_at"]), tz=timezone.utc)
            except (ValueError, OSError):
                pass
        postings.append(
            JobPosting(
                title=entry.get("title", ""),
                company=entry.get("company_name", ""),
                location=entry.get("location", ""),
                url=entry.get("url", ""),
                source=source,
                posted_at=posted_at,
                description=_strip_html(entry.get("description", "")),
                work_mode=WorkMode.REMOTE if entry.get("remote") else WorkMode.UNKNOWN,
            )
        )
        if len(postings) >= cap:
            break
    return postings


def _parse_himalayas(payload: dict, source: str, cap: int) -> list[JobPosting]:
    postings = []
    for entry in payload.get("jobs", []):
        posted_at = None
        if entry.get("pubDate"):
            try:
                posted_at = datetime.fromtimestamp(int(entry["pubDate"]), tz=timezone.utc)
            except (ValueError, OSError, TypeError):
                pass
        location = entry.get("locationRestrictions") or []
        postings.append(
            JobPosting(
                title=entry.get("title", ""),
                company=entry.get("companyName", ""),
                location=", ".join(location) if isinstance(location, list) else str(location),
                url=entry.get("applicationLink") or entry.get("guid", ""),
                source=source,
                posted_at=posted_at,
                description=_strip_html(entry.get("description", "") or entry.get("excerpt", "")),
                work_mode=WorkMode.REMOTE,
            )
        )
        if len(postings) >= cap:
            break
    return postings


def _parse_jobicy(payload: dict, source: str, cap: int) -> list[JobPosting]:
    postings = []
    for entry in payload.get("jobs", []):
        posted_at = None
        if entry.get("pubDate"):
            try:
                posted_at = datetime.fromisoformat(entry["pubDate"].replace("Z", "+00:00"))
            except ValueError:
                pass
        postings.append(
            JobPosting(
                title=entry.get("jobTitle", ""),
                company=entry.get("companyName", ""),
                location=entry.get("jobGeo", ""),
                url=entry.get("url", ""),
                source=source,
                posted_at=posted_at,
                description=_strip_html(entry.get("jobDescription", "")),
                work_mode=WorkMode.REMOTE,
            )
        )
        if len(postings) >= cap:
            break
    return postings


def _parse_rss(body: str, source: str, cap: int) -> list[JobPosting]:
    parsed = feedparser.parse(body)
    postings = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue
        posted_at = None
        if entry.get("published_parsed"):
            posted_at = datetime.fromtimestamp(mktime(entry["published_parsed"]), tz=timezone.utc)
        postings.append(
            JobPosting(
                title=title,
                url=url,
                source=source,
                posted_at=posted_at,
                description=_strip_html(entry.get("summary", "")),
                work_mode=WorkMode.REMOTE,
            )
        )
        if len(postings) >= cap:
            break
    return postings


_PARSERS = {
    "remoteok": lambda body, source, cap: _parse_remoteok(body, source, cap),
    "arbeitnow": lambda body, source, cap: _parse_arbeitnow(body, source, cap),
    "himalayas": lambda body, source, cap: _parse_himalayas(body, source, cap),
    "jobicy": lambda body, source, cap: _parse_jobicy(body, source, cap),
}


async def _fetch_one(client: httpx.AsyncClient, board: RemoteBoardConfig, cap: int) -> list[JobPosting]:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = await client.get(
                board.url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT_SECONDS, follow_redirects=True
            )
            response.raise_for_status()
            break
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("Board fetch failed (attempt %d/%d) for %s: %s", attempt, _MAX_RETRIES, board.name, exc)
            if attempt == _MAX_RETRIES:
                logger.warning("Skipping board after repeated failures: %s", board.name)
                return []

    try:
        if board.kind == "rss":
            postings = _parse_rss(response.text, board.name, cap)
        else:
            parser = _PARSERS.get(board.kind)
            if parser is None:
                logger.warning("Unknown board kind '%s' for %s — skipping", board.kind, board.name)
                return []
            postings = parser(response.json(), board.name, cap)
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse response from %s: %s", board.name, exc)
        return []

    logger.info("Fetched %d jobs from %s", len(postings), board.name)
    return postings


async def collect_remote_board_jobs(boards: list[RemoteBoardConfig], cap_per_board: int) -> list[JobPosting]:
    """Fetch all remote job board APIs concurrently. A single board failure never aborts the run."""
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(_fetch_one(client, board, cap_per_board) for board in boards),
            return_exceptions=True,
        )

    postings: list[JobPosting] = []
    for board, result in zip(boards, results):
        if isinstance(result, Exception):
            logger.warning("Unexpected error collecting %s: %s", board.name, result)
            continue
        postings.extend(result)
    return postings
