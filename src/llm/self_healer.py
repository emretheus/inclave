import re
from src.llm.ollama_client import CodeGenerator
from src.llm.executor import CodeExecutor
from src.config import MAX_HEAL_ATTEMPTS

FIX_PROMPT = """The following Python code produced an error. Fix it.

Code:
```python
{code}
```
Error:
{error}

Return ONLY the fixed Python code, no explanations."""


class SelfHealer:
    """Kodu çalıştırmayı dener. Eğer hata verirse (fail), hatayı LLM'e gönderip kodu düzelttirir. Maksimum 3 deneme yapar."""

    def __init__(self, max_attempts: int = MAX_HEAL_ATTEMPTS):
        self.executor = CodeExecutor()
        self.generator = CodeGenerator()
        self.max_attempts = max_attempts

    def _extract_code(self, response: str) -> str:
        pattern = r'```(?:python)?\s*\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            return match.group(1).strip()

        return response.strip()

    def run_with_retry(self, code: str) -> dict:
        """
        Döngü halinde kodu çalıştırır ve hataları düzeltir.
        Dönüş formatı: {code, success, attempts, output, last_error}
        """
        result = None  # max_attempts <= 0 durumuna karşı güvenlik

        for attempt in range(1, self.max_attempts + 1):
            # 1. Kodu Sandbox'ta çalıştır
            result = self.executor.execute(code)

            # 2. Eğer başarılıysa, mükemmel! Döngüden çık ve sonucu döndür.
            if result.success:
                return {
                    "code": code,
                    "success": True,
                    "attempts": attempt,
                    "output": result.output,
                    "last_error": None,
                }

            # 3. Başarısız olduysa ve henüz son hakkımız değilse, LLM'den düzeltmesini iste
            if attempt < self.max_attempts:
                print(f"[Self-Healer] Deneme {attempt} başarısız oldu. Hata LLM'e gönderiliyor...")

                raw_response = self.generator.generate(
                    prompt=FIX_PROMPT.format(code=code, error=result.error),
                    system_prompt="You are a Python expert. Fix the code. Return ONLY code.",
                )

                code = self._extract_code(raw_response)

        # 4. Tüm denemeler tükendiyse son durumu döndür
        return {
            "code": code,
            "success": False,
            "attempts": self.max_attempts,
            "output": result.output if result else None,
            "last_error": result.error if result else None,
        }