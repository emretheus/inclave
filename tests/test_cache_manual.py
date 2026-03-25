from src.cache.semantic_cache import SemanticCache

cache = SemanticCache()

# 1. Sisteme başarılı bir sonuç kaydediyoruz (Öğretiyoruz)
cache.store_result(
    query="Show total revenue by city",
    schema_fingerprint="abc123",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00\n...",
)

# 2. TEST: Birebir aynı soruyu soruyoruz
hit = cache.lookup("Show total revenue by city", "abc123")
assert hit is not None, "HATA: Birebir eşleşme bulunamadı!"
print(f"✅ Exact match (Birebir Eşleşme): {hit.code[:50]}...")

# 3. TEST: Soruyu değiştirip eşanlamlı (semantik) soruyoruz
hit = cache.lookup("Display sum of revenue per city", "abc123")
assert hit is not None, "HATA: Anlamsal eşleşme bulunamadı!"
print(f"✅ Semantic match (Anlamsal Eşleşme): {hit.code[:50]}...")

# 4. TEST: Soru aynı ama Şema (Dosya) farklı - TUZAK
miss = cache.lookup("Show total revenue by city", "xyz789")
assert miss is None, "HATA: Farklı şemada yanlışlıkla önbellekten sonuç getirdi!"
print("✅ Different schema (Farklı Şema): Cache miss (Doğru çalıştı, tuzağa düşmedi)")

# Son İstatistikleri Yazdır
print(f"\n📊 Cache stats: {cache.stats()}")