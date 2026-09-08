from app.domain.models import AnalyzedJob, JobPosting
from app.services.ranking import rank_jobs, select_matches


def make_analyzed(title: str, match_score: int) -> AnalyzedJob:
    job = JobPosting(title=title, url=f"https://example.com/{title}", source="Test", description="x" * 100)
    return AnalyzedJob(
        job=job,
        match_score=match_score,
        seniority_fit=True,
        matched_skills=["Python"],
        missing_skills=[],
        why_good_fit="Good fit",
        recommended_action="Apply",
        confidence=80,
    )


def test_rank_jobs_orders_by_match_score_descending():
    low = make_analyzed("Low", 40)
    high = make_analyzed("High", 95)
    ranked = rank_jobs([low, high])
    assert ranked[0].job.title == "High"
    assert ranked[1].job.title == "Low"


def test_select_matches_returns_qualifying_jobs_without_fallback():
    jobs = [make_analyzed("A", 95), make_analyzed("B", 60), make_analyzed("C", 92)]
    top, all_matches, used_fallback = select_matches(rank_jobs(jobs), min_match_score=90, top_count=5)
    assert used_fallback is False
    assert {j.job.title for j in all_matches} == {"A", "C"}
    assert top[0].job.title == "A"


def test_select_matches_falls_back_when_nothing_qualifies():
    jobs = [make_analyzed("A", 50), make_analyzed("B", 60)]
    top, all_matches, used_fallback = select_matches(rank_jobs(jobs), min_match_score=90, top_count=5)
    assert used_fallback is True
    assert len(top) == 2
    assert top[0].job.title == "B"


def test_select_matches_respects_top_count():
    jobs = [make_analyzed(f"J{i}", 95) for i in range(5)]
    top, all_matches, used_fallback = select_matches(rank_jobs(jobs), min_match_score=90, top_count=2)
    assert len(top) == 2
    assert len(all_matches) == 5
