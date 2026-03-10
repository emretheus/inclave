from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import re


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict


class MarkdownCodeChunker:
    """Splits markdown files into chunks by ## headers.
    Each chunk = one section with its code blocks."""

    def chunk_file(self, file_path: str | Path) -> list[Chunk]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        sections = re.split(r'\n(?=## )', content)

        chunks = []
        for i, section in enumerate(sections):
            section = section.strip()
            if not section or len(section) < 20:
                continue

            # Extract title from first line
            title_match = re.match(r'## (.+)', section)
            title = title_match.group(1) if title_match else f"section_{i}"

            chunks.append(Chunk(
                id=f"{path.stem}_{i}_{title.lower().replace(' ', '_')[:40]}",
                text=section,
                metadata={
                    "source": path.name,
                    "title": title,
                    "chunk_index": i,
                },
            ))
        return chunks

    def chunk_directory(self, dir_path: str | Path) -> list[Chunk]:
        """Chunk all markdown files in a directory."""
        all_chunks = []
        for md_file in Path(dir_path).glob("*.md"):
            all_chunks.extend(self.chunk_file(md_file))
        return all_chunks