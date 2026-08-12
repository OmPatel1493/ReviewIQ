"""LLM providers.

Mirrors the embeddings module: the concrete chat model lives behind an `LLMProvider`
interface so the review engine never imports a vendor SDK — swapping local ↔ OpenAI is
a config change (`AI_PROVIDER`). Local default is **Ollama** (e.g. `qwen2.5-coder`),
which is free and runs on the developer's machine.

Providers return the model's **raw JSON string**; the review service validates it with
Pydantic. We ask for JSON mode so the model is constrained to emit parseable output.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings

settings = get_settings()


class LLMError(Exception):
    """The LLM backend was unreachable or returned an error/empty response."""


class LLMProvider(Protocol):
    provider_name: str
    model: str

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str: ...

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str: ...


class OllamaProvider:
    """Local chat completion via Ollama's REST API (`POST /api/chat`, JSON mode).

    An `httpx.AsyncClient` can be injected for tests (via `httpx.MockTransport`);
    otherwise a client is created per call.
    """

    provider_name = "ollama"

    def __init__(
        self, base_url: str, model: str, client: httpx.AsyncClient | None = None
    ) -> None:
        self.model = model
        self._base = base_url.rstrip("/")
        self._client = client

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        """Chat completion constrained to valid JSON (for the review engine)."""
        return await self._chat(system_prompt, user_prompt, json_mode=True)

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Free-text chat completion (for Ask-AI)."""
        return await self._chat(system_prompt, user_prompt, json_mode=False)

    async def _chat(
        self, system_prompt: str, user_prompt: str, *, json_mode: bool
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},  # low temp = more deterministic output
        }
        if json_mode:
            payload["format"] = "json"  # constrain output to valid JSON

        url = f"{self._base}/api/chat"
        try:
            if self._client is not None:
                resp = await self._client.post(url, json=payload)
            else:
                async with httpx.AsyncClient(
                    timeout=settings.REVIEW_TIMEOUT_SECONDS
                ) as client:
                    resp = await client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach Ollama at {self._base}: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMError(f"Ollama returned {resp.status_code}: {resp.text[:500]}")

        content = resp.json().get("message", {}).get("content", "")
        if not content:
            raise LLMError("Ollama returned an empty response.")
        return content


class OpenAICompatibleProvider:
    """Chat completion via any OpenAI-compatible API (OpenAI, Groq, OpenRouter, Together).

    This is the deploy path: a 7B local model can't run on free hosting, so point
    `AI_PROVIDER=openai` at a free hosted endpoint (e.g. Groq) with a base URL + key +
    model. An `httpx.AsyncClient` can be injected for tests.
    """

    provider_name = "openai"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        return await self._chat(system_prompt, user_prompt, json_mode=True)

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        return await self._chat(system_prompt, user_prompt, json_mode=False)

    async def _chat(
        self, system_prompt: str, user_prompt: str, *, json_mode: bool
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{self._base}/chat/completions"
        try:
            if self._client is not None:
                resp = await self._client.post(url, json=payload, headers=headers)
            else:
                async with httpx.AsyncClient(
                    timeout=settings.REVIEW_TIMEOUT_SECONDS
                ) as client:
                    resp = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach the LLM API at {self._base}: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMError(f"LLM API returned {resp.status_code}: {resp.text[:500]}")

        choices = resp.json().get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        if not content:
            raise LLMError("LLM API returned an empty response.")
        return content


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Process-wide singleton LLM provider selected by `AI_PROVIDER`."""
    if settings.AI_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            raise NotImplementedError(
                "AI_PROVIDER=openai needs OPENAI_API_KEY (+ OPENAI_BASE_URL / OPENAI_MODEL). "
                "For a free hosted LLM, use Groq: OPENAI_BASE_URL=https://api.groq.com/openai/v1"
            )
        return OpenAICompatibleProvider(
            settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY, settings.OPENAI_MODEL
        )
    return OllamaProvider(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
