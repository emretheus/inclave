import pytest
from src.llm.pipeline import CodePipeline
import os

def test_full_pipeline_with_all_features():
    """Phase 1.2: Tüm özelliklerin (Cache, Memory, RAG, Judge, Classifier) uyum testi."""
    pipeline = CodePipeline()
    csv_path = "data/sample_csvs/sales_data.csv"
    
    # Dosya kontrolü (Testin patlamaması için)
    if not os.path.exists(csv_path):
        pytest.skip(f"Test dosyası bulunamadı: {csv_path}")

    # --- TUR 1: AGGREGATION (RAG ve Judge tetiklenmeli) ---
    print("\n[Tur 1] İlk sorgu gönderiliyor...")
    r1 = pipeline.generate(csv_path, "Show total revenue by city")
    
    assert r1.execution_success, "İlk tur başarısız oldu!"
    assert r1.query_category == "aggregation", "Sınıflandırma hatalı!"
    assert r1.session_id is not None, "Oturum oluşturulmadı!"
    assert not r1.from_cache, "İlk sorgu cache'den gelmemeliydi!"
    assert r1.judge_verdict in ("PASS", "WARN"), f"Judge reddetti: {r1.judge_issues}"
    
    session_id = r1.session_id

    # --- TUR 2: FOLLOW-UP (Memory testi) ---
    print("[Tur 2] Takip sorgusu gönderiliyor (Bağlam testi)...")
    r2 = pipeline.generate(csv_path, "Now make it a bar chart", session_id=session_id)
    
    assert r2.is_follow_up, "Takip sorgusu algılanamadı!"
    assert "plt." in r2.code or "plot" in r2.code, "Grafik kodu üretilmedi!"
    assert r2.turn_number == 2, "Tur sayısı hatalı!"

    # --- TUR 3: REPEAT QUERY (Semantic Cache testi) ---
    print("[Tur 3] Tekrarlanan sorgu (Cache testi)...")
    # Hafif farklı sorsak bile (%92 benzerlik) yakalamalı
    r3 = pipeline.generate(csv_path, "Show the total revenue for each city")
    
    assert r3.from_cache, "Semantic Cache bu sorguyu yakalamalıydı!"
    assert r3.retrieval_method == "semantic_cache"
    print(f"⚡ Cache Hit Rate: {r3.cache_stats.get('hit_rate')}")

    print("\n✅ Phase 1.2 Entegrasyon Testi Başarıyla Tamamlandı!")