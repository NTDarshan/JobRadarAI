from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.domain.models import JobPosting
from app.utils.logging import get_logger
from app.utils.text import normalize_url

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    url_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    source TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
)
"""


class SeenJobStore:
    """Tracks which job postings have already been analyzed, so re-runs (and the next
    day's run) skip them instead of re-spending an AI call and re-emailing the same job.

    Backed by a small SQLite file. On GitHub Actions this file must be committed back
    to the repo after each run (see .github/workflows/daily_job_search.yml) — a runner
    is a fresh disposable VM, so anything not persisted back to git is lost when it ends.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def filter_unseen(self, jobs: list[JobPosting]) -> list[JobPosting]:
        with closing(sqlite3.connect(self._db_path)) as conn:
            rows = conn.execute("SELECT url_key FROM seen_jobs").fetchall()
        seen_keys = {row[0] for row in rows}

        unseen = [job for job in jobs if normalize_url(job.url) not in seen_keys]
        logger.info("%d of %d jobs are new (not previously seen)", len(unseen), len(jobs))
        return unseen

    def mark_seen(self, jobs: list[JobPosting]) -> None:
        if not jobs:
            return
        now = datetime.now(timezone.utc).isoformat()
        rows = [(normalize_url(job.url), job.title, job.company, job.source, now) for job in jobs]
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO seen_jobs (url_key, title, company, source, first_seen_at) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
        logger.info("Recorded %d jobs as seen", len(rows))

    def prune_older_than(self, days: int) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with closing(sqlite3.connect(self._db_path)) as conn:
            cursor = conn.execute("DELETE FROM seen_jobs WHERE first_seen_at < ?", (cutoff,))
            conn.commit()
        if cursor.rowcount:
            logger.info("Pruned %d seen-job records older than %d days", cursor.rowcount, days)
