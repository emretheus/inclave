import hashlib
import re
from src.vectordb.store import VectorStore


class FewShotStore:
    """Stores successful query->code pairs for retrieval as examples."""

    def __init__(self):
        self.store = VectorStore(collection_name="few_shot_examples")

    def save(self, query: str, schema_summary: str, code: str):
        doc_id = hashlib.md5(f"{query}:{schema_summary}".encode()).hexdigest()
        text = f"Query: {query}\nSchema: {schema_summary}\nCode:\n{code}"
        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[text],
            metadatas=[{"query": query, "type": "few_shot"}],
        )

    def find_similar(self, query: str, top_k: int = 1) -> str:
        results = self.store.search(query, top_k=top_k)
        if results and results[0]["score"] >= 0.5:
            return results[0]["text"]
        return ""

    def list_all(self) -> list[dict]:
        """Return all stored examples as parsed {id, query, code} dicts."""
        raw = self.store.list_all()
        examples = []
        for item in raw:
            query = item["metadata"].get("query", "")
            code = ""
            text = item["text"]
            code_match = re.search(r"Code:\n(.+)", text, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
            examples.append(
                {"id": item["id"], "query": query, "code": code}
            )
        return examples

    def delete(self, doc_id: str):
        self.store.delete(doc_id)

    def count(self) -> int:
        return self.store.count()
