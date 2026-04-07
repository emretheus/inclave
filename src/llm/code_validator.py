import ast
import logging

logger = logging.getLogger(__name__)

class CodeValidator:
    """
    Ollama tarafından üretilen kodu Sandbox'a göndermeden önce denetler.
    1. Eksik import'ları (pd, plt, np vb.) tespit edip otomatik ekler.
    2. Kodun Python syntax (sözdizimi) açısından geçerli olup olmadığını kontrol eder.
    """

    # Hangi kısaltma görüldüğünde hangi import eklenecek?
    IMPORT_FIXES = {
        "pd.": "import pandas as pd",
        "np.": "import numpy as np",
        "plt.": "import matplotlib.pyplot as plt",
        "sns.": "import seaborn as sns",
        "json.": "import json",
        "Path(": "from pathlib import Path",
    }

    def validate_and_fix(self, code: str) -> tuple[bool, str, str]:
        """
        Kodu düzeltir ve syntax kontrolünden geçirir.
        Dönüş: (basarili_mi: bool, duzeltilmis_kod: str, hata_mesaji: str)
        """
        # 1. Eksik importları tamamla
        fixed_code = self._fix_imports(code)

        # 2. Syntax kontrolü yap
        is_valid, error_msg = self._check_syntax(fixed_code)

        if not is_valid:
            logger.error(f"Validator syntax hatası yakaladı: {error_msg}")
            # Syntax hatası varsa bile düzeltilmiş (import eklenmiş) kodu dönüyoruz,
            # böylece Self-Healer doğrudan bu hatayı görüp onarabilir.
            return False, fixed_code, error_msg

        return True, fixed_code, ""

    def _fix_imports(self, code: str) -> str:
        """Kod içindeki kullanımlara bakarak eksik kütüphaneleri en üste ekler."""
        added_imports = []
        
        for trigger, import_stmt in self.IMPORT_FIXES.items():
            # Eğer tetikleyici kelime (örn: 'pd.') kodda geçiyorsa...
            if trigger in code:
                # ...ama import cümlesi (örn: 'import pandas as pd') kodda YOKSA
                # (Bu kontrol False Positive'i yani halihazırda import edilmişse tekrar edilmesini engeller)
                if import_stmt not in code:
                    added_imports.append(import_stmt)
        
        if added_imports:
            imports_str = "\n".join(added_imports)
            logger.info(f"Eksik importlar otomatik eklendi: {added_imports}")
            # Importları kodun en tepesine, orijinal kodla arasına boşluk bırakarak ekle
            return f"{imports_str}\n\n{code}"
            
        return code

    def _check_syntax(self, code: str) -> tuple[bool, str]:
        """Python'ın yerleşik 'ast' modülüyle kodu çalıştırmadan sözdizimi kontrolü yapar."""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} (Satır: {e.lineno})"
        except Exception as e:
            return False, f"Beklenmeyen Hata: {str(e)}"