from src.vectordb.store import VectorStore
from src.rag.chunking import MarkdownCodeChunker
from src.config import KNOWLEDGE_DIR  # Düzeltilmiş import
from pathlib import Path

class KnowledgeIndexer:
    """Bilgi dökümanlarını parçalayıp vektör veritabanına indeksler (kaydeder)."""

    def __init__(self):
        # Koleksiyon adını 'knowledge' (bilgi) olarak belirliyoruz
        self.store = VectorStore(collection_name="knowledge")
        self.chunker = MarkdownCodeChunker()

    def index_knowledge_dir(self, force_reindex: bool = False):
        """Bilgi klasöründeki tüm markdown dosyalarını indeksler."""
        knowledge_dir = KNOWLEDGE_DIR

        # Eğer zorla yeniden indeksleme isteniyorsa veritabanını sıfırla
        if force_reindex:
            print("Veritabanı sıfırlanıyor (Force reindex)...")
            self.store.reset()

        # Eğer zaten doluysa ve sıfırlama istenmediyse işlemi atla
        if self.store.count() > 0 and not force_reindex:
            print(f"Bilgi bankası zaten indekslenmiş ({self.store.count()} parça). Yeniden oluşturmak için force_reindex=True kullanın.")
            return

        # Markdown dosyalarını parçala (Chunking)
        chunks = self.chunker.chunk_directory(knowledge_dir)
        if not chunks:
            print(f"{knowledge_dir} klasöründe hiç markdown dosyası bulunamadı.")
            return

        print(f"Vektörleştiriliyor... Lütfen bekleyin. (Bu işlem Ollama'yı kullanır)")
        
        # Veritabanına toplu ekleme yap (ChromaDB bunu arka planda yönetir)
        self.store.add_documents(
            doc_ids=[c.id for c in chunks],
            texts=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        print(f"Başarılı! {knowledge_dir} klasöründen {len(chunks)} parça indekslendi.")

    def get_stats(self) -> dict:
        return {"total_chunks": self.store.count()}