import pandas as pd
from src.csv_engine.schema_analyzer import SchemaAnalyzer

# 1. Test için sahte ve biraz "kirli" bir veri oluşturalım
data = {
    "Isim": ["Ali", "Ayşe", "Mehmet"],
    "Boy": ["170 cm", "1.80 m", "165cm"],      # Birimli veri
    "Indirim": ["%10", "%25", "%15"],          # Yüzdelik veri
    "Adres": ["12. Cadde No 5", "Apt 4", "10. Sok"] # Tehlikeli metin verisi
}
df = pd.read_csv("data/sample_csvs/test_veri.csv") if False else pd.DataFrame(data)

# Test dosyasını data/sample_csvs klasörüne kaydedelim
test_file_path = "data/sample_csvs/test_veri.csv"
df.to_csv(test_file_path, index=False)

# 2. Analyzer'ı çalıştıralım
analyzer = SchemaAnalyzer()
schema = analyzer.analyze(test_file_path)

# 3. Sonucu yazdıralım (Yapay zekanın göreceği format)
print("\n--- YAPAY ZEKAYA GİDECEK PROMPT ŞEMASI ---")
print(schema.to_prompt_string())