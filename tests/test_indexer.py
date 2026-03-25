from src.rag.indexer import KnowledgeIndexer

# İndeksleyiciyi başlat
indexer = KnowledgeIndexer()

# force_reindex=True diyerek her seferinde temizden başlamasını sağlıyoruz
indexer.index_knowledge_dir(force_reindex=True)

# Son durumu kontrol et
stats = indexer.get_stats()
print("\n--- İstatistikler ---")
print(stats)