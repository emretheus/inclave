from src.vectordb.store import VectorStore
from src.rag.bm25_index import BM25Index, BM25Document
from src.rag.reranker import SimpleReranker, LLMReranker
from src.rag.chunking import MarkdownCodeChunker
from src.config import CHROMA_PERSIST_DIR, KNOWLEDGE_DIR, VECTOR_WEIGHT, BM25_WEIGHT, MIN_RETRIEVAL_SCORE
import logging

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Combines vector search (semantic) + BM25 (keyword) with re-ranking.
    Drop-in replacement for the Phase 1 KnowledgeRetriever.
    """

    def __init__(self, use_llm_reranker: bool = False):
        self.vector_store = VectorStore(collection_name="knowledge")
        self.bm25_index = BM25Index()
        # Varsayılan olarak hızlı olan SimpleReranker (RRF) kullanıyoruz
        self.reranker = LLMReranker() if use_llm_reranker else SimpleReranker()
        self._bm25_built = False

    def build_bm25_index(self, force: bool = False):
        """Build BM25 index from the same knowledge documents used by vector store."""
        bm25_path = CHROMA_PERSIST_DIR / "bm25_docs.json"

        if not force and bm25_path.exists():
            self.bm25_index.load(bm25_path)
            self._bm25_built = True
            logger.info(f"BM25 index loaded: {len(self.bm25_index.documents)} docs")
            return

        chunker = MarkdownCodeChunker()
        chunks = chunker.chunk_directory(KNOWLEDGE_DIR)

        docs = [
            BM25Document(doc_id=c.id, text=c.text, metadata=c.metadata)
            for c in chunks
        ]
        self.bm25_index.build(docs)
        self.bm25_index.save(bm25_path)
        self._bm25_built = True
        logger.info(f"BM25 index built: {len(docs)} docs")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = MIN_RETRIEVAL_SCORE,
        schema_hint: str = "",
        vector_weight: float = VECTOR_WEIGHT,
        bm25_weight: float = BM25_WEIGHT,
    ) -> str:
        """
        Hybrid retrieval: vector + BM25, merged and re-ranked.
        Returns formatted context string for prompt injection.
        """
        enriched_query = query
        if schema_hint:
            enriched_query = f"{query} | {schema_hint}"

        # 1. Vector search (Semantic similarity / Anlamsal benzerlik)
        vector_results = self.vector_store.search(enriched_query, top_k=top_k * 2)
        for r in vector_results:
            r["source"] = "vector"
            r["score"] = r["score"] * vector_weight

        # 2. BM25 search (Keyword matching / Birebir kelime eşleşmesi)
        bm25_results = []
        if self._bm25_built:
            bm25_results = self.bm25_index.search(query, top_k=top_k * 2)
            if bm25_results:
                # BM25 skorları sınırsızdır (unbounded), 0-1 arasına normalize etmeliyiz
                max_bm25 = max((x["score"] for x in bm25_results), default=1.0)
                for r in bm25_results:
                    r["score"] = (r["score"] / max_bm25) * bm25_weight if max_bm25 > 0 else 0

        # Merge and deduplicate (İkisini birleştir ve tekrarları sil)
        all_results = vector_results + bm25_results
        seen_ids = set()
        unique_results = []
        for r in all_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)

        if not unique_results:
            return ""

        # 3. Re-rank (Yeniden Sıralama)
        reranked = self.reranker.rerank(unique_results, top_n=top_k)

        if reranked and isinstance(self.reranker, SimpleReranker):
            max_rs = max((r.get("rerank_score", 0) for r in reranked), default=1.0)
            if max_rs > 0:
                for r in reranked:
                    r["rerank_score"] = r.get("rerank_score", 0) / max_rs

        # Filter by minimum score (Kalite filtresi)
        relevant = [r for r in reranked if r.get("rerank_score", r["score"]) >= min_score]

        if not relevant:
            return ""

        # Format as context string (Prompt için metne çevir)
        context_parts = []
        for r in relevant:
            source = r.get("source", "hybrid")
            title = r.get("metadata", {}).get("title", "Reference")
            context_parts.append(f"### {title} [{source}]\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)