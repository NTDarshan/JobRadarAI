"""All prompt text lives here, kept out of the calling code."""

from __future__ import annotations

import json

from app.domain.models import CandidateProfile, JobPosting

_SHARED_GROUND_RULES = """
Ground rules:
- Do not hallucinate or invent facts. Only use information present in the job posting text.
- If the company name is not clearly stated in the text, return an empty string for it — never guess.
- Always preserve the posting's original URL exactly as given.
- Be concise and specific. Avoid generic filler language.
- Judge seniority honestly: if the posting clearly requires years of professional experience this
  candidate does not have, say so in seniority_fit and concerns, even if the skills otherwise overlap.
- Only recommend an action when the posting genuinely justifies one.
""".strip()


def _profile_block(profile: CandidateProfile) -> str:
    return json.dumps(profile.model_dump(), indent=2)


def build_job_analysis_prompt(job: JobPosting, profile: CandidateProfile) -> str:
    return f"""
You are a precise, honest career-fit analyst helping one specific fresher candidate decide which
job postings are worth applying to today.

Candidate profile:
{_profile_block(profile)}

{_SHARED_GROUND_RULES}

Scoring task:
- match_score (0-100): overall fit, combining skill overlap, role-level appropriateness for a
  fresher, and alignment with the candidate's target roles and location/work-mode preferences.
  A posting that requires 3+ years of experience should score low even if the tech stack matches
  perfectly — seniority mismatch is disqualifying, not a minor deduction.
- seniority_fit: true only if a fresher with one internship could realistically apply and be
  considered.
- matched_skills: skills from the candidate's profile that this posting explicitly wants.
- missing_skills: skills/requirements this posting wants that are not in the candidate's profile.
- confidence: how confident you are, given the amount of usable text in the posting.

Analysis task:
- company_name: the hiring company's name if stated in the text, else an empty string.
- why_good_fit: 1-3 sentences grounded in the posting content.
- concerns: anything that should give the candidate pause (seniority mismatch, unclear location,
  visa/eligibility requirements, suspicious posting, etc.), or an empty string if there are none.
- recommended_action: a concrete next step (e.g. "Apply today — strong match", "Read the JD
  fully before applying — some ambiguity on experience required"), or an empty string if this
  posting is not worth pursuing.

Job posting:
title: {job.title}
company (as scraped, may be blank or unreliable): {job.company}
location: {job.location}
url: {job.url}
source: {job.source}
description:
{job.description[:4000]}

Respond with structured output matching the required schema. The "url" field must equal the
posting url above exactly.
""".strip()
