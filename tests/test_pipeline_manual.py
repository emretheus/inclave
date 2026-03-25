# test_pipeline_manual.py
from src.llm.pipeline import CodePipeline
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("=== SİSTEM BAŞLATILIYOR ===")
pipeline = CodePipeline()

# Test 2: Çeşitli Senaryolar (Artık sadece çıktı ve başarı durumunu göreceğiz)
print("\n" + "="*60)
print("TEST 2: Çeşitli Senaryolar ve Sandbox Sonuçları")
print("="*60)

test_prompts = [
    "Show the first 5 rows",
    "Fill missing discount values with 0",
    "Group by city and show total revenue per city",
    "Find and remove duplicate rows",
    "Create a bar chart of revenue by product",
]

for prompt in test_prompts:
    print(f"\n{'-'*60}")
    print(f"Sorgu: {prompt}")
    
    res = pipeline.generate(
        csv_path="data/sample_csvs/sales_data.csv", 
        user_prompt=prompt
    )
    
    print("\n--- SANDBOX SONUCU ---")
    print(f"Başarı Durumu : {'✅ BAŞARILI' if res.execution_success else '❌ BAŞARISIZ'}")
    print(f"Kaç Deneme    : {res.attempts} / 3")
    
    if res.execution_success:
        print("TERMINAL ÇIKTISI:")
        # Terminal çıktısı boşsa uyar, değilse yazdır
        print(res.execution_output if res.execution_output.strip() else "(Kod çalıştı ama ekrana hiçbir şey yazdırmadı - print eksik)")
    else:
        print("SON HATA (ERROR):")
        print(res.execution_error)