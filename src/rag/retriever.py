from src.vectordb.store import VectorStore

class KnowledgeRetriever:
    """Verilen bir sorgu için ilgili bilgi parçalarını (chunk) veritabanından getirir."""

    def __init__(self):
        # Indexer'ın doldurduğu 'knowledge' koleksiyonuna bağlanıyoruz
        self.store = VectorStore(collection_name="knowledge")

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.3,
                 schema_hint: str = "") -> str:
        """
        İlgili parçaları arar ve onları bağlam (context) metni olarak formatlar.
        İlgili hiçbir şey bulunamazsa boş string döner.
        
        schema_hint: Aramayı zenginleştirmek için opsiyonel sütun tipi bilgisi
                     (Örn: "columns: revenue(float64), city(object)")
        """
        # Şema-farkındalı sorgu (Schema-aware query): Arama metnini sütun tipleriyle 
        # zenginleştirerek gerçek veri tiplerine uyan kalıpları bulmasını sağlıyoruz.
        enriched_query = query
        if schema_hint:
            enriched_query = f"{query} | {schema_hint}"

        # Veritabanında (ChromaDB) anlamsal arama yap
        results = self.store.search(enriched_query, top_k=top_k)

        # Minimum alaka (benzerlik) skoruna göre filtrele
        relevant = [r for r in results if r["score"] >= min_score]

        if not relevant:
            return ""

        # Bulunan sonuçları LLM'e göndermek üzere formatla
        context_parts = []
        for r in relevant:
            context_parts.append(f"### {r['metadata'].get('title', 'Reference')}\n{r['text']}")

        # Araya ayraçlar koyarak tek bir metin halinde birleştir
        return "\n\n---\n\n".join(context_parts)