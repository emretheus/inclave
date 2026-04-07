# 1. ADIM: DOSYANIN EN ÜSTÜNE ŞU İKİ KÜTÜPHANEYİ EKLE:
import sys
import subprocess

# ... (Mevcut diğer importların ve FIX_PROMPT değişkenin aynı kalacak) ...

class SelfHealer:
    # ... (__init__ ve _extract_code metodların aynı kalacak) ...

    # 2. ADIM: _extract_code METODUNUN BİTTİĞİ YERE, HEMEN ALTINA BU YENİ METODU EKLE:
    def _auto_install_missing_module(self, error_message: str) -> bool:
        """ModuleNotFoundError hatasını yakalar ve eksik paketi arka planda pip ile kurar."""
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", error_message)
        if not match:
            return False
            
        module_name = match.group(1)
        
        # Bazen import adı ile pip yükleme adı farklıdır, bunları eşleştiriyoruz
        pip_mapping = {
            "sklearn": "scikit-learn",
            "bs4": "beautifulsoup4",
            "cv2": "opencv-python",
            "PIL": "Pillow"
        }
        
        install_name = pip_mapping.get(module_name, module_name)
        
        print(f"📦 [Auto-Install] Eksik kütüphane tespit edildi. '{install_name}' arka planda indiriliyor...")
        try:
            # sys.executable, aktif olan sanal ortamın (.venv) pip'ini kullanmayı garanti eder
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                print(f"✅ [Auto-Install] '{install_name}' başarıyla kuruldu! Koda devam ediliyor.")
                return True
            else:
                print(f"❌ [Auto-Install] Kurulum başarısız: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ [Auto-Install] Sistem hatası: {e}")
            return False


    # 3. ADIM: MEVCUT "run_with_retry" METODUNU TAMAMEN SİL VE YERİNE BUNU YAPIŞTIR:
    def run_with_retry(self, code: str) -> dict:
        """
        Döngü halinde kodu çalıştırır ve hataları düzeltir.
        Dönüş formatı: {code, success, attempts, output, last_error}
        """
        result = None
        attempt = 1

        # For döngüsü yerine While kullanıyoruz (Kütüphane kurulduğunda deneme hakkımız yanmasın diye)
        while attempt <= self.max_attempts:
            # Kodu Sandbox'ta çalıştır
            result = self.executor.execute(code)

            # Başarılıysa döngüden çık
            if result.success:
                return {
                    "code": code,
                    "success": True,
                    "attempts": attempt,
                    "output": result.output,
                    "last_error": None,
                }

            # --- YENİ EKLENEN KISIM: KÜTÜPHANE KONTROLÜ ---
            if result.error and "ModuleNotFoundError" in result.error:
                is_installed = self._auto_install_missing_module(result.error)
                if is_installed:
                    # Kütüphane kuruldu, 'attempt' artırmadan kodu tekrar dene!
                    continue
            # -----------------------------------------------

            # Başarısız olduysa ve son hakkımız değilse, LLM'den düzeltmesini iste
            if attempt < self.max_attempts:
                print(f"[Self-Healer] Deneme {attempt} başarısız oldu. Hata LLM'e gönderiliyor...")

                raw_response = self.generator.generate(
                    prompt=FIX_PROMPT.format(code=code, error=result.error),
                    system_prompt="You are a Python expert. Fix the code. Return ONLY code.",
                )
                code = self._extract_code(raw_response)

            attempt += 1

        # Tüm denemeler bitti ve başarı sağlanamadı
        return {
            "code": code,
            "success": False,
            "attempts": self.max_attempts,
            "output": result.output if result else None,
            "last_error": result.error if result else None,
        }