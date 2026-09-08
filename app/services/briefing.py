from __future__ import annotations

from datetime import date

from app.domain.models import AnalyzedJob, DailyJobBriefing
from app.services.ranking import rank_jobs, select_matches


def build_daily_briefing(
    analyzed_jobs: list[AnalyzedJob],
    sources_checked: list[str],
    total_jobs_found: int,
    total_after_dedup: int,
    min_match_score: int,
    top_matches_count: int,
    briefing_date: date | None = None,
) -> DailyJobBriefing:
    ranked = rank_jobs(analyzed_jobs)
    top_matches, all_matches, used_fallback = select_matches(ranked, min_match_score, top_matches_count)

    return DailyJobBriefing(
        date=(briefing_date or date.today()).isoformat(),
        top_matches=top_matches,
        all_matches=all_matches,
        sources_checked=sources_checked,
        total_jobs_found=total_jobs_found,
        total_after_dedup=total_after_dedup,
        below_threshold_fallback=used_fallback,
    )
