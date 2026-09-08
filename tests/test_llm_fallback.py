from pydantic import BaseModel

from app.ai.llm_client import FallbackLLMClient, is_quota_exhausted_error


class DummySchema(BaseModel):
    value: str


class StubClient:
    def __init__(self, responses=None, error=None):
        self._responses = responses or []
        self._error = error
        self.calls = 0

    def generate_structured(self, system_prompt, user_prompt, schema):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)


def test_is_quota_exhausted_error_detects_known_markers():
    assert is_quota_exhausted_error(Exception("insufficient_quota"))
    assert is_quota_exhausted_error(Exception("credit_balance_exhausted"))
    assert not is_quota_exhausted_error(Exception("some other error"))


def test_fallback_uses_primary_when_it_succeeds():
    primary = StubClient(responses=[DummySchema(value="from-openai")])
    secondary = StubClient(responses=[DummySchema(value="from-groq")])
    client = FallbackLLMClient(primary, "OpenAI", secondary, "Groq")

    result = client.generate_structured("sys", "user", DummySchema)

    assert result.value == "from-openai"
    assert primary.calls == 1
    assert secondary.calls == 0


def test_fallback_switches_to_secondary_on_quota_error():
    primary = StubClient(error=Exception("insufficient_quota"))
    secondary = StubClient(responses=[DummySchema(value="from-groq")])
    client = FallbackLLMClient(primary, "OpenAI", secondary, "Groq")

    result = client.generate_structured("sys", "user", DummySchema)

    assert result.value == "from-groq"
    assert client._use_secondary is True


def test_fallback_stays_on_secondary_for_subsequent_calls():
    primary = StubClient(error=Exception("insufficient_quota"))
    secondary = StubClient(responses=[DummySchema(value="first"), DummySchema(value="second")])
    client = FallbackLLMClient(primary, "OpenAI", secondary, "Groq")

    client.generate_structured("sys", "user", DummySchema)
    client.generate_structured("sys", "user", DummySchema)

    assert primary.calls == 1
    assert secondary.calls == 2


def test_fallback_reraises_non_quota_errors():
    primary = StubClient(error=RuntimeError("network blip"))
    secondary = StubClient(responses=[DummySchema(value="unused")])
    client = FallbackLLMClient(primary, "OpenAI", secondary, "Groq")

    try:
        client.generate_structured("sys", "user", DummySchema)
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass
    assert secondary.calls == 0
