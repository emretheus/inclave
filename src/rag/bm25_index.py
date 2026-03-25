import json
import re
from pathlib import Path
from dataclasses import dataclass
from rank_bm25 import BM25Okapi

@dataclass
class BM25Document:
    doc_id: str
    text: str
    metadata: dict

class BM25Index:
    """
    BM25 keyword search index. Complements vector search
    by finding exact keyword/API name matches.
    """

    def __init__(self):
        self.documents: list[BM25Document] = []
        self.bm25: BM25Okapi | None = None
        self._tokenized_corpus: list[list[str]] = []

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric, keep underscores."""
        text = text.lower()
        tokens = re.findall(r'[a-z_][a-z0-9_.]*', text)
        return [t for t in tokens if len(t) > 1]

    def build(self, documents: list[BM25Document]):
        """Build the BM25 index from a list of documents."""
        self.documents = documents
        self._tokenized_corpus = [self._tokenize(doc.text) for doc in documents]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search using BM25 scoring."""
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        scored_docs = list(zip(self.documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scored_docs[:top_k]:
            if score <= 0:
                break
            results.append({
                "id": doc.doc_id,
                "text": doc.text,
                "score": float(score),
                "metadata": doc.metadata,
                "source": "bm25",
            })
        return results

    def save(self, path: str | Path):
        """Persist document list to JSON (BM25 index is rebuilt on load)."""
        data = [{"id": d.doc_id, "text": d.text, "metadata": d.metadata}
                for d in self.documents]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, path: str | Path):
        """Load documents from JSON and rebuild BM25 index."""
        data = json.loads(Path(path).read_text())
        docs = [BM25Document(doc_id=d["id"], text=d["text"], metadata=d["metadata"])
                for d in data]
        self.build(docs)