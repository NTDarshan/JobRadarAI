from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.domain.models import CandidateProfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class SearchConfig(BaseModel):
    provider: str = "tavily"
    queries: list[str] = Field(default_factory=list)
    trusted_domains: list[str] = Field(default_factory=list)
    max_results_per_query: int = 10


class RemoteBoardConfig(BaseModel):
    name: str
    kind: str
    url: str


class JobSourcesConfig(BaseModel):
    search: SearchConfig
    remote_boards: list[RemoteBoardConfig] = Field(default_factory=list)


class Settings(BaseModel):
    openai_api_key: str
    openai_model: str
    groq_api_key: str
    groq_model: str
    tavily_api_key: str

    email_host: str
    email_port: int
    email_username: str
    email_password: str
    email_from: str
    email_to: str

    max_jobs_per_source: int
    max_ai_jobs: int
    min_match_score: int
    top_matches_count: int

    seen_store_path: str
    seen_jobs_retention_days: int


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        tavily_api_key=os.environ.get("TAVILY_API_KEY", ""),
        email_host=os.environ.get("EMAIL_HOST", ""),
        email_port=int(os.environ.get("EMAIL_PORT", "587")),
        email_username=os.environ.get("EMAIL_USERNAME", ""),
        email_password=os.environ.get("EMAIL_PASSWORD", ""),
        email_from=os.environ.get("EMAIL_FROM", ""),
        email_to=os.environ.get("EMAIL_TO", ""),
        max_jobs_per_source=int(os.environ.get("MAX_JOBS_PER_SOURCE", "40")),
        max_ai_jobs=int(os.environ.get("MAX_AI_JOBS", "40")),
        min_match_score=int(os.environ.get("MIN_MATCH_SCORE", "90")),
        top_matches_count=int(os.environ.get("TOP_MATCHES_COUNT", "5")),
        seen_store_path=os.environ.get("SEEN_STORE_PATH", "data/seen_jobs.db"),
        seen_jobs_retention_days=int(os.environ.get("SEEN_JOBS_RETENTION_DAYS", "60")),
    )


def load_candidate_profile(path: Path = CONFIG_DIR / "candidate_profile.yaml") -> CandidateProfile:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return CandidateProfile(**raw["candidate"])


def load_job_sources(path: Path = CONFIG_DIR / "job_sources.yaml") -> JobSourcesConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return JobSourcesConfig(**raw)
