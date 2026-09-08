from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.utils.logging import get_logger

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)

_QUOTA_ERROR_MARKERS = ("insufficient_quota", "credit_balance_exhausted", "exceeded your current quota")


class LLMClient:
    """Thin wrapper isolating all LLM SDK usage behind structured-output calls.

    Also accepts any OpenAI-compatible endpoint (e.g. Groq) via base_url. Those
    providers implement the chat completions contract but not OpenAI's newer
    Responses API, so use_responses_api selects which one to call.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        use_responses_api: bool = True,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        self._model = model
        self._use_responses_api = use_responses_api

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[ModelT]) -> ModelT:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if self._use_responses_api:
            response = self._client.responses.parse(model=self._model, input=messages, text_format=schema)
            parsed = response.output_parsed
        else:
            completion = self._client.chat.completions.parse(
                model=self._model, messages=messages, response_format=schema
            )
            parsed = completion.choices[0].message.parsed

        if parsed is None:
            raise RuntimeError(f"LLM returned no parsable structured output for schema {schema.__name__}")
        return parsed


def is_quota_exhausted_error(exc: Exception) -> bool:
    message = str(exc)
    return any(marker in message for marker in _QUOTA_ERROR_MARKERS)


class FallbackLLMClient:
    """Tries the primary client first; once it hits a quota/credits error, switches to the
    secondary client for the rest of the process run rather than retrying a dead primary
    on every subsequent call."""

    def __init__(self, primary: LLMClient, primary_name: str, secondary: LLMClient, secondary_name: str) -> None:
        self._primary = primary
        self._primary_name = primary_name
        self._secondary = secondary
        self._secondary_name = secondary_name
        self._use_secondary = False

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[ModelT]) -> ModelT:
        if not self._use_secondary:
            try:
                return self._primary.generate_structured(system_prompt, user_prompt, schema)
            except Exception as exc:
                if not is_quota_exhausted_error(exc):
                    raise
                logger.warning(
                    "%s quota/credits exhausted — switching to %s for the rest of this run: %s",
                    self._primary_name,
                    self._secondary_name,
                    exc,
                )
                self._use_secondary = True

        return self._secondary.generate_structured(system_prompt, user_prompt, schema)
