import pytest
from src.llm.reviewer import LocalReviewerAgent, ReviewResult, ReviewIssue

# --- FIXTURE ---
@pytest.fixture
def reviewer():
    """Her test için taze bir LocalReviewerAgent örneği oluşturur."""
    return LocalReviewerAgent()

# ==========================================
# 1. BİRİM TESTLERİ (UNIT TESTS)
# (Ollama'ya gitmeden iç metodları test eder)
# ==========================================

def test_extract_code_with_markdown(reviewer):
    """Markdown blokları içindeki Python kodunu doğru ayıklıyor mu?"""
    raw_text = "Here is the code:\n```python\nprint('hello')\n```\nEnjoy!"
    extracted = reviewer._extract_code(raw_text)
    assert extracted == "print('hello')"

def test_extract_code_without_markdown(reviewer):
    """Eğer LLM markdown kullanmazsa kodu bozmadan döndürüyor mu?"""
    raw_text = "print('hello world')"
    extracted = reviewer._extract_code(raw_text)
    assert extracted == "print('hello world')"

def test_parse_review_valid_json(reviewer):
    """Geçerli bir JSON döndüğünde ReviewResult objesi doğru doluyor mu?"""
    mock_llm_response = """
    I have reviewed the code.
    ```json
    {
        "issues": [
            {"severity": "high", "description": "Used mean instead of sum."}
        ],
        "suggestions": ["Change .mean() to .sum()"],
        "summary": "Found a critical logic error."
    }
    ```
    """
    result = reviewer._parse_review(mock_llm_response)
    
    assert result.error is None
    assert len(result.issues) == 1
    assert result.issues[0].severity == "high"
    assert result.issues[0].description == "Used mean instead of sum."
    assert result.summary == "Found a critical logic error."
    assert "Change .mean() to .sum()" in result.suggestions

def test_parse_review_invalid_json_graceful_degradation(reviewer):
    """JSON parse edilemezse uygulama çökmeden hata mesajı dönüyor mu?"""
    mock_bad_response = "I'm sorry, I cannot fulfill this request right now."
    result = reviewer._parse_review(mock_bad_response)
    
    assert result.error == "Parse error"
    assert len(result.issues) == 0

# ==========================================
# 2. ENTEGRASYON TESTLERİ (INTEGRATION TESTS)
# (Gerçek Ollama API çağrısı yapar)
# ==========================================

@pytest.mark.integration
def test_review_real_ollama_call(reviewer):
    """
    Ollama'nın bariz bir mantık hatasını (ortalama yerine toplam istenmesi) 
    yakalayıp yakalayamadığını test eder.
    """
    user_prompt = "Calculate the total revenue by city."
    csv_schema = "city(object), revenue(float), date(object)"
    
    # Hatalı kod: sum() yerine mean() kullanılmış!
    bad_code = """
import pandas as pd
df = pd.read_csv(csv_path)
print(df.groupby('city')['revenue'].mean())
"""
    
    result = reviewer.review(user_prompt, csv_schema, bad_code)
    
    assert isinstance(result, ReviewResult)
    assert result.error is None, f"JSON Parse hatası yaşandı: {result.error}"
    assert len(result.issues) > 0, "Reviewer hatalı kodda hiçbir sorun bulamadı!"
    
    # LLM'in bu hatayı (ortalama alma) bulmasını bekliyoruz.
    severities = [issue.severity.lower() for issue in result.issues]
    assert "high" in severities or "medium" in severities, "Hata bulundu ama önemi belirtilmedi veya düşük (low) verildi."

@pytest.mark.integration
def test_improve_real_ollama_call(reviewer):
    """
    Reviewer'ın verilen bir hata listesine bakarak kodu GERÇEKTEN 
    düzeltip düzeltemediğini test eder.
    """
    user_prompt = "Calculate the total revenue by city."
    csv_schema = "city(object), revenue(float), date(object)"
    bad_code = """
import pandas as pd
df = pd.read_csv(csv_path)
print(df.groupby('city')['revenue'].mean())
"""
    # Kendi yakaladığı bir 'high' hata senaryosunu taklit ediyoruz
    mock_review_result = ReviewResult(
        issues=[
            ReviewIssue(severity="high", description="You used .mean() for 'total revenue'. You must use .sum().")
        ],
        summary="Aggregation logic error."
    )
    
    improved_code = reviewer.improve(user_prompt, csv_schema, bad_code, mock_review_result)
    
    assert improved_code is not None
    assert len(improved_code) > 0
    assert "sum()" in improved_code, "Düzeltilmiş kodda 'sum()' fonksiyonu bulunamadı, düzeltme başarısız!"
    assert "mean()" not in improved_code, "Düzeltilmiş kodda hala yanlış olan 'mean()' fonksiyonu duruyor!"
    assert "import pandas" in improved_code, "Düzeltilmiş kod, import kısımlarını silmiş, tam script dönmedi."