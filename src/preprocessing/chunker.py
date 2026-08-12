"""
src/preprocessing/chunker.py
-----------------------------
Splits repository source files into overlapping token chunks
for embedding and retrieval.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class CodeChunk:
    repo_id: str
    file_path: str
    language: str
    content: str
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)


def chunk_file(
    file_path: str,
    repo_id: str,
    chunk_size: int = 256,
    chunk_overlap: int = 32,
    language: str = "python",
) -> List[CodeChunk]:
    """
    Naïve line-based chunker.
    Replace with a tree-sitter AST chunker for better boundaries.
    """
    path = Path(file_path)
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    chunks: List[CodeChunk] = []
    step = max(1, chunk_size - chunk_overlap)
    i = 0
    while i < len(lines):
        window = lines[i: i + chunk_size]
        chunks.append(
            CodeChunk(
                repo_id=repo_id,
                file_path=str(path),
                language=language,
                content="\n".join(window),
                start_line=i,
                end_line=i + len(window) - 1,
            )
        )
        i += step
    return chunks


def chunk_repository(
    repo_root: str,
    repo_id: str,
    extensions: tuple = (".py",),
    chunk_size: int = 256,
    chunk_overlap: int = 32,
) -> List[CodeChunk]:
    """Walk a repository directory and chunk every matching source file."""
    root = Path(repo_root)
    all_chunks: List[CodeChunk] = []
    for fp in root.rglob("*"):
        if fp.suffix in extensions and fp.is_file():
            all_chunks.extend(
                chunk_file(
                    str(fp),
                    repo_id=repo_id,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            )
    return all_chunks

