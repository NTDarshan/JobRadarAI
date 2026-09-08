from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import WorkMode


class JobPosting(BaseModel):
    title: str = Field(min_length=1)
    company: str = ""
    location: str = ""
    url: str = Field(min_length=1)
    source: str
    posted_at: datetime | None = None
    description: str = ""
    work_mode: WorkMode = WorkMode.UNKNOWN
    salary_text: str = ""


class CandidateProfile(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    experience_level: str = ""
    location_preference: list[str] = Field(default_factory=list)
    work_mode_preference: list[str] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    strongest_areas: list[str] = Field(default_factory=list)
    highlighted_experience: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    education: str = ""
    links: dict[str, str] = Field(default_factory=dict)


class AnalyzedJob(BaseModel):
    job: JobPosting
    company_name: str = ""
    match_score: int = Field(ge=0, le=100)
    seniority_fit: bool
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    why_good_fit: str
    concerns: str = ""
    recommended_action: str
    confidence: int = Field(ge=0, le=100)

    @property
    def display_company(self) -> str:
        return self.company_name or self.job.company or "Unknown company"


class DailyJobBriefing(BaseModel):
    date: str
    top_matches: list[AnalyzedJob]
    all_matches: list[AnalyzedJob]
    sources_checked: list[str]
    total_jobs_found: int
    total_after_dedup: int
    below_threshold_fallback: bool = False
