"""Indexing use-case: turn a repository into a searchable vector index.

Pipeline: clone → walk source files → chunk → embed → upsert vectors into Qdrant +
persist chunk metadata in Postgres → mark the repo indexed. This is the retrieval
foundation that semantic search (Phase 5) and the review engine (Phase 6) build on.

It runs inside a Celery worker (see `app/workers`), off the request path, because
embedding a repo can take a while.
"""

from __future__ import annotations

import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import CodeChunk, Repository
from app.models.enums import IndexStatus
from app.modules.ai.embeddings import EmbeddingProvider, get_embedding_provider
from app.modules.indexing.chunker import Chunk, chunk_text, iter_source_files
from app.modules.indexing.cloner import clone_repository
from app.modules.search.vector_store import QdrantVectorStore, make_point
from app.repositories.code_chunk_repository import CodeChunkRepository
from app.repositories.repository_repository import RepositoryRepository

settings = get_settings()
logger = get_logger(__name__)

# Extension → language label for nicer search results / filtering.
_LANG_BY_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".java": "java", ".go": "go", ".rb": "ruby", ".rs": "rust",
    ".c": "c", ".cc": "cpp", ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".cs": "csharp",
    ".php": "php", ".kt": "kotlin", ".swift": "swift", ".scala": "scala", ".sh": "shell",
    ".sql": "sql", ".md": "markdown", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
}


def _language_for(file_path: str) -> str | None:
    return _LANG_BY_EXT.get(Path(file_path).suffix.lower())


class IndexingService:
    def __init__(
        self,
        db: AsyncSession,
        vector_store: QdrantVectorStore | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self.repos = RepositoryRepository(db)
        self.chunks = CodeChunkRepository(db)
        self.vs = vector_store or QdrantVectorStore()
        self.embedder = embedder or get_embedding_provider()

    async def index_repository(
        self, repo_id: uuid.UUID, *, token: str | None = None
    ) -> dict[str, Any]:
        """Clone the repo, index it, and update its status. Cleans up the clone."""
        repo = await self.repos.get(repo_id)
        if repo is None:
            raise ValueError(f"repository {repo_id} not found")

        repo.index_status = IndexStatus.INDEXING
        await self.db.flush()

        workdir = Path(settings.CLONE_DIR) / f"{repo.id}-{uuid.uuid4().hex[:8]}"
        try:
            clone_repository(repo.clone_url, token, workdir, ref=repo.default_branch)
            result = await self.index_path(repo, workdir)
            repo.index_status = IndexStatus.INDEXED
            repo.indexed_at = datetime.now(UTC)
            await self.db.flush()
            logger.info("Indexed %s: %s", repo.full_name, result)
            return result
        except Exception:
            repo.index_status = IndexStatus.FAILED
            await self.db.flush()
            raise
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def index_path(self, repo: Repository, root: Path) -> dict[str, Any]:
        """Index an already-available directory (the clone). Also used directly in
        tests, which bypass cloning."""
        await self.vs.ensure_collection()

        # 1) Collect chunks from every source file.
        all_chunks: list[Chunk] = []
        file_count = 0
        for rel_path, text in iter_source_files(root):
            file_count += 1
            all_chunks.extend(chunk_text(rel_path, text))

        # 2) Full re-index: clear this repo's previous chunks (DB + vectors).
        await self.chunks.delete_by_repo(repo.id)
        await self.vs.delete_by_repo(str(repo.id))

        # 3) Embed in batches and upsert to Qdrant + Postgres.
        batch_size = settings.EMBED_BATCH_SIZE
        rows: list[CodeChunk] = []
        for start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[start : start + batch_size]
            vectors = self.embedder.embed([c.content for c in batch])
            points = []
            for chunk, vector in zip(batch, vectors, strict=True):
                vector_id = uuid.uuid4()
                points.append(
                    make_point(
                        vector_id,
                        vector,
                        repo_id=str(repo.id),
                        file_path=chunk.file_path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                    )
                )
                rows.append(
                    CodeChunk(
                        repository_id=repo.id,
                        file_path=chunk.file_path,
                        language=_language_for(chunk.file_path),
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content_hash=chunk.content_hash,
                        vector_id=vector_id,
                    )
                )
            await self.vs.upsert(points)

        await self.chunks.bulk_insert(rows)
        await self.db.flush()
        return {"files_indexed": file_count, "chunks_indexed": len(all_chunks)}

    async def aclose(self) -> None:
        await self.vs.aclose()
