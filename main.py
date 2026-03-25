import uvicorn
from src.api.routes import app
from src.rag.indexer import KnowledgeIndexer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def startup():
    """Sunucu başlarken yapılacak ilk hazırlıklar."""
    indexer = KnowledgeIndexer()
    stats = indexer.get_stats()
    
    # Eğer veritabanı boşsa (ilk kez çalıştırılıyorsa) otomatik olarak indeksle
    if stats["total_chunks"] == 0:
        logger.info("İlk çalışma tespit edildi — bilgi bankası (RAG) indeksleniyor...")
        indexer.index_knowledge_dir()
    else:
        logger.info(f"Bilgi bankası hazır. (Toplam {stats['total_chunks']} parça var)")

if __name__ == "__main__":
    startup()
    # Uygulamayı 8000 portunda dışa açıyoruz
    uvicorn.run(app, host="0.0.0.0", port=8000)