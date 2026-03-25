# test_rag_manual.py
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import KnowledgeRetriever

# Adım 1: İndeksleme (Kütüphaneyi Güncelleme)
print("--- ADIM 1: Bilgi Bankası Hazırlanıyor ---")
indexer = KnowledgeIndexer()
indexer.index_knowledge_dir(force_reindex=True)
print("İstatistikler:", indexer.get_stats())

# Adım 2: Arama (Retriever Testi)
print("\n--- ADIM 2: Arama Motoru Testi ---")
retriever = KnowledgeRetriever()

# Test Sorguları
test_queries = [
    "how to read a CSV file",
    "fill missing values in dataframe",
    "group by column and sum",
    "export to excel",
    "find duplicate rows",
]

for q in test_queries:
    print(f"\n{'='*60}")
    print(f"Sorgu: {q}")
    # En iyi 2 sonucu getiriyoruz
    context = retriever.retrieve(q, top_k=2)
    
    if context:
        # Ekranı çok doldurmamak için sadece ilk 200 karakteri yazdırıyoruz
        print(f"Bulunan İçerik:\n{context[:200]}...")
    else:
        print("İlgili hiçbir içerik bulunamadı.")