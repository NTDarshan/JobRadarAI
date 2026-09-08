from __future__ import annotations

from app.domain.models import AnalyzedJob
from app.utils.logging import get_logger

logger = get_logger(__name__)


def rank_jobs(analyzed_jobs: list[AnalyzedJob]) -> list[AnalyzedJob]:
    ranked = sorted(analyzed_jobs, key=lambda a: a.match_score, reverse=True)
    logger.info("Ranked %d analyzed jobs", len(ranked))
    return ranked


def select_matches(
    ranked_jobs: list[AnalyzedJob], min_match_score: int, top_count: int
) -> tuple[list[AnalyzedJob], list[AnalyzedJob], bool]:
    """Return (top_matches, all_qualifying_matches, used_fallback).

    used_fallback is True when nothing met min_match_score, so the top N are
    shown anyway — the email must say clearly that these fall short of the bar.
    """
    qualifying = [a for a in ranked_jobs if a.match_score >= min_match_score]
    if qualifying:
        return qualifying[:top_count], qualifying, False

    fallback = ranked_jobs[:top_count]
    return fallback, fallback, True
