from src.rag.chunking import MarkdownCodeChunker


def test_chunk_knowledge_dir():
    chunker = MarkdownCodeChunker()
    chunks = chunker.chunk_directory("data/knowledge")
    assert len(chunks) > 5, "Should have at least 5 chunks from pandas patterns"
    assert all(c.text for c in chunks), "All chunks should have text"
    assert all(c.metadata.get("title") for c in chunks), "All chunks should have titles"


def test_chunk_has_code():
    chunker = MarkdownCodeChunker()
    chunks = chunker.chunk_directory("data/knowledge")
    code_chunks = [c for c in chunks if "```python" in c.text or "pd." in c.text]
    assert len(code_chunks) > 3, "Most chunks should contain Python code"
