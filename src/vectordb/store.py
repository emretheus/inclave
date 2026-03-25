import chromadb
from chromadb.config import Settings as ChromaSettings
import ollama
from pathlib import Path

# DİKKAT: Bizim config dosyamıza uyumlu import yapıyoruz
from src.config import CHROMA_PERSIST_DIR, OLLAMA_BASE_URL, EMBED_MODEL

class VectorStore:
    """ChromaDB için ince bir sarmalayıcı (wrapper). RAG işlemleri için kullanılır."""

    def __init__(self, collection_name: str = "knowledge"):
        self.persist_dir = str(CHROMA_PERSIST_DIR)
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Kosinüs benzerliği kullanarak arama yapacak koleksiyonu oluştur
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embed_client = ollama.Client(host=OLLAMA_BASE_URL)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Ollama nomic-embed-text kullanarak metinleri vektörlere dönüştürür."""
        response = self.embed_client.embed(
            model=EMBED_MODEL,
            input=texts,
        )
        return response["embeddings"]

    def add_documents(self, doc_ids: list[str], texts: list[str], metadatas: list[dict] | None = None):
        """Dökümanları vektörleştirip veritabanına ekler."""
        embeddings = self._embed(texts)
        self.collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Benzer dökümanları arar. {id, text, score, metadata} listesi döner."""
        query_embedding = self._embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        # ChromaDB sonuçları iç içe listeler halinde döndürdüğü için onları düzeltiyoruz
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                items.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "score": 1 - results["distances"][0][i],  # kosinüs mesafesini -> benzerlik skoruna çevir
                    "metadata": results["metadatas"][0][i],
                })
        return items

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        """Tüm dökümanları siler. Yeniden indeksleme için kullanılır."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )