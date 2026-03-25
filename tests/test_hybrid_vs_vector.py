from src.rag.retriever import KnowledgeRetriever
from src.rag.hybrid_retriever import HybridRetriever

print("🔍 Vektör Arama vs Hibrit Arama Karşılaştırma Testi Başlıyor...\n")

# Eski ve yeni motorları başlatıyoruz
vector_only = KnowledgeRetriever()
hybrid = HybridRetriever(use_llm_reranker=False)

print("BM25 İndeksi oluşturuluyor/yükleniyor...")
hybrid.build_bm25_index()
print("-" * 50)

test_queries = [
    "pd.read_csv encoding parameter",      # Nokta atışı API ismi → BM25 parlayacak
    "how to handle missing data",          # Anlamsal (Semantic) → Vektör parlayacak
    "groupby sum reset_index",             # Karışık (API ismi + Konsept)
    "convert string column to datetime",   # İkisi de iyi sonuç vermeli
    "df.merge on customer_id",             # Nokta atışı API ismi → BM25 parlayacak
]

for q in test_queries:
    # İki motoru da aynı soruyla ve aynı limitlerle (top_k=3) çalıştırıyoruz
    v_result = vector_only.retrieve(q, top_k=3)
    h_result = hybrid.retrieve(q, top_k=3)
    
    print(f"\nSorgu: '{q}'")
    print(f"  Eski Sistem (Sadece Vektör): {len(v_result)} karakter bağlam getirdi.")
    print(f"  Yeni Sistem (Hibrit):        {len(h_result)} karakter bağlam getirdi.")
    
    # Not: İdeal olan, Hibrit'in sadece karakter olarak daha fazla değil, 
    # içerik olarak daha isabetli sonuçlar (BM25 sayesinde) getirmesidir.