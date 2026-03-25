# clear_cache.py
from src.cache.semantic_cache import SemanticCache

def main():
    print("🧹 Semantic Cache temizleniyor...")
    cache = SemanticCache()
    # ChromaDB'deki 'semantic_cache' koleksiyonunu sıfırla
    cache.store.reset() 
    print("✅ Önbellek başarıyla silindi. Artık testler sıfırdan başlayacak.")

if __name__ == "__main__":
    main()