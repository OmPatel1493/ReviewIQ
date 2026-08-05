"""Review use-case: RAG-retrieve context for a PR's diffs, ask an LLM for structured
findings + scores, and persist them.

The heavy work (GitHub fetch → retrieval → LLM) runs off-request in a Celery worker
(see app/workers). The request path only creates the Review + Job and returns 202.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Finding, PullRequest, Repository, Review, User
from app.modules.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.modules.ai.llm import LLMProvider, get_llm_provider
from app.modules.github.service import (
    GitHubService,
    RepositoryAccessError,
    RepositoryNotFoundError,
)
from app.modules.review.prompt import (
    SYSTEM_PROMPT,
    FileForReview,
    build_user_prompt,
)
from app.modules.review.schemas import LLMFinding, LLMReviewResult
from app.modules.search.vector_store import QdrantVectorStore, SearchHit
from app.repositories.finding_repository import FindingRepository
from app.repositories.review_repository import ReviewRepository

settings = get_settings()
logger = get_logger(__name__)

# Re-exported so the router catches ownership errors without importing the github module.
__all__ = ["RepositoryAccessError", "RepositoryNotFoundError", "ReviewService"]


class ReviewService:
    def __init__(
        self,
        db: AsyncSession,
        user: User,
        *,
        github: GitHubService | None = None,
        vector_store: QdrantVectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.user = user
        # Injected collaborators default to the real ones (tests pass fakes).
        self.gh = github or GitHubService(db, user)
        self.reviews = ReviewRepository(db)
        self.findings = FindingRepository(db)
        self.vs = vector_store or QdrantVectorStore()
        self.embedder = embedder or get_embedding_provider()
        self.llm = llm or get_llm_provider()

    # ----------------------------------------- request path (create + enqueue)
    async def create_pending_review(
        self, repo_id: uuid.UUID, pull_number: int
    ) -> tuple[Review, Repository]:
        """Verify ownership, ensure the PR row exists, and create a PENDING review."""
        repo = await self.gh.get_connected_repository(repo_id)  # raises 404/403
        pr = await self.gh.get_or_sync_pull_request(repo_id, pull_number)
        review = await self.reviews.create(pull_request_id=pr.id)
        return review, repo

    # ----------------------------------------------- worker path (do the work)
    async def run_review(self, review_id: uuid.UUID) -> dict[str, Any]:
        review = await self.reviews.get(review_id)
        if review is None:
            raise ValueError(f"review {review_id} not found")
        pr = await self.db.get(PullRequest, review.pull_request_id)
        if pr is None:
            raise ValueError("pull request row missing for review")
        repo = await self.db.get(Repository, pr.repository_id)
        if repo is None:
            raise ValueError("repository row missing for review")

        files = await self._collect_files(repo.id, pr.number)
        if not files:
            await self.reviews.mark_completed(
                review_id,
                summary="No reviewable text changes in this pull request.",
                quality_score=100,
                security_score=100,
                complexity_score=100,
                maintainability_score=100,
                performance_score=100,
                provider=self.llm.provider_name,
                model=self.llm.model,
                meta={"files_reviewed": 0},
            )
            return {"review_id": str(review_id), "files_reviewed": 0, "findings": 0}

        user_prompt = build_user_prompt(
            pr_title=pr.title or f"PR #{pr.number}", pr_body=pr.body, files=files
        )
        raw = await self.llm.generate_json(SYSTEM_PROMPT, user_prompt)
        result = self._parse(raw)

        rows = [self._to_row(review_id, f) for f in result.findings]
        await self.findings.bulk_insert(rows)
        await self.reviews.mark_completed(
            review_id,
            summary=result.summary,
            quality_score=result.quality_score,
            security_score=result.security_score,
            complexity_score=result.complexity_score,
            maintainability_score=result.maintainability_score,
            performance_score=result.performance_score,
            provider=self.llm.provider_name,
            model=self.llm.model,
            meta={"files_reviewed": len(files), "findings": len(rows)},
        )
        return {
            "review_id": str(review_id),
            "files_reviewed": len(files),
            "findings": len(rows),
        }

    # ------------------------------------------------------------- internals
    async def _collect_files(
        self, repo_id: uuid.UUID, pr_number: int
    ) -> list[FileForReview]:
        gh_files = await self.gh.get_pull_request_files(repo_id, pr_number)
        selected: list[FileForReview] = []
        for gf in gh_files:
            if gf.status == "removed" or not gf.patch:
                continue  # nothing to review (deletion or binary/huge file)
            patch = gf.patch[: settings.REVIEW_MAX_PATCH_CHARS]
            context = await self._retrieve_context(str(repo_id), gf.filename, patch)
            selected.append(
                FileForReview(
                    filename=gf.filename, status=gf.status, patch=patch, context=context
                )
            )
            if len(selected) >= settings.REVIEW_MAX_FILES:
                break
        return selected

    async def _retrieve_context(
        self, repo_id: str, filename: str, patch: str
    ) -> list[SearchHit]:
        vector = self.embedder.embed([f"{filename}\n{patch}"])[0]
        return await self.vs.search(repo_id, vector, settings.REVIEW_CONTEXT_TOP_K)

    @staticmethod
    def _parse(raw: str) -> LLMReviewResult:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON: {exc}") from exc
        # Validate findings one-by-one so a single malformed entry doesn't sink the review.
        findings_raw = data.pop("findings", []) or []
        result = LLMReviewResult.model_validate(data)
        for fr in findings_raw:
            try:
                result.findings.append(LLMFinding.model_validate(fr))
            except Exception:  # noqa: BLE001 — skip the bad finding, keep the good ones
                logger.warning("Skipping malformed finding from LLM: %r", fr)
        return result

    @staticmethod
    def _to_row(review_id: uuid.UUID, f: LLMFinding) -> Finding:
        return Finding(
            review_id=review_id,
            file_path=f.file_path[:1024],
            line_start=f.line_start,
            line_end=f.line_end,
            severity=f.severity,
            category=f.category,
            title=f.title[:512],
            rationale=f.rationale,
            impact=f.impact,
            suggestion=f.suggestion,
            confidence=f.confidence,
        )

    async def aclose(self) -> None:
        await self.vs.aclose()
