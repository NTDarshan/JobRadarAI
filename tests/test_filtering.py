from datetime import datetime, timedelta, timezone

from app.domain.models import JobPosting
from app.services.filtering import filter_jobs


def make_job(title: str, description: str, source: str = "Test", posted_at=None) -> JobPosting:
    return JobPosting(
        title=title,
        url=f"https://example.com/{title}",
        source=source,
        description=description,
        posted_at=posted_at or datetime.now(timezone.utc),
    )


def test_filter_removes_too_short_descriptions():
    jobs = [make_job("Backend Engineer", "too short")]
    assert filter_jobs(jobs, max_per_source=10) == []


def test_filter_removes_senior_titles():
    jobs = [make_job("Senior Backend Engineer", "x" * 100)]
    assert filter_jobs(jobs, max_per_source=10) == []


def test_filter_keeps_genuine_entry_level_jobs():
    jobs = [make_job("Backend Engineer (Fresher)", "x" * 100)]
    result = filter_jobs(jobs, max_per_source=10)
    assert len(result) == 1


def test_filter_caps_per_source_by_recency():
    now = datetime.now(timezone.utc)
    older = make_job("Older Role", "x" * 100, posted_at=now - timedelta(days=1))
    newer = make_job("Newer Role", "x" * 100, posted_at=now)
    result = filter_jobs([older, newer], max_per_source=1)
    assert len(result) == 1
    assert result[0].title == "Newer Role"


def test_filter_caps_independently_per_source():
    jobs = [
        make_job("Role A", "x" * 100, source="SourceA"),
        make_job("Role B", "x" * 100, source="SourceA"),
        make_job("Role C", "x" * 100, source="SourceB"),
    ]
    result = filter_jobs(jobs, max_per_source=1)
    sources = {job.source for job in result}
    assert len(result) == 2
    assert sources == {"SourceA", "SourceB"}
