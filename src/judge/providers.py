import httpx
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class JudgeProvider(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Sends a request to the cloud LLM and returns the text response."""
        pass

class GroqProvider(JudgeProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            # Force JSON mode explicitly for Groq
            # "response_format": {"type": "json_object"} 
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            # HATANIN GERÇEK SEBEBİNİ YAKALA VE GÖSTER!
            error_detail = e.response.text
            logger.error(f"Groq API HTTP Hatası: {e} | Detay: {error_detail}")
            raise Exception(f"Groq HTTP Hatası: {e}\nDetay: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Groq Ağ Bağlantı Hatası: {e}")
            raise Exception(f"Groq'a bağlanılamadı: {e}")

class GeminiProvider(JudgeProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        # Gemini uses a slightly different URL structure
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        headers = {"Content-Type": "application/json"}
        # Gemini format is specific
        data = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": temperature}
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.url, headers=headers, json=data)
                response.raise_for_status()
                # Assuming the standard text response structure for Gemini
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"Gemini API HTTP Hatası: {e} | Detay: {error_detail}")
            raise Exception(f"Gemini HTTP Hatası: {e}\nDetay: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Gemini Ağ Bağlantı Hatası: {e}")
            raise Exception(f"Gemini'ye bağlanılamadı: {e}")

class OpenRouterProvider(JudgeProvider):
     def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

     def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501", # Optional but recommended by OpenRouter
            "X-Title": "AI Code Engine" # Optional
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"OpenRouter API HTTP Hatası: {e} | Detay: {error_detail}")
            raise Exception(f"OpenRouter HTTP Hatası: {e}\nDetay: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"OpenRouter Ağ Bağlantı Hatası: {e}")
            raise Exception(f"OpenRouter'a bağlanılamadı: {e}")