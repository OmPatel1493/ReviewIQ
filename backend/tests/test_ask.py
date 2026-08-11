"""Unit tests for Ask-AI: the service wiring (retrieve → prompt → LLM) with fakes,
and the prompt builder. No DB, Qdrant, or Ollama required."""

from __future__ import annotations

import uuid

from app.modules.ask.prompt import SYSTEM_PROMPT, build_user_prompt
from app.modules.ask.service import AskService
from app.modules.search.vector_store import SearchHit


class _FakeSearch:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits
        self.calls: list[tuple] = []

    async def search(self, repo_id: uuid.UUID, question: str, top_k: int) -> list[SearchHit]:
        self.calls.append((repo_id, question, top_k))
        return self._hits

    async def aclose(self) -> None:
        pass


class _FakeLLM:
    provider_name = "fake"
    model = "fake"

    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.prompts: list[tuple[str, str]] = []

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        self.prompts.append((system_prompt, user_prompt))
        return self._answer

    async def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        return "{}"


async def test_ask_retrieves_then_answers() -> None:
    hits = [SearchHit("auth/jwt.py", 1, 20, "def decode(t): ...", 0.88)]
    search = _FakeSearch(hits)
    llm = _FakeLLM("You should test decode() with an expired token.")
    svc = AskService(None, None, search=search, llm=llm)  # type: ignore[arg-type]

    repo_id = uuid.uuid4()
    answer, sources = await svc.ask(repo_id, "what tests should I write?", top_k=4)

    assert answer == "You should test decode() with an expired token."
    assert sources == hits
    # top_k is forwarded to retrieval, and the question reaches the LLM prompt.
    assert search.calls == [(repo_id, "what tests should I write?", 4)]
    assert "what tests should I write?" in llm.prompts[0][1]


def test_build_user_prompt_grounds_in_sources() -> None:
    hits = [SearchHit("db.py", 5, 9, "engine = create_engine()", 0.7)]
    prompt = build_user_prompt("where is the DB configured?", hits)
    assert "where is the DB configured?" in prompt
    assert "db.py" in prompt
    assert "engine = create_engine()" in prompt


def test_system_prompt_discourages_hallucination() -> None:
    assert "ONLY" in SYSTEM_PROMPT
    assert "does not contain" in SYSTEM_PROMPT
