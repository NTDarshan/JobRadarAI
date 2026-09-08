from app.domain.models import JobPosting
from app.services.deduplication import deduplicate_jobs
from app.utils.text import normalize_text, normalize_url


def make_job(title: str, url: str, company: str = "Acme") -> JobPosting:
    return JobPosting(title=title, company=company, url=url, source="Test Source", description="x" * 100)


def test_normalize_url_strips_tracking_params():
    a = normalize_url("https://example.com/job?utm_source=twitter&id=1")
    b = normalize_url("https://example.com/job?id=1")
    assert a == b


def test_normalize_text_ignores_punctuation_and_case():
    assert normalize_text("Backend Engineer!") == normalize_text("backend engineer")


def test_deduplicate_exact_url_duplicates():
    jobs = [
        make_job("Backend Engineer", "https://example.com/a"),
        make_job("Backend Engineer", "https://example.com/a?utm_source=rss"),
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 1


def test_deduplicate_near_identical_title_and_company():
    jobs = [
        make_job("Full Stack Developer", "https://a.com/1", company="Acme Corp"),
        make_job("Full Stack Developer!", "https://b.com/1", company="Acme Corp"),
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 1


def test_deduplicate_keeps_distinct_jobs():
    jobs = [
        make_job("Backend Engineer", "https://a.com/1", company="Acme"),
        make_job("Frontend Engineer", "https://b.com/2", company="Globex"),
    ]
    result = deduplicate_jobs(jobs)
    assert len(result) == 2
