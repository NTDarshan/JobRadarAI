from __future__ import annotations

from html import escape

from app.domain.models import AnalyzedJob, DailyJobBriefing

_COLORS = {
    "bg": "#0f1115",
    "card": "#ffffff",
    "text": "#1c1f26",
    "muted": "#5b6270",
    "accent": "#1a9c6b",
}


def _section(title: str, inner_html: str) -> str:
    if not inner_html.strip():
        return ""
    return f"""
<tr><td style="padding:28px 32px 4px 32px;">
  <h2 style="margin:0 0 12px 0;font-size:18px;color:{_COLORS['text']};">{escape(title)}</h2>
  {inner_html}
</td></tr>
""".strip()


def _job_card(item: AnalyzedJob, highlight: bool = False) -> str:
    border = _COLORS["accent"] if highlight else "#e5e7eb"
    bg = "#f0fbf6" if highlight else "#fafafa"
    missing = ", ".join(item.missing_skills) if item.missing_skills else "None notable"
    matched = ", ".join(item.matched_skills) if item.matched_skills else "—"
    concerns_html = (
        f'<p style="margin:0 0 6px 0;font-size:13px;color:#b45309;"><strong>Note:</strong> {escape(item.concerns)}</p>'
        if item.concerns
        else ""
    )
    location_bits = " · ".join(
        b for b in [item.job.location, str(item.job.work_mode.value) if item.job.work_mode else ""] if b
    )
    return f"""
<div style="border-left:4px solid {border};padding:12px 16px;margin-bottom:14px;background:{bg};border-radius:4px;">
  <p style="margin:0 0 4px 0;font-weight:600;color:{_COLORS['text']};">
    <a href="{escape(item.job.url)}" style="color:{_COLORS['text']};text-decoration:none;">{escape(item.job.title)}</a>
  </p>
  <p style="margin:0 0 6px 0;font-size:13px;color:{_COLORS['muted']};">{escape(item.display_company)}
    {" · " + escape(location_bits) if location_bits else ""} · via {escape(item.job.source)}</p>
  <p style="margin:0 0 6px 0;font-size:14px;color:{_COLORS['text']};">{escape(item.why_good_fit)}</p>
  <p style="margin:0 0 4px 0;font-size:13px;color:{_COLORS['text']};"><strong>Matched skills:</strong> {escape(matched)}</p>
  <p style="margin:0 0 6px 0;font-size:13px;color:{_COLORS['text']};"><strong>Gaps:</strong> {escape(missing)}</p>
  {concerns_html}
  <p style="margin:0 0 6px 0;font-size:13px;color:{_COLORS['text']};"><strong>Action:</strong> {escape(item.recommended_action)}</p>
  <p style="margin:0;font-size:12px;color:{_COLORS['muted']};">Match {item.match_score}/100 &middot;
    <a href="{escape(item.job.url)}" style="color:{_COLORS['accent']};">apply here</a></p>
</div>
""".strip()


def _jobs_html(items: list[AnalyzedJob], highlight: bool = False) -> str:
    return "\n".join(_job_card(item, highlight=highlight) for item in items)


def render_job_digest_html(briefing: DailyJobBriefing) -> str:
    top_urls = {item.job.url for item in briefing.top_matches}
    other_matches = [item for item in briefing.all_matches if item.job.url not in top_urls]

    fallback_html = (
        f"""<div style="padding:10px 16px;background:#fff7ed;border-left:3px solid #f59e0b;border-radius:4px;margin-bottom:14px;">
  <p style="margin:0;font-size:13px;color:{_COLORS['text']};">No posting reached the {escape(str(briefing.date))}
  target match bar today — showing the closest matches found instead so nothing is missed.</p>
</div>"""
        if briefing.below_threshold_fallback
        else ""
    )

    top_html = fallback_html + _jobs_html(briefing.top_matches, highlight=True)
    other_html = _jobs_html(other_matches)

    sources_html = "".join(
        f'<p style="margin:0 0 4px 0;font-size:12px;color:{_COLORS["muted"]};">{escape(s)}</p>'
        for s in briefing.sources_checked
    )

    return f"""
<!doctype html>
<html>
<body style="margin:0;padding:0;background:{_COLORS['bg']};font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_COLORS['bg']};padding:24px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:{_COLORS['card']};border-radius:8px;overflow:hidden;">
<tr><td style="padding:32px 32px 8px 32px;">
  <h1 style="margin:0;font-size:22px;color:{_COLORS['text']};">JobRadar AI</h1>
  <p style="margin:4px 0 0 0;color:{_COLORS['muted']};font-size:14px;">Your Daily Job Matches &middot; {escape(briefing.date)}</p>
  <p style="margin:8px 0 0 0;color:{_COLORS['muted']};font-size:12px;">
    {briefing.total_jobs_found} jobs found &middot; {briefing.total_after_dedup} after dedup &middot;
    {len(briefing.all_matches)} strong matches</p>
</td></tr>
{_section("🎯 Apply Today — Top Matches", top_html)}
{_section("📋 Other Strong Matches", other_html)}
{_section("Sources checked today", sources_html)}
<tr><td style="padding:20px 32px;">
  <p style="margin:0;font-size:11px;color:{_COLORS['muted']};">Generated automatically by JobRadar AI. Always verify a
  listing on the original site before applying.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
""".strip()
