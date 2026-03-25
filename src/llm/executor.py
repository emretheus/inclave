import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
import sys

@dataclass
class ExecutionResult:
    """Çalıştırma işleminin sonucunu tutan veri sınıfı."""
    success: bool
    output: str
    error: str
    return_code: int

class CodeExecutor:
    """Üretilen Python kodunu bir alt süreçte (subprocess) çalıştırır ve çıktıları/hataları yakalar."""

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Kodu izole bir alt süreçte çalıştırır. Çıktı veya hata döndürür."""
        
        # 1. Kodu geçici (temp) bir dosyaya yaz
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            tmp_path = f.name

        try:
            # 2. Kodu ayrı bir terminal komutu gibi çalıştır
            result = subprocess.run(
                [sys.executable, tmp_path],  # <-- YENİ: 'python' yerine sys.executable kullan
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.cwd()),  # Göreceli CSV yolları (data/...) çalışsın diye kök dizini hedef gösteriyoruz
            )
            
            # 3. Sonuçları topla ve döndür
            return ExecutionResult(
                success=(result.returncode == 0),
                output=result.stdout[:2000],  # Çıktı çok uzunsa ilk 2000 karakteri al (Terminali boğmamak için)
                error=result.stderr[:2000],   # Hata çok uzunsa ilk 2000 karakteri al
                return_code=result.returncode,
            )
            
        except subprocess.TimeoutExpired:
            # Yapay zeka sonsuz döngü (while True) yazarsa sistemi kilitlenmekten kurtar
            return ExecutionResult(
                success=False, 
                output="", 
                error="Timeout: Kodun çalışması çok uzun sürdü (Zaman Aşımı)", 
                return_code=-1
            )
            
        finally:
            # 4. İşlem bitince geçici dosyayı çöpe at
            Path(tmp_path).unlink(missing_ok=True)