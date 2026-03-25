from src.csv_engine.schema_analyzer import SchemaAnalyzer

# Analyzer'ı başlat
analyzer = SchemaAnalyzer()

# Dosya yolunu kendi dosyana göre ayarla (eğer adı train.csv ise değiştir)
dosya_yolu = "data/sample_csvs/Titanic-Dataset.csv" 

print(f"{dosya_yolu} analiz ediliyor... Lütfen bekleyin.\n")

# Analizi yap ve şemayı al
schema = analyzer.analyze(dosya_yolu)

# LLM'in (Ollama'nın) göreceği o meşhur metni yazdır
print("--- YAPAY ZEKAYA GİDECEK TITANIC ŞEMASI ---")
print(schema.to_prompt_string())