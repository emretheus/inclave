from src.llm.pipeline import CodePipeline
import time

def run_evaluation():
    pipeline = CodePipeline()
    print("=== OTONOM TEST BAŞLIYOR (10 SENARYO) ===")
    
    
    test_scenarios = [
        # --- PLANLANAN KARIŞIK TESTLER ---
        ("data/sample_csvs/employees.csv", "Show the first 5 rows"),
        ("data/sample_csvs/weather.csv", "Plot monthly temperature trend"),
        ("data/sample_csvs/weather.csv", "Find outliers using IQR method for temp_c"),
        ("data/sample_csvs/employees.csv", "Group by department and show average salary"),
        ("data/sample_csvs/messy_data.csv", "Read this file, clean stock_level column to be numeric, and show it"),
        
        # --- TITANIC ÖZEL TESTLERİ (10 Adet) ---
        ("data/sample_csvs/Titanic-Dataset.csv", "Show the first 5 rows"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Calculate the overall survival rate"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Fill missing Age values with the median age"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Group by Sex and show the survival rate"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Show the average Fare grouped by Pclass"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Find the oldest passenger who survived"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Count the number of passengers from each Embarked port"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Filter the dataframe to show only female passengers in 1st class"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Create a bar chart showing the number of survivors by Pclass"),
        ("data/sample_csvs/Titanic-Dataset.csv", "Drop the Cabin column and print the new columns list"),
    ]
    
    success_count = 0
    total = len(test_scenarios)
    
    # Rapor dosyasını Python ile doğrudan oluşturuyoruz
    with open("basarili_kodlar_raporu.txt", "w", encoding="utf-8") as rapor:
        rapor.write("=== BAŞARILI TEST SENARYOLARI RAPORU ===\n\n")
        
        for i, (csv_file, prompt) in enumerate(test_scenarios, 1):
            print(f"[{i}/{total}] Test ediliyor: '{prompt}'...")
            start_time = time.time()
            
            result = pipeline.generate(csv_file, prompt)
            elapsed = time.time() - start_time
            
            if result.execution_success:
                success_count += 1
                print(f"  -> ✅ Başarılı! ({elapsed:.1f} sn) Rapora eklendi.")
                
                # SADECE BAŞARILI OLANLARI DOSYAYA YAZ
                rapor.write(f"Sorgu: {prompt}\n")
                rapor.write(f"Veri Seti: {csv_file}\n")
                rapor.write("-" * 40 + "\n")
                rapor.write("💻 ÜRETİLEN KOD:\n")
                rapor.write(result.code + "\n")
                rapor.write("-" * 40 + "\n")
                rapor.write("📊 ÇIKTI (TERMINAL):\n")
                rapor.write(result.execution_output.strip() if result.execution_output.strip() else "(Kod çalıştı ama ekrana bir şey yazdırmadı)")
                rapor.write("\n" + "=" * 60 + "\n\n")
            else:
                print(f"  -> ❌ Başarısız. ({elapsed:.1f} sn) Dosyaya yazılmadı.")

                
    success_rate = (success_count / total) * 100
    print("\n" + "="*40)
    print("🏆 TEST SONUÇLARI (KARNE)")
    print("="*40)
    print(f"Çalışan Senaryo: {success_count} / {total}")
    print(f"Başarı Oranı   : %{success_rate}")
    
    if success_rate >= 70:
        print("Sonuç: 🌟 HEDEF TUTTURULDU! (MVP MVP hedefi %70 aşildı)")
    else:
        print("Sonuç: ⚠️ GELİŞTİRİLMESİ GEREKİYOR.")

if __name__ == "__main__":
    run_evaluation()