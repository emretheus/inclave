"""Ollama client wrapper.
Sends prompts to the local Ollama server and returns generated code.
"""
import ollama
from src.config import OLLAMA_BASE_URL, CODE_MODEL

class CodeGenerator:
    def __init__(self):
        # Config dosyasından gelen URL ile istemciyi başlatıyoruz
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        self.model = CODE_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Ollama'ya bir prompt gönderir, yanıtı temizler (markdown'dan arındırır) ve döner.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Hata aldığın yer burasıydı, şimdi parametreler tam:
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0.1,
                "num_predict": 2048,
            },
        )
        
        content = response["message"]["content"]

        # --- Markdown Temizleme (Sanitization) ---
        # Eğer model kodu ```python ... ``` blokları içine aldıysa, 
        # sadece içindeki saf kodu ayıklıyoruz.
        if "```" in content:
            lines = content.split("\n")
            # İçinde ``` geçen satırları (başlangıç ve bitiş bloklarını) atla
            cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
            content = "\n".join(cleaned_lines).strip()
            
        return content

    def health_check(self) -> bool:
        """Ollama sunucusunun ve seçilen modelin hazır olup olmadığını kontrol eder."""
        try:
            self.client.show(self.model)
            return True
        except Exception:
            return False