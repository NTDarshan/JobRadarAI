import pytest
from pydantic import ValidationError

from app.domain.models import AnalyzedJob, JobPosting


def test_job_posting_requires_title_and_url():
    with pytest.raises(ValidationError):
        JobPosting(title="", url="", source="Test")


def test_analyzed_job_rejects_out_of_range_match_score():
    job = JobPosting(title="T", url="https://example.com/1", source="Test")
    with pytest.raises(ValidationError):
        AnalyzedJob(
            job=job,
            match_score=150,
            seniority_fit=True,
            why_good_fit="w",
            recommended_action="a",
            confidence=50,
        )


def test_analyzed_job_display_company_falls_back_to_scraped_company():
    job = JobPosting(title="T", url="https://example.com/1", source="Test", company="Acme")
    analyzed = AnalyzedJob(
        job=job,
        company_name="",
        match_score=80,
        seniority_fit=True,
        why_good_fit="w",
        recommended_action="a",
        confidence=50,
    )
    assert analyzed.display_company == "Acme"


def test_analyzed_job_display_company_prefers_ai_extracted_name():
    job = JobPosting(title="T", url="https://example.com/1", source="Test", company="")
    analyzed = AnalyzedJob(
        job=job,
        company_name="Acme Corp",
        match_score=80,
        seniority_fit=True,
        why_good_fit="w",
        recommended_action="a",
        confidence=50,
    )
    assert analyzed.display_company == "Acme Corp"
