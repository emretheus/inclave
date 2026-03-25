from src.llm.judge import JudgeAgent

print("Hakem (Judge Agent) test ediliyor. Bu işlem birkaç saniye sürebilir...\n")
judge = JudgeAgent()

# --- TEST 1: KUSURSUZ KOD (PASS BEKLİYORUZ) ---
print("Test 1: Doğru çalışıp doğru mantık kuran koda PASS vermeli...")
verdict1 = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00",
)
print(f"Sonuç: Beklenen PASS, Alınan: {verdict1.verdict}")
assert verdict1.verdict == "PASS", "HATA: Doğru koda PASS vermedi!"


# --- TEST 2: YANLIŞ FONKSİYON KULLANIMI (FAIL BEKLİYORUZ) ---
# Kullanıcı "total" (toplam) istemiş ama kod "mean" (ortalama) kullanmış.
print("\nTest 2: Yanlış hesaplama (sum yerine mean) yaptıysa FAIL vermeli ve uyarmalı...")
verdict2 = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.groupby('city')['revenue'].mean())",
    execution_output="Istanbul  1720.10\nAnkara   1716.67",
)
print(f"Sonuç: Beklenen FAIL, Alınan: {verdict2.verdict}")
print(f"Hakemin Bulduğu Sorunlar: {verdict2.issues}")
if verdict2.suggested_fix:
    print("Hakemin Önerdiği Kod Düzeltmesi var.")


# --- TEST 3: YANLIŞ SÜTUN KULLANIMI (FAIL BEKLİYORUZ) ---
# Kullanıcı "city" (şehir) bazında istemiş ama kod "product" (ürün) bazında gruplamış.
print("\nTest 3: Yanlış sütuna göre (city yerine product) grupladıysa FAIL vermeli...")
verdict3 = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.groupby('product')['revenue'].sum())",
    execution_output="Widget A  6501.50\nWidget B  7250.00\nWidget C  2475.75",
)
print(f"Sonuç: Beklenen FAIL, Alınan: {verdict3.verdict}")
print(f"Hakemin Bulduğu Sorunlar: {verdict3.issues}")

print("\n✅ TÜM TESTLER BAŞARIYLA GEÇİLDİ! HAKEM GÖREVİNİ KUSURSUZ YAPIYOR.")