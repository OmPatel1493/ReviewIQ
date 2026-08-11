"""Prompt construction for Ask-AI.

Grounds the model in the retrieved code and tells it to say "I don't know" rather than
hallucinate when the context is insufficient.
"""

from __future__ import annotations

from app.modules.search.vector_store import SearchHit

SYSTEM_PROMPT = """\
You are a helpful senior engineer answering questions about a specific codebase.
Answer using ONLY the code context provided below. If the context does not contain
enough information to answer, say so plainly instead of guessing. Reference file paths
when relevant, keep the answer concise and concrete, and use markdown for any code.\
"""


def _format_sources(hits: list[SearchHit]) -> str:
    if not hits:
        return "(no relevant code was retrieved)"
    return "\n\n".join(
        f"--- {h.file_path}:{h.start_line}-{h.end_line} ---\n{h.content}" for h in hits
    )


def build_user_prompt(question: str, hits: list[SearchHit]) -> str:
    return (
        f"Question: {question}\n\n"
        f"Relevant code from the repository:\n{_format_sources(hits)}\n\n"
        "Answer the question using only the code above."
    )
