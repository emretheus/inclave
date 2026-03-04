"""
Ollama client wrapper.
Sends prompts to the local Ollama server and returns generated code.
"""
import ollama
from src.config import OLLAMA_BASE_URL, CODE_MODEL


class CodeGenerator:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        self.model = CODE_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to Ollama and return the response text.

        Args:
            prompt: What you want the model to do (e.g., "Write a function that...")
            system_prompt: Instructions for how the model should behave

        Returns:
            The model's response as a string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0.1,      # Low = more predictable code output
                "num_predict": 2048,      # Max length of response
            },
        )
        return response["message"]["content"]

    def health_check(self) -> bool:
        """Check if Ollama is running and our model is available."""
        try:
            self.client.show(self.model)
            return True
        except Exception:
            return False
