import json
import re
import logging
from dataclasses import dataclass
from src.config import JUDGE_PROVIDER, JUDGE_API_KEY, JUDGE_MODEL, JUDGE_PASS_THRESHOLD
from src.judge.providers import JudgeProvider, GroqProvider, GeminiProvider, OpenRouterProvider
from src.llm.prompts import CLOUD_JUDGE_SYSTEM, CLOUD_JUDGE_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class JudgeScore:
    correctness: float
    intent_alignment: float
    code_quality: float
    overall: float
    feedback: str
    passed: bool
    raw_response: str
    error: str | None = None

class CloudJudgeAgent:
    """
    Independent code evaluation using a cloud LLM.
    Scores code on a 0-10 scale across three dimensions.
    """

    def __init__(self):
        self.threshold = JUDGE_PASS_THRESHOLD
        self.provider = self._init_provider()

    def _init_provider(self) -> JudgeProvider | None:
        """Configures the correct HTTP provider based on settings."""
        if not JUDGE_API_KEY:
            logger.warning("Cloud Judge is enabled but JUDGE_API_KEY is empty. Judge will be disabled.")
            return None

        if JUDGE_PROVIDER == "groq":
            return GroqProvider(JUDGE_API_KEY, JUDGE_MODEL)
        elif JUDGE_PROVIDER == "gemini":
            return GeminiProvider(JUDGE_API_KEY, JUDGE_MODEL)
        elif JUDGE_PROVIDER == "openrouter":
            return OpenRouterProvider(JUDGE_API_KEY, JUDGE_MODEL)
        else:
            logger.warning(f"Unknown JUDGE_PROVIDER '{JUDGE_PROVIDER}'. Cloud Judge disabled.")
            return None

    def evaluate(self, user_prompt: str, csv_schema: str, code: str, execution_success: bool, execution_output: str) -> JudgeScore:
        """Calls the cloud API to score the generated code."""
        if not self.provider:
            return JudgeScore(0, 0, 0, 0, "Judge Disabled (Missing API Key or Invalid Provider)", False, "", error="Disabled")

        prompt = CLOUD_JUDGE_TEMPLATE.format(
            user_prompt=user_prompt,
            csv_schema=csv_schema,
            code=code,
            execution_success=execution_success,
            output_length=len(execution_output)
        )

        try:
            logger.info(f"Cloud Judge ({JUDGE_PROVIDER}) kod puanlaması yapıyor...")
            raw_response = self.provider.chat(
                system_prompt=CLOUD_JUDGE_SYSTEM,
                user_prompt=prompt
            )
            return self._parse_score(raw_response)
        except Exception as e:
            logger.error(f"Cloud Judge Error: {e}")
            # Graceful degradation
            return JudgeScore(0, 0, 0, 0, f"Network/API Error: {str(e)}", False, "", error=str(e))

    def _parse_score(self, raw_response: str) -> JudgeScore:
        """Parses the JSON score and calculates the weighted overall score."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                data = json.loads(json_match.group())
                
                # Extract scores (default to 0 if missing)
                c_score = float(data.get("correctness", 0))
                i_score = float(data.get("intent_alignment", 0))
                q_score = float(data.get("code_quality", 0))
                
                # Calculate weighted overall score
                # correctness (40%), intent_alignment (40%), code_quality (20%)
                overall = (c_score * 0.4) + (i_score * 0.4) + (q_score * 0.2)
                
                return JudgeScore(
                    correctness=c_score,
                    intent_alignment=i_score,
                    code_quality=q_score,
                    overall=round(overall, 2),
                    feedback=data.get("feedback", "No feedback provided."),
                    passed=overall >= self.threshold,
                    raw_response=raw_response
                )
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.error(f"Failed to parse Cloud Judge response: {e}")
            pass

        # Fallback if parsing fails
        return JudgeScore(0, 0, 0, 0, "Failed to parse judge output.", False, raw_response, error="Parse Error")