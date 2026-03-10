from __future__ import annotations
from src.vectordb.store import VectorStore


class KnowledgeRetriever:
    """Retrieves relevant knowledge chunks for a given query."""

    def __init__(self):
        self.store = VectorStore(collection_name="knowledge")

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.3) -> str:
        """
        Search for relevant chunks and format them as context string.
        Returns empty string if nothing relevant found.
        """
        results = self.store.search(query, top_k=top_k)

        # Filter by minimum relevance score
        relevant = [r for r in results if r["score"] >= min_score]

        if not relevant:
            return ""

        context_parts = []
        for r in relevant:
            context_parts.append(f"### {r['metadata'].get('title', 'Reference')}\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)