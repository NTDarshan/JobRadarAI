from __future__ import annotations

from app.domain.models import JobPosting
from app.utils.logging import get_logger
from app.utils.text import normalize_text, normalize_url, text_similarity

logger = get_logger(__name__)

_TITLE_SIMILARITY_THRESHOLD = 0.90


def _composite_key(job: JobPosting) -> str:
    return normalize_text(f"{job.title} {job.company}")


def deduplicate_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    """Drop exact URL duplicates and near-identical title+company postings, keeping the first seen."""
    seen_urls: set[str] = set()
    seen_composites: set[str] = set()
    kept: list[JobPosting] = []

    for job in jobs:
        url_key = normalize_url(job.url)
        composite_key = _composite_key(job)

        if url_key in seen_urls or composite_key in seen_composites:
            continue

        if any(
            text_similarity(f"{job.title} {job.company}", f"{other.title} {other.company}")
            >= _TITLE_SIMILARITY_THRESHOLD
            for other in kept
        ):
            continue

        seen_urls.add(url_key)
        seen_composites.add(composite_key)
        kept.append(job)

    logger.info("Deduplicated %d jobs down to %d", len(jobs), len(kept))
    return kept
