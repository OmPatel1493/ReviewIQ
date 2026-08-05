"""Unit tests for the review engine's pure logic — parsing the LLM output and
building the prompt. No DB, GitHub, Qdrant, or Ollama required."""

from __future__ import annotations

import json

import pytest

from app.models.enums import FindingCategory, Severity
from app.modules.review.prompt import (
    SYSTEM_PROMPT,
    FileForReview,
    build_user_prompt,
)
from app.modules.review.service import ReviewService
from app.modules.search.vector_store import SearchHit


def _payload(**overrides: object) -> str:
    base = {
        "summary": "Reasonable change with one risk.",
        "quality_score": 80,
        "security_score": 60,
        "complexity_score": 75,
        "maintainability_score": 70,
        "performance_score": 90,
        "findings": [],
    }
    base.update(overrides)
    return json.dumps(base)


def test_parse_clamps_scores_and_normalises_enums() -> None:
    raw = _payload(
        quality_score=150,  # → 100
        security_score=-5,  # → 0
        findings=[
            {
                "file_path": "auth.py",
                "severity": "HIGH",  # uppercase → normalised
                "category": "Security",
                "title": "SQL injection",
                "rationale": "string-built query",
                "confidence": 2.0,  # → clamped to 1.0
            }
        ],
    )

    result = ReviewService._parse(raw)

    assert result.quality_score == 100
    assert result.security_score == 0
    assert len(result.findings) == 1
    assert result.findings[0].severity is Severity.HIGH
    assert result.findings[0].category is FindingCategory.SECURITY
    assert result.findings[0].confidence == 1.0


def test_parse_skips_malformed_findings_but_keeps_good_ones() -> None:
    raw = _payload(
        findings=[
            {  # invalid severity → dropped
                "file_path": "a.py",
                "severity": "nonsense",
                "category": "bug",
                "title": "x",
                "rationale": "y",
            },
            {  # valid → kept
                "file_path": "b.py",
                "severity": "low",
                "category": "bug",
                "title": "ok",
                "rationale": "why",
            },
        ]
    )

    result = ReviewService._parse(raw)

    assert [f.file_path for f in result.findings] == ["b.py"]


def test_parse_rejects_non_json() -> None:
    with pytest.raises(ValueError):
        ReviewService._parse("not json {")


def test_system_prompt_enumerates_categories_and_severities() -> None:
    assert "security" in SYSTEM_PROMPT
    assert "critical" in SYSTEM_PROMPT
    assert "JSON object" in SYSTEM_PROMPT


def test_build_user_prompt_includes_diff_and_context() -> None:
    files = [
        FileForReview(
            filename="auth/jwt.py",
            status="modified",
            patch="@@ -1,2 +1,3 @@\n+token = decode(x)",
            context=[SearchHit("auth/jwt.py", 1, 10, "def decode(x): ...", 0.91)],
        )
    ]

    prompt = build_user_prompt(pr_title="Add JWT", pr_body="adds auth", files=files)

    assert "Add JWT" in prompt
    assert "auth/jwt.py" in prompt
    assert "token = decode(x)" in prompt
    assert "def decode(x): ..." in prompt  # retrieved context is embedded
