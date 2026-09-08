from app.config.settings import CONFIG_DIR, load_candidate_profile, load_job_sources, load_settings


def test_load_candidate_profile_from_yaml():
    profile = load_candidate_profile(CONFIG_DIR / "candidate_profile.yaml")
    assert "Full-Stack Developer" in profile.target_roles
    assert "Node.js" in profile.skills.get("backend", [])
    assert profile.education


def test_load_job_sources_from_yaml():
    sources = load_job_sources(CONFIG_DIR / "job_sources.yaml")
    assert len(sources.search.queries) > 0
    assert "linkedin.com" in sources.search.trusted_domains
    assert len(sources.remote_boards) >= 4
    assert all(board.url.startswith("http") for board in sources.remote_boards)


def test_load_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("EMAIL_HOST", "smtp.test.com")
    monkeypatch.setenv("EMAIL_PORT", "587")
    monkeypatch.setenv("EMAIL_USERNAME", "user")
    monkeypatch.setenv("EMAIL_PASSWORD", "pass")
    monkeypatch.setenv("EMAIL_FROM", "from@test.com")
    monkeypatch.setenv("EMAIL_TO", "to@test.com")
    monkeypatch.setenv("MIN_MATCH_SCORE", "90")

    settings = load_settings()
    assert settings.openai_api_key == "test-key"
    assert settings.groq_api_key == "test-groq-key"
    assert settings.min_match_score == 90
