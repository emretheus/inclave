from src.vectordb.store import VectorStore 
import hashlib

class FewShotStore:
    """Başarılı çalışan sorguları anlamsal vektör olarak kaydeder, kodu metadatada saklar."""

    def __init__(self):
        # Normal belgelerle karışmasın diye ChromaDB'de yeni bir koleksiyon
        self.store = VectorStore(collection_name="few_shot_examples")

    def save(self, query: str, schema_summary: str, code: str):
        """Sadece sorguyu vektöre çevirip veritabanına ekler, kodu 'metadata'ya kargo yapar."""
        # ID'yi sadece kullanıcı sorgusundan üretiyoruz (büyük/küçük harf duyarsız)
        doc_id = hashlib.md5(query.strip().lower().encode()).hexdigest()
        
        # DİKKAT: Vektörlenecek text (documents) olarak SADECE query veriyoruz!
        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[query],  # ChromaDB sadece bunu matematiğe (vektöre) dökecek
            metadatas=[{
                "code": code,
                "schema_summary": schema_summary,
                "type": "few_shot"
            }]
        )

    def find_similar(self, query: str, top_k: int = 1) -> str:
        """Kullanıcının yeni sorusuna anlamsal olarak benzeyen eski bir soru var mı diye arar."""
        results = self.store.search(query, top_k=top_k)
        
        # Eğer sonuç varsa ve benzerlik skoru yüksekse (%85 ve üzeri)
        if results and len(results) > 0:
            best_match = results[0]
            if best_match["score"] >= 0.85:
                # Eşleşen sorunun sırt çantasındaki (metadata) kodu çıkar ve ver!
                return best_match["metadata"].get("code", "")
        return ""

    def count(self) -> int:
        return self.store.count()

    def remove_query(self, query: str):
        """Kullanıcının beğenmediği sorguyu Few-Shot (Başarılı Kodlar) hafızasından siler."""
        doc_id = hashlib.md5(query.strip().lower().encode()).hexdigest()
        try:
            self.store.delete([doc_id])
            print(f"🗑️ [Few-Shot] '{query}' başarıyla silindi.")
        except Exception as e:
            print(f"⚠️ [Few-Shot] Silme hatası veya kayıt yok: {e}")