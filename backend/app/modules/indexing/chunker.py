"""Split source files into overlapping chunks for embedding.

We use a line-based sliding window with overlap. It's language-agnostic and simple,
and the overlap keeps a function that straddles a boundary from being cut in half.
(A future upgrade is AST-aware chunking via tree-sitter so chunks align to function/
class boundaries — noted for later.)
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class Chunk:
    file_path: str  # repo-relative
    content: str
    start_line: int  # 1-indexed, inclusive
    end_line: int

    @property
    def content_hash(self) -> str:
        """SHA-256 of the chunk — used to skip re-embedding unchanged code."""
        return hashlib.sha256(self.content.encode("utf-8", "ignore")).hexdigest()


def chunk_text(
    file_path: str,
    text: str,
    *,
    max_lines: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    max_lines = max_lines or settings.CHUNK_MAX_LINES
    overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP_LINES
    step = max(1, max_lines - overlap)

    lines = text.splitlines()
    n = len(lines)
    chunks: list[Chunk] = []
    i = 0
    while i < n:
        window = lines[i : i + max_lines]
        raw = "\n".join(window)
        if raw.strip():  # skip whitespace-only windows
            chunks.append(
                Chunk(
                    file_path=file_path,
                    content=raw,
                    start_line=i + 1,
                    end_line=min(i + max_lines, n),
                )
            )
        if i + max_lines >= n:
            break
        i += step
    return chunks


def iter_source_files(root: Path) -> Iterator[tuple[str, str]]:
    """Yield `(relative_path, text)` for indexable source files under `root`,
    skipping excluded dirs, non-source extensions, and oversized/binary files."""
    include = settings.index_include_extensions
    exclude = settings.index_exclude_dirs
    max_bytes = settings.INDEX_MAX_FILE_BYTES

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in exclude for part in rel.parts):
            continue
        if path.suffix.lower() not in include:
            continue
        try:
            if path.stat().st_size > max_bytes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if text.strip():
            yield (str(rel), text)
