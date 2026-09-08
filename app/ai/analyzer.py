from __future__ import annotations

import time

from app.ai.llm_client import FallbackLLMClient
from app.ai.prompts import build_job_analysis_prompt
from app.ai.schemas import JobAnalysisResult
from app.domain.models import AnalyzedJob, CandidateProfile, JobPosting
from app.utils.logging import get_logger

logger = get_logger(__name__)

_ANALYSIS_SYSTEM_PROMPT = "You are a precise, honest, factual career-fit analyst. Never invent information."
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2.0


def _call_with_retry(client: FallbackLLMClient, system_prompt: str, user_prompt: str, schema):
    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return client.generate_structured(system_prompt, user_prompt, schema)
        except Exception as exc:
            last_error = exc
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts: {last_error}") from last_error


def analyze_jobs(
    client: FallbackLLMClient,
    jobs: list[JobPosting],
    profile: CandidateProfile,
) -> list[AnalyzedJob]:
    """Score and analyze each job posting. A single posting's failure is skipped, not fatal."""
    analyzed: list[AnalyzedJob] = []
    for job in jobs:
        try:
            prompt = build_job_analysis_prompt(job, profile)
            result: JobAnalysisResult = _call_with_retry(client, _ANALYSIS_SYSTEM_PROMPT, prompt, JobAnalysisResult)
        except RuntimeError as exc:
            logger.warning("Skipping job after repeated analysis failures: %s (%s)", job.url, exc)
            continue

        analyzed.append(
            AnalyzedJob(
                job=job,
                company_name=result.company_name,
                match_score=result.match_score,
                seniority_fit=result.seniority_fit,
                matched_skills=result.matched_skills,
                missing_skills=result.missing_skills,
                why_good_fit=result.why_good_fit,
                concerns=result.concerns,
                recommended_action=result.recommended_action,
                confidence=result.confidence,
            )
        )

    logger.info("AI analysis completed for %d/%d jobs", len(analyzed), len(jobs))
    return analyzed
