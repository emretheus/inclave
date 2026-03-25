import hashlib
import time
from dataclasses import dataclass
from src.vectordb.store import VectorStore
from src.config import (
    CACHE_SIMILARITY_THRESHOLD as SIMILARITY_THRESHOLD,
    CACHE_MAX_AGE_SECONDS as MAX_AGE_SECONDS,
)

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
    Sorguları ve üretilen kodları anlamsal benzerliğe göre önbelleğe alır.
    Aynı veya benzer sorular sorulduğunda LLM'i pas geçip direkt sonucu döndürür.
    """
    
    def __init__(self):
        # Normal RAG belgelerine karışmasın diye yeni bir koleksiyon (raf) açıyoruz
        self.store = VectorStore(collection_name="semantic_cache")
        self.total_lookups = 0
        self.total_hits = 0

    def _make_cache_text(self, query: str, schema_fingerprint: str) -> str:
        """Vektörlenecek asıl metni oluşturur."""
        return f"[schema:{schema_fingerprint}] {query}"

    def lookup(self, query: str, schema_fingerprint: str) -> CacheEntry | None:
        """Benzer bir soru önceden sorulmuş mu diye ChromaDB'ye bakar."""
        self.total_lookups += 1  # Her aramada sayacı artır
        cache_text = self._make_cache_text(query, schema_fingerprint)
        results = self.store.search(cache_text, top_k=3)

        for r in results:
            # 1. Kontrol: Yeterince benziyor mu?
            if r["score"] < SIMILARITY_THRESHOLD:
                continue

            meta = r["metadata"]
            
            # 2. Kontrol: Sütun yapıları (Şema) aynı mı?
            if meta.get("schema_fingerprint") != schema_fingerprint:
                continue

            # 3. Kontrol: Kayıt çok eski (bayat) mi?
            age = time.time() - meta.get("created_at", 0)
            if age > MAX_AGE_SECONDS:
                continue

            self.total_hits += 1  # Hit sayısını artır

            # Her şey uygunsa, önbellekteki o altından değerli kodu döndür!
            return CacheEntry(
                query=meta.get("original_query", query),
                schema_fingerprint=schema_fingerprint,
                code=meta.get("code", ""),
                execution_output=meta.get("execution_output", ""),
                created_at=meta.get("created_at", 0),
                hit_count=meta.get("hit_count", 0) + 1,
            )

        return None

    def store_result(self, query: str, schema_fingerprint: str, code: str, execution_output: str = ""):
        """Başarılı olan kodu, gelecekte kopya çekmek üzere veritabanına kaydeder."""
        cache_text = self._make_cache_text(query, schema_fingerprint)
        
        # ID'yi sadece "Soru + Sütun Yapısı" ile oluşturuyoruz ki aynı şey 2 kere kaydedilmesin.
        doc_id = hashlib.md5(f"{query.lower().strip()}:{schema_fingerprint}".encode()).hexdigest()

        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[cache_text],
            metadatas=[{
                "original_query": query,
                "schema_fingerprint": schema_fingerprint,
                "code": code,
                "execution_output": execution_output[:500], # Çıktı çok uzunsa kırp
                "created_at": time.time(),
                "hit_count": 0,
            }],
        )

    def stats(self) -> dict:
        hit_rate = 0
        if self.total_lookups > 0:
            hit_rate = (self.total_hits / self.total_lookups) * 100
            
        return {
            "total_cached": self.store.count(),
            "hit_rate": f"{hit_rate:.1f}%",
            "total_lookups": self.total_lookups,
            "total_hits": self.total_hits,
            "similarity_threshold": SIMILARITY_THRESHOLD,
        }