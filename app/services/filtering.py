from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from app.domain.models import JobPosting
from app.utils.logging import get_logger

logger = get_logger(__name__)

_MIN_DESCRIPTION_LENGTH = 60

# A fresher won't be a fit for these regardless of skill overlap — filter deterministically
# rather than spending an AI call establishing what the title already makes obvious.
_SENIOR_TITLE_MARKERS = (
    "senior",
    "sr.",
    "staff",
    "principal",
    "lead ",
    "architect",
    "manager",
    "director",
    "head of",
    "10+ years",
    "8+ years",
    "5+ years",
)


def _is_too_short(job: JobPosting) -> bool:
    return len(job.description) < _MIN_DESCRIPTION_LENGTH


def _looks_senior(job: JobPosting) -> bool:
    haystack = job.title.lower()
    return any(marker in haystack for marker in _SENIOR_TITLE_MARKERS)


def filter_jobs(jobs: list[JobPosting], max_per_source: int) -> list[JobPosting]:
    """Remove postings a fresher clearly can't use, then cap volume per source by recency."""
    filtered = [job for job in jobs if not _is_too_short(job) and not _looks_senior(job)]

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    filtered.sort(key=lambda j: j.posted_at or epoch, reverse=True)

    capped: list[JobPosting] = []
    per_source_count: dict[str, int] = defaultdict(int)
    for job in filtered:
        if per_source_count[job.source] >= max_per_source:
            continue
        per_source_count[job.source] += 1
        capped.append(job)

    logger.info("Filtered %d jobs down to %d", len(jobs), len(capped))
    return capped
