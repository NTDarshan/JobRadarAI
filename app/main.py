from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.ai.analyzer import analyze_jobs
from app.ai.llm_client import FallbackLLMClient, LLMClient
from app.collectors.remote_boards import collect_remote_board_jobs
from app.collectors.tavily_search import search_trusted_job_boards
from app.config.settings import PROJECT_ROOT, load_candidate_profile, load_job_sources, load_settings
from app.email.email_sender import send_job_digest_email
from app.email.template import render_job_digest_html
from app.services.briefing import build_daily_briefing
from app.services.deduplication import deduplicate_jobs
from app.services.filtering import filter_jobs
from app.services.seen_store import SeenJobStore
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


async def _collect_all_jobs(settings, sources) -> list:
    search_jobs, board_jobs = await asyncio.gather(
        search_trusted_job_boards(settings.tavily_api_key, sources.search),
        collect_remote_board_jobs(sources.remote_boards, settings.max_jobs_per_source),
    )
    return search_jobs + board_jobs


def run() -> int:
    configure_logging()
    logger.info("Starting JobRadar AI")

    logger.info("Loading configuration")
    settings = load_settings()
    profile = load_candidate_profile()
    sources = load_job_sources()

    logger.info("Searching trusted job boards and remote job APIs")
    jobs = asyncio.run(_collect_all_jobs(settings, sources))
    logger.info("Found %d job postings", len(jobs))
    if not jobs:
        logger.error("No job postings were collected from any source. Aborting.")
        return 1

    deduped = deduplicate_jobs(jobs)
    logger.info("Deduplicated to %d job postings", len(deduped))

    filtered = filter_jobs(deduped, settings.max_jobs_per_source)
    logger.info("Filtered to %d job postings", len(filtered))

    store_path = Path(settings.seen_store_path)
    if not store_path.is_absolute():
        store_path = PROJECT_ROOT / store_path
    seen_store = SeenJobStore(store_path)
    seen_store.prune_older_than(settings.seen_jobs_retention_days)

    unseen = seen_store.filter_unseen(filtered)
    if not unseen:
        logger.info("No new job postings since the last run — nothing to analyze or send today.")
        return 0

    candidates = unseen[: settings.max_ai_jobs]
    logger.info("Sending %d job postings to AI for fit analysis", len(candidates))

    openai_client = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
    groq_client = LLMClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        base_url=_GROQ_BASE_URL,
        use_responses_api=False,
    )
    client = FallbackLLMClient(openai_client, "OpenAI", groq_client, "Groq")

    analyzed = analyze_jobs(client, candidates, profile)
    if not analyzed:
        logger.error("AI analysis produced no usable results. Aborting.")
        return 1
    logger.info("AI analysis completed")

    # Mark only successfully analyzed jobs as seen — a job whose analysis failed
    # (e.g. both LLM providers down) should still be retried on the next run.
    seen_store.mark_seen([a.job for a in analyzed])

    sources_checked = [board.name for board in sources.remote_boards] + (
        ["Trusted-site web search (Tavily)"] if settings.tavily_api_key else []
    )

    logger.info("Generating job digest")
    briefing = build_daily_briefing(
        analyzed_jobs=analyzed,
        sources_checked=sources_checked,
        total_jobs_found=len(jobs),
        total_after_dedup=len(deduped),
        min_match_score=settings.min_match_score,
        top_matches_count=settings.top_matches_count,
    )
    html = render_job_digest_html(briefing)

    logger.info("Sending email")
    try:
        send_job_digest_email(
            html_body=html,
            host=settings.email_host,
            port=settings.email_port,
            username=settings.email_username,
            password=settings.email_password,
            from_address=settings.email_from,
            to_address=settings.email_to,
        )
    except Exception:
        logger.error("Email delivery failed")
        return 1

    logger.info("Job digest sent successfully")
    logger.info("Completed")
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
