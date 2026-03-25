import json
import re
from dataclasses import dataclass
from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import JUDGE_SYSTEM_PROMPT, JUDGE_TEMPLATE


@dataclass
class JudgeVerdict:
    verdict: str  # PASS, FAIL, WARN
    issues: list[str]
    suggested_fix: str  # empty if PASS
    raw_response: str

class JudgeAgent:
    """
    Second LLM call that validates generated code for logic correctness.
    Uses the same Ollama model but with a different system prompt.
    """

    def __init__(self):
        self.generator = CodeGenerator()

    def review(
        self,
        user_prompt: str,
        csv_schema: str,
        code: str,
        execution_output: str = "",
    ) -> JudgeVerdict:
        """Review generated code and return verdict."""

        prompt = JUDGE_TEMPLATE.format(
            user_prompt=user_prompt,
            csv_schema=csv_schema,
            code=code,
            execution_output=execution_output[:1000],
        )

        raw = self.generator.generate(
            prompt=prompt,
            system_prompt=JUDGE_SYSTEM_PROMPT,
        )

        return self._parse_verdict(raw)

    def _parse_verdict(self, raw_response: str) -> JudgeVerdict:
        """Parse the LLM's JSON response into a structured verdict."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                data = json.loads(json_match.group())
                return JudgeVerdict(
                    verdict=data.get("verdict", "WARN").upper(),
                    issues=data.get("issues", []),
                    suggested_fix=data.get("suggested_fix", ""),
                    raw_response=raw_response,
                )
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: if JSON parsing fails, look for keywords
        upper = raw_response.upper()
        if "FAIL" in upper:
            verdict = "FAIL"
        elif "WARN" in upper:
            verdict = "WARN"
        else:
            verdict = "PASS"

        return JudgeVerdict(
            verdict=verdict,
            issues=[raw_response[:200]],
            suggested_fix="",
            raw_response=raw_response,
        )