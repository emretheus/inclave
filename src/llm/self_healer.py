import re
from src.llm.ollama_client import CodeGenerator
from src.llm.executor import CodeExecutor
from src.llm.prompts import FIX_PROMPT


class SelfHealer:
    """Try to run code; if it fails, send error back to LLM to fix. Max N attempts."""

    def __init__(self, max_attempts: int = 3):
        self.executor = CodeExecutor()
        self.generator = CodeGenerator()
        self.max_attempts = max_attempts

    def run_with_retry(self, code: str) -> dict:
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            result = self.executor.execute(code)

            if result.success:
                return {
                    "code": code,
                    "success": True,
                    "attempts": attempt,
                    "output": result.output,
                    "last_error": None,
                    "plot_paths": result.plot_paths,
                }

            last_error = result.error

            if attempt < self.max_attempts:
                raw = self.generator.generate(
                    prompt=FIX_PROMPT.format(code=code, error=result.error),
                    system_prompt="You are a Python expert. Fix the code. Return ONLY code.",
                )
                code = self._extract_code(raw)

        return {
            "code": code,
            "success": False,
            "attempts": self.max_attempts,
            "output": "",
            "last_error": last_error,
            "plot_paths": [],
        }

    def _extract_code(self, response: str) -> str:
        pattern = r"```python\s*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        pattern = r"```\s*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        return response.strip()
