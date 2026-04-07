import pytest
from src.llm.code_validator import CodeValidator

# --- FIXTURE ---
@pytest.fixture
def validator():
    """Her test için taze bir CodeValidator örneği oluşturur."""
    return CodeValidator()

# ==========================================
# 1. IMPORT DÜZELTME TESTLERİ (_fix_imports)
# ==========================================

def test_fix_imports_adds_missing(validator):
    """Eksik olan kütüphaneleri (pd, np, plt) başarıyla ekliyor mu?"""
    # İçinde pd., np. ve plt. geçen ama import edilmemiş ham kod
    raw_code = "df = pd.DataFrame()\narray = np.array([1, 2])\nplt.plot(array)"
    
    fixed_code = validator._fix_imports(raw_code)
    
    # Beklentimiz: Eksik importların kodun en tepesine eklenmesi
    assert "import pandas as pd" in fixed_code
    assert "import numpy as np" in fixed_code
    assert "import matplotlib.pyplot as plt" in fixed_code
    assert "df = pd.DataFrame()" in fixed_code  # Orijinal kod bozulmamalı

def test_fix_imports_no_false_positives(validator):
    """Halihazırda import edilmiş kütüphaneleri tekrar tekrar (çift) eklemeyi engelliyor mu?"""
    # 'pd.' geçiyor ama 'import pandas as pd' zaten yazılmış
    raw_code = "import pandas as pd\ndf = pd.read_csv('test.csv')"
    
    fixed_code = validator._fix_imports(raw_code)
    
    # 'import pandas as pd' metninin kodda sadece BİR KERE geçmesi lazım
    occurrences = fixed_code.count("import pandas as pd")
    assert occurrences == 1, "Hata: Zaten var olan import'u tekrar ekledi (False Positive)!"

# ==========================================
# 2. SYNTAX (SÖZDİZİMİ) KONTROL TESTLERİ (_check_syntax)
# ==========================================

def test_check_syntax_valid_code(validator):
    """Hatasız, düzgün bir Python koduna onay veriyor mu?"""
    valid_code = "for i in range(5):\n    print(i)"
    
    is_valid, error_msg = validator._check_syntax(valid_code)
    
    print(f"\n[ÇIKTI]: Geçerli mi? {is_valid} | Hata Mesajı: '{error_msg}'")
    assert is_valid is True
    assert error_msg == ""

def test_check_syntax_invalid_code(validator):
    """Syntax (Yazım) hatası olan kodu yakalayıp düzgün mesaj dönüyor mu?"""
    # Kasıtlı syntax hatası: İfadeden sonra iki nokta (:) eksik
    invalid_code = "if True\n    print('hello')"
    print(f"\n\n--- TEST 4: HATALI SYNTAX YAKALAMA ---")
    print(f"[GİRDİ]:\n{invalid_code}")
    
    is_valid, error_msg = validator._check_syntax(invalid_code)
    
    print(f"\n[ÇIKTI]: Geçerli mi? {is_valid} | Hata Mesajı: '{error_msg}'")
    assert is_valid is False
    assert "SyntaxError" in error_msg

# ==========================================
# 3. ANA AKIŞ TESTİ (validate_and_fix)
# ==========================================

def test_validate_and_fix_flow(validator):
    """Eksik importu ekleyip, ardından syntax kontrolünden geçirip doğru tuple'ı dönüyor mu?"""
    # Hem import eksik, hem de yazım hatası (kapanmamış parantez) var
    raw_code = "df = pd.DataFrame(" 
    print(f"\n\n--- TEST 5: TAM AKIŞ (HEM EKSİK İMPORT HEM HATALI KOD) ---")
    print(f"[GİRDİ]:\n{raw_code}")
    
    is_valid, final_code, error_msg = validator.validate_and_fix(raw_code)
    
    assert is_valid is False  # Syntax hatası olduğu için False dönmeli
    assert "import pandas as pd" in final_code  # Hatalı olsa bile importu eklemeli!
    assert "SyntaxError" in error_msg  # Hata mesajı dolu olmalı