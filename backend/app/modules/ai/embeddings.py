"""Embedding providers.

An embedding turns text/code into a vector so that semantically similar things land
near each other. We hide the concrete model behind an `EmbeddingProvider` interface so
the pipeline never imports a vendor SDK directly — swapping local ↔ OpenAI is a config
change (`EMBEDDING_PROVIDER`).

Local default: **fastembed** (by Qdrant) running **BAAI/bge-small-en-v1.5** via ONNX.
It's CPU-friendly, needs no GPU/torch, and is free — ideal for a local-first build. The
model is loaded lazily (first `embed` call) so importing this module is cheap.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

from app.core.config import get_settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding

settings = get_settings()


class EmbeddingProvider(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalFastEmbedProvider:
    """Local ONNX embeddings via fastembed."""

    def __init__(self, model_name: str, dimension: int) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model: TextEmbedding | None = None

    def _ensure_model(self) -> TextEmbedding:
        if self._model is None:
            from fastembed import TextEmbedding

            # Downloads the model on first use (cached under ~/.cache afterwards).
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        return [
            vector.tolist()
            for vector in model.embed(texts, batch_size=settings.EMBED_BATCH_SIZE)
        ]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Process-wide singleton so the model is loaded at most once."""
    if settings.EMBEDDING_PROVIDER == "openai":
        raise NotImplementedError(
            "OpenAI embeddings are pluggable but not wired (local-first). "
            "Set EMBEDDING_PROVIDER=local."
        )
    return LocalFastEmbedProvider(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)
