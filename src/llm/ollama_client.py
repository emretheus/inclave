import ollama
from src.config import settings


class CodeGenerator:
    """Sends prompts to the local Ollama server and returns generated code."""

    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.model = settings.code_model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0.1,
                "num_predict": 2048,
            },
        )
        return response["message"]["content"]

    def health_check(self) -> bool:
        try:
            self.client.show(self.model)
            return True
        except Exception:
            return False
