"""Prompt construction for the review engine.

Builds a (system, user) message pair: the system prompt pins the reviewer persona, the
rubric, and the exact JSON schema the model must return; the user prompt carries the PR
metadata, each changed file's diff, and the RAG-retrieved surrounding code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import FindingCategory, Severity
from app.modules.search.vector_store import SearchHit

_SEVERITIES = ", ".join(s.value for s in Severity)
_CATEGORIES = ", ".join(c.value for c in FindingCategory)

SYSTEM_PROMPT = f"""\
You are a meticulous senior software engineer reviewing a GitHub pull request.
Review ONLY the changes shown in the diffs; use the surrounding repository context
to understand them. Find concrete issues: bugs, security vulnerabilities (injection,
XSS, secrets, unsafe deserialization), performance problems, missing edge cases,
duplication, and maintainability/complexity concerns. Do not invent problems — if a
change is clean, return few or no findings and high scores.

Return ONLY a JSON object (no markdown, no commentary) with exactly this shape:
{{
  "summary": "<2-4 sentence executive summary of the PR's quality>",
  "quality_score": <0-100>,
  "security_score": <0-100>,
  "complexity_score": <0-100>,
  "maintainability_score": <0-100>,
  "performance_score": <0-100>,
  "findings": [
    {{
      "file_path": "<path exactly as shown in the diff>",
      "line_start": <int or null>,
      "line_end": <int or null>,
      "severity": "<one of: {_SEVERITIES}>",
      "category": "<one of: {_CATEGORIES}>",
      "title": "<short problem title>",
      "rationale": "<why this is a problem>",
      "impact": "<what could go wrong, or null>",
      "suggestion": "<concrete fix, or null>",
      "confidence": <number 0.0-1.0>
    }}
  ]
}}
Scores are 0-100 (100 = excellent). Base line numbers on the added lines in the diff.\
"""


@dataclass
class FileForReview:
    filename: str
    status: str
    patch: str
    context: list[SearchHit] = field(default_factory=list)


def _format_context(hits: list[SearchHit]) -> str:
    if not hits:
        return "(no related code retrieved)"
    blocks = [
        f"--- {h.file_path}:{h.start_line}-{h.end_line} (similarity {h.score:.2f}) ---\n{h.content}"
        for h in hits
    ]
    return "\n\n".join(blocks)


def build_user_prompt(
    *, pr_title: str, pr_body: str | None, files: list[FileForReview]
) -> str:
    parts: list[str] = [f"Pull request: {pr_title}"]
    if pr_body:
        parts.append(f"Description:\n{pr_body.strip()}")

    for f in files:
        parts.append(
            f"\n===== FILE: {f.filename} ({f.status}) =====\n"
            f"Diff:\n{f.patch}\n\n"
            f"Related existing code (for context):\n{_format_context(f.context)}"
        )

    parts.append(
        "\nReview the changes above and return the JSON object described in the system prompt."
    )
    return "\n".join(parts)
