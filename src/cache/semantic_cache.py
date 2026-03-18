import hashlib
import time
from dataclasses import dataclass
from src.vectordb.store import VectorStore


@dataclass
class CacheEntry:
    query: str
    schema_fingerprint: str
    code: str
    execution_output: str
    created_at: float
    hit_count: int = 0


class SemanticCache:
    """
    Caches query→code mappings using semantic similarity.
    Uses ChromaDB for embedding storage and cosine similarity search.
    """

    SIMILARITY_THRESHOLD = 0.92
    MAX_AGE_SECONDS = 86400 * 7  # 7 days
    MAX_ENTRIES = 1000

    def __init__(self):
        self.store = VectorStore(collection_name="semantic_cache")

    def _make_cache_text(self, query: str, schema_fingerprint: str) -> str:
        return f"[schema:{schema_fingerprint}] {query}"

    def lookup(self, query: str, schema_fingerprint: str) -> CacheEntry | None:
        """
        Search for a semantically similar cached result.
        Returns CacheEntry if found with sufficient similarity, None otherwise.
        """
        cache_text = self._make_cache_text(query, schema_fingerprint)
        results = self.store.search(cache_text, top_k=3)

        for r in results:
            if r["score"] < self.SIMILARITY_THRESHOLD:
                continue

            meta = r["metadata"]
            if meta.get("schema_fingerprint") != schema_fingerprint:
                continue

            age = time.time() - meta.get("created_at", 0)
            if age > self.MAX_AGE_SECONDS:
                continue

            return CacheEntry(
                query=meta.get("original_query", query),
                schema_fingerprint=schema_fingerprint,
                code=meta.get("code", ""),
                execution_output=meta.get("execution_output", ""),
                created_at=meta.get("created_at", 0),
                hit_count=meta.get("hit_count", 0) + 1,
            )

        return None

    def store_result(
        self,
        query: str,
        schema_fingerprint: str,
        code: str,
        execution_output: str = "",
    ):
        """Save a successful generation result to the cache."""
        cache_text = self._make_cache_text(query, schema_fingerprint)
        doc_id = hashlib.md5(f"{query}:{schema_fingerprint}".encode()).hexdigest()

        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[cache_text],
            metadatas=[{
                "original_query": query,
                "schema_fingerprint": schema_fingerprint,
                "code": code,
                "execution_output": execution_output[:500],
                "created_at": time.time(),
                "hit_count": 0,
            }],
        )

    def invalidate(self, schema_fingerprint: str):
        """Remove all cached entries for a specific schema."""
        results = self.store.search(f"[schema:{schema_fingerprint}]", top_k=100)
        ids_to_delete = [
            r["id"] for r in results
            if r["metadata"].get("schema_fingerprint") == schema_fingerprint
        ]
        if ids_to_delete:
            self.store.collection.delete(ids=ids_to_delete)

    def stats(self) -> dict:
        return {
            "total_cached": self.store.count(),
            "max_entries": self.MAX_ENTRIES,
            "similarity_threshold": self.SIMILARITY_THRESHOLD,
            "max_age_days": self.MAX_AGE_SECONDS / 86400,
        }