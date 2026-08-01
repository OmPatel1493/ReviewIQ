"""Chunker unit tests — pure logic, no DB/Qdrant/model."""

from __future__ import annotations

from pathlib import Path

from app.modules.indexing.chunker import chunk_text, iter_source_files


def test_chunks_cover_all_lines_with_overlap() -> None:
    text = "\n".join(f"line{i}" for i in range(1, 26))  # 25 lines
    chunks = chunk_text("f.py", text, max_lines=10, overlap=2)

    # step = 10 - 2 = 8 → windows start at lines 1, 9, 17, 25
    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 10), (9, 18), (17, 25)]
    # overlap: line 9 appears in both the first and second chunk
    assert "line9" in chunks[0].content and "line9" in chunks[1].content
    # every line is covered
    covered = {i for c in chunks for i in range(c.start_line, c.end_line + 1)}
    assert covered == set(range(1, 26))


def test_short_file_is_one_chunk() -> None:
    chunks = chunk_text("f.py", "a\nb\nc", max_lines=60, overlap=10)
    assert len(chunks) == 1
    assert (chunks[0].start_line, chunks[0].end_line) == (1, 3)


def test_whitespace_only_text_yields_no_chunks() -> None:
    assert chunk_text("f.py", "   \n\n  \n") == []


def test_content_hash_is_stable_and_content_sensitive() -> None:
    a = chunk_text("f.py", "x = 1\ny = 2", max_lines=60)[0]
    b = chunk_text("f.py", "x = 1\ny = 2", max_lines=60)[0]
    c = chunk_text("f.py", "x = 1\ny = 3", max_lines=60)[0]
    assert a.content_hash == b.content_hash
    assert a.content_hash != c.content_hash


def test_iter_source_files_filters_by_extension_and_dir(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("print('hi')\n")
    (tmp_path / "skip.png").write_text("not source\n")
    (tmp_path / "empty.py").write_text("")
    vendored = tmp_path / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "index.js").write_text("module.exports = 1\n")

    found = {rel for rel, _ in iter_source_files(tmp_path)}
    assert found == {"keep.py"}  # .png excluded, empty skipped, node_modules excluded
