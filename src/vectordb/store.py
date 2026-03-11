import chromadb
from chromadb.config import Settings as ChromaSettings
import ollama
from src.config import settings
from pathlib import Path


class VectorStore:
    """Thin wrapper around ChromaDB with Ollama embeddings."""

    def __init__(self, collection_name: str = "knowledge"):
        self.persist_dir = str(settings.chroma_persist_dir)
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embed_client = ollama.Client(host=settings.ollama_base_url)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.embed_client.embed(
            model=settings.embed_model,
            input=texts,
        )
        return response["embeddings"]

    def add_documents(
        self,
        doc_ids: list[str],
        texts: list[str],
        metadatas: list[dict] | None = None,
    ):
        embeddings = self._embed(texts)
        self.collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        query_embedding = self._embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        for i in range(len(results["ids"][0])):
            items.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "score": 1 - results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
            )
        return items

    def list_all(self, limit: int = 50) -> list[dict]:
        """Return all documents in the collection (up to limit)."""
        count = self.collection.count()
        if count == 0:
            return []
        results = self.collection.get(
            limit=min(count, limit),
            include=["documents", "metadatas"],
        )
        items = []
        for i in range(len(results["ids"])):
            items.append(
                {
                    "id": results["ids"][i],
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                }
            )
        return items

    def delete(self, doc_id: str):
        self.collection.delete(ids=[doc_id])

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )
