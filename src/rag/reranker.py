import re
from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import RERANK_SYSTEM, RERANK_TEMPLATE

class LLMReranker:
    """
    Re-ranks retrieved chunks using the LLM as a cross-encoder.
    Scores each chunk's relevance to the query on a 0-10 scale.
    """

    
    def __init__(self):
        self.generator = CodeGenerator()

    def rerank(self, query: str, results: list[dict], top_n: int = 3) -> list[dict]:
        """
        Re-rank a list of search results by asking the LLM to score each.
        Returns top_n results sorted by relevance score.
        """
        if len(results) <= top_n:
            return results

        scored = []
        for r in results:
            try:
                raw = self.generator.generate(
                        prompt=self.RERANK_TEMPLATE.format(
                        query=query,
                        document=r["text"][:500],
                    ),
                    system_prompt=self.RERANK_SYSTEM,
                )
                score = self._parse_score(raw)
            except Exception:
                score = r.get("score", 0.5)

            scored.append({**r, "rerank_score": score})

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_n]

    def _parse_score(self, raw: str) -> float:
        """Extract a numeric score from LLM response."""
        match = re.search(r'(\d+(?:\.\d+)?)', raw.strip())
        if match:
            score = float(match.group(1))
            return min(max(score / 10.0, 0.0), 1.0)
        return 0.5


class SimpleReranker:
    """
    Lightweight re-ranker that combines vector and BM25 scores
    using Reciprocal Rank Fusion (RRF). No LLM call needed.
    Use this for low-latency scenarios; use LLMReranker for higher quality.
    """

    def rerank(self, results: list[dict], top_n: int = 3, k: int = 60) -> list[dict]:
        """
        Reciprocal Rank Fusion: combines rankings from multiple sources.
        RRF(d) = Σ 1/(k + rank_i(d))
        """
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        # Group by source (vector vs bm25)
        sources: dict[str, list[dict]] = {}
        for r in results:
            source = r.get("source", "vector")
            sources.setdefault(source, []).append(r)
            doc_map[r["id"]] = r

        # Calculate RRF scores
        for source, docs in sources.items():
            docs.sort(key=lambda x: x["score"], reverse=True)
            for rank, doc in enumerate(docs):
                rrf = 1.0 / (k + rank + 1)
                doc_scores[doc["id"]] = doc_scores.get(doc["id"], 0) + rrf

        
        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {**doc_map[doc_id], "rerank_score": score}
            for doc_id, score in ranked[:top_n]
        ]