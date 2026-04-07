import os
import pytest
from dotenv import load_dotenv
from src.judge.judge_agent import CloudJudgeAgent
from src.judge.providers import GroqProvider

# .env dosyasını yükle ki JUDGE_API_KEY test ortamına gelsin
load_dotenv()

@pytest.fixture
def judge():
    """Her test için CloudJudgeAgent örneği döner."""
    return CloudJudgeAgent()

# ==========================================
# 1. BİRİM TESTLERİ (JSON PARSE VE MATEMATİK)
# ==========================================

def test_parse_score_valid_json(judge):
    """LLM'den gelen JSON'u bulup puanı doğru hesaplıyor mu?"""
    print("\n\n--- TEST 1: JSON AYRIŞTIRMA VE AĞIRLIKLI PUAN HESAPLAMA ---")
    
    # Arayüzü bozmamak için markdown işaretleri yerine doğrudan JSON stringi veriyoruz.
    # Hakem regex ile bu kısmı zaten yakalayacaktır.
    mock_response = '{"correctness": 8, "intent_alignment": 10, "code_quality": 5, "feedback": "Harika ama yorum satırı eksik."}'
    
    print(f"[GİRDİ - Sahte LLM Yanıtı]:\n{mock_response}")

    score = judge._parse_score(mock_response)

    print(f"[ÇIKTI]: Doğruluk: {score.correctness}, Niyet: {score.intent_alignment}, Kalite: {score.code_quality}")
    print(f"Genel Puan: {score.overall} | Geçti mi? {score.passed}")

    # Matematik: (8 * 0.4) + (10 * 0.4) + (5 * 0.2) = 3.2 + 4.0 + 1.0 = 8.2
    assert score.overall == 8.2
    assert score.passed is True
    assert score.feedback == "Harika ama yorum satırı eksik."

def test_parse_score_invalid_json(judge):
    """Bozuk JSON geldiğinde sistem çökmek yerine güvenli bir hata (fallback) dönüyor mu?"""
    print("\n\n--- TEST 2: BOZUK JSON (GRACEFUL DEGRADATION) ---")
    bad_response = "I cannot evaluate this code."

    score = judge._parse_score(bad_response)
    print(f"[ÇIKTI]: Genel Puan: {score.overall} | Geri Bildirim: {score.feedback}")

    assert score.overall == 0.0
    assert score.passed is False
    assert "Failed to parse" in score.feedback

# ==========================================
# 2. ENTEGRASYON TESTİ (GERÇEK GROQ ÇAĞRISI)
# ==========================================

@pytest.mark.integration
def test_groq_real_evaluation(judge):
    """Gerçek Groq API'sine bağlanıp Llama3 ile bir kodu puanlatır."""
    print("\n\n--- TEST 3: GERÇEK BULUT HAKEMİ (GROQ API) ÇAĞRISI ---")

    api_key = os.getenv("JUDGE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        pytest.skip("JUDGE_API_KEY bulunamadı. Bu test atlanıyor.")
        
    assert isinstance(judge.provider, GroqProvider), "Sağlayıcı Groq olarak ayarlanmamış!"

    user_prompt = "Calculate the average price of cars."
    csv_schema = "Columns: brand(object), price(float), year(int)"

    # Basit, çalışan bir pandas kodu
    good_code = "import pandas as pd\ndf = pd.read_csv('cars.csv')\nprint(df['price'].mean())"

    print("Buluta kod gönderiliyor... (Lütfen bekleyin)")
    score = judge.evaluate(
        user_prompt=user_prompt,
        csv_schema=csv_schema,
        code=good_code,
        execution_success=True,
        execution_output="25000.5"
    )

    print(f"[GROQ ÇIKTISI]: Puan: {score.overall}/10.0 | Geçti mi: {score.passed}")
    print(f"[GROQ YORUMU]: {score.feedback}")

    assert score.error is None, f"API Hatası yaşandı: {score.error}"
    assert score.overall > 0, "Puan hesaplanamadı veya 0 geldi."
    assert score.passed is True, "Hakem tamamen doğru olan bir koda 'kaldı' dedi!"