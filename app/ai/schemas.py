from __future__ import annotations

from pydantic import BaseModel, Field


class JobAnalysisResult(BaseModel):
    """Structured output the model returns for a single job posting's fit analysis."""

    url: str
    company_name: str = Field(description="Company name extracted from the posting, empty string if not identifiable")
    match_score: int = Field(ge=0, le=100)
    seniority_fit: bool = Field(description="True if this role is genuinely appropriate for a fresher/entry-level candidate")
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    why_good_fit: str
    concerns: str = Field(default="", description="Empty string if there are no real concerns")
    recommended_action: str
    confidence: int = Field(ge=0, le=100)
