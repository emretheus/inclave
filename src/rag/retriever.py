from src.vectordb.store import VectorStore


class KnowledgeRetriever:
    """Retrieves relevant knowledge chunks for a given query."""

    def __init__(self):
        self.store = VectorStore(collection_name="knowledge")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.3,
        schema_hint: str = "",
    ) -> str:
        enriched_query = query
        if schema_hint:
            enriched_query = f"{query} | {schema_hint}"

        results = self.store.search(enriched_query, top_k=top_k)
        relevant = [r for r in results if r["score"] >= min_score]

        if not relevant:
            return ""

        context_parts = []
        for r in relevant:
            context_parts.append(
                f"### {r['metadata'].get('title', 'Reference')}\n{r['text']}"
            )

        return "\n\n---\n\n".join(context_parts)
