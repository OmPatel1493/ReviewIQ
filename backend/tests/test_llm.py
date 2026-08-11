"""OllamaProvider unit tests using httpx.MockTransport — no Ollama server needed."""

from __future__ import annotations

import json

import httpx
import pytest

from app.modules.ai.llm import LLMError, OllamaProvider


def _provider(handler: object) -> OllamaProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return OllamaProvider("http://ollama:11434", "qwen2.5-coder:7b", client=client)


async def test_generate_json_posts_chat_and_returns_content() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"summary": "ok"}'}})

    out = await _provider(handler).generate_json("system", "user")

    assert out == '{"summary": "ok"}'
    assert seen["path"] == "/api/chat"
    assert seen["body"]["format"] == "json"  # JSON mode requested
    assert seen["body"]["stream"] is False
    assert seen["body"]["messages"][0]["role"] == "system"


async def test_generate_text_omits_json_format() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "plain answer"}})

    out = await _provider(handler).generate_text("system", "user")

    assert out == "plain answer"
    assert "format" not in seen["body"]  # free-text mode, not JSON-constrained


async def test_generate_json_raises_on_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="model overloaded")

    with pytest.raises(LLMError):
        await _provider(handler).generate_json("s", "u")


async def test_generate_json_raises_on_empty_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": ""}})

    with pytest.raises(LLMError):
        await _provider(handler).generate_json("s", "u")
