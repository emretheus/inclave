import json
import re
import logging
from dataclasses import dataclass, field
from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import (
    REVIEWER_SYSTEM_PROMPT, 
    REVIEWER_TEMPLATE,
    CODE_IMPROVER_SYSTEM_PROMPT,
    CODE_IMPROVER_TEMPLATE
)

logger = logging.getLogger(__name__)

@dataclass
class ReviewIssue:
    severity: str
    description: str

@dataclass
class ReviewResult:
    issues: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    summary: str = ""
    error: str | None = None

class LocalReviewerAgent:
    def __init__(self):
        self.generator = CodeGenerator()

    def review(self, user_prompt: str, csv_schema: str, code: str) -> ReviewResult:
        """Kodu analiz eder ve sadece hata raporunu (JSON) döner."""
        prompt = REVIEWER_TEMPLATE.format(
            user_prompt=user_prompt,
            csv_schema=csv_schema,
            code=code
        )
        raw_response = self.generator.generate(
            prompt=prompt,
            system_prompt=REVIEWER_SYSTEM_PROMPT
        )
        return self._parse_review(raw_response)

    def improve(self, user_prompt: str, csv_schema: str, original_code: str, review_result: ReviewResult) -> str:
        """
        Hata raporunu alıp, LLM'e göndererek GERÇEK bir kod iyileştirmesi yapar.
        """
        # Sadece kritik hataları özetleyelim
        issues_text = "\n".join([f"- [{i.severity.upper()}] {i.description}" for i in review_result.issues])
        
        prompt = CODE_IMPROVER_TEMPLATE.format(
            original_code=original_code,
            review_summary=issues_text,
            user_prompt=user_prompt,
            csv_schema=csv_schema
        )

        logger.info("Local Reviewer: Kod iyileştirme (improvement) çağrısı yapılıyor...")
        improved_response = self.generator.generate(
            prompt=prompt,
            system_prompt=CODE_IMPROVER_SYSTEM_PROMPT
        )

        # Markdown içinden kodu ayıkla
        return self._extract_code(improved_response)

    def _extract_code(self, text: str) -> str:
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0].strip()
        return text.strip()

    def _parse_review(self, raw_response: str) -> ReviewResult:
        try:
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                data = json.loads(json_match.group())
                issues = [ReviewIssue(severity=i.get("severity", "low"), description=i.get("description", "")) 
                          for i in data.get("issues", [])]
                return ReviewResult(
                    issues=issues,
                    suggestions=data.get("suggestions", []),
                    summary=data.get("summary", "")
                )
        except Exception as e:
            logger.error(f"Reviewer parse hatası: {e}")
        
        return ReviewResult(error="Parse error")