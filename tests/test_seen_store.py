from datetime import datetime, timedelta, timezone

from app.domain.models import JobPosting
from app.services.seen_store import SeenJobStore


def make_job(title: str, url: str) -> JobPosting:
    return JobPosting(title=title, url=url, source="Test", description="x" * 100)


def test_filter_unseen_returns_all_jobs_on_first_run(tmp_path):
    store = SeenJobStore(tmp_path / "seen.db")
    jobs = [make_job("A", "https://example.com/a"), make_job("B", "https://example.com/b")]

    assert store.filter_unseen(jobs) == jobs


def test_marked_jobs_are_excluded_on_next_filter(tmp_path):
    store = SeenJobStore(tmp_path / "seen.db")
    job_a = make_job("A", "https://example.com/a")
    job_b = make_job("B", "https://example.com/b")

    store.mark_seen([job_a])
    remaining = store.filter_unseen([job_a, job_b])

    assert remaining == [job_b]


def test_filter_unseen_normalizes_urls_before_comparing(tmp_path):
    store = SeenJobStore(tmp_path / "seen.db")
    store.mark_seen([make_job("A", "https://example.com/a?utm_source=rss")])

    remaining = store.filter_unseen([make_job("A", "https://example.com/a/")])

    assert remaining == []


def test_mark_seen_is_idempotent(tmp_path):
    store = SeenJobStore(tmp_path / "seen.db")
    job = make_job("A", "https://example.com/a")

    store.mark_seen([job])
    store.mark_seen([job])  # should not raise or duplicate

    assert store.filter_unseen([job]) == []


def test_store_persists_across_instances(tmp_path):
    db_path = tmp_path / "seen.db"
    SeenJobStore(db_path).mark_seen([make_job("A", "https://example.com/a")])

    reopened = SeenJobStore(db_path)
    assert reopened.filter_unseen([make_job("A", "https://example.com/a")]) == []


def test_prune_older_than_removes_stale_entries(tmp_path, monkeypatch):
    db_path = tmp_path / "seen.db"
    store = SeenJobStore(db_path)
    job = make_job("A", "https://example.com/a")
    store.mark_seen([job])

    # Backdate the entry so it falls outside the retention window.
    import sqlite3

    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE seen_jobs SET first_seen_at = ?", (old_timestamp,))
        conn.commit()

    store.prune_older_than(60)

    assert store.filter_unseen([job]) == [job]
