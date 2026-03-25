import re
from dataclasses import dataclass
from enum import Enum
from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import CLASSIFIER_SYSTEM_PROMPT

class QueryCategory(str, Enum):
    SIMPLE = "simple"
    AGGREGATION = "aggregation"
    VISUALIZATION = "visualization"
    CLEANING = "cleaning"
    COMPLEX = "complex"

@dataclass
class ClassificationResult:
    category: QueryCategory
    confidence: float       # 0.0 - 1.0
    sub_tasks: list[str]    # only populated for COMPLEX
    method: str             # "rule" or "llm"

# Rule-based patterns (fast, no LLM call needed)
RULE_PATTERNS: dict[QueryCategory, list[str]] = {
    QueryCategory.SIMPLE: [
        r"\b(show|display|print|list|head|tail|first|last)\b.*\b(rows?|columns?|names?|shape|info|dtypes?)\b",
        r"\b(count|len|size|number of)\b.*\b(rows?|columns?|entries)\b",
        r"\b(describe|summary|statistics|stats)\b",
    ],
    QueryCategory.VISUALIZATION: [
        r"\b(plot|chart|graph|histogram|scatter|bar\s*chart|line\s*chart|pie\s*chart|heatmap|boxplot|violin)\b",
        r"\b(visuali[sz]e|draw|create.*chart)\b",
        r"\b(matplotlib|seaborn|plotly)\b",
    ],
    QueryCategory.CLEANING: [
        r"\b(clean|fill|drop|remove|handle|fix|impute)\b.*\b(null|nan|missing|duplicate|na)\b",
        r"\b(convert|cast|change|transform)\b.*\b(type|dtype|datetime|numeric|string|int|float)\b",
        r"\b(rename|replace|strip|trim|normalize)\b.*\b(column|value)\b",
        r"\b(encode|one.?hot|label.?encod|dummy)\b",
    ],
    QueryCategory.AGGREGATION: [
        r"\b(group\s*by|groupby|aggregate|agg)\b",
        r"\b(sum|total|average|mean|median|count|min|max)\b.*\b(by|per|each|for every)\b",
        r"\b(pivot|crosstab|cross.?tabul)\b",
    ],
}

COMPLEX_INDICATORS = [
    r"\b(and then|after that|next|finally|step \d|first.*then)\b",
    r"\b(merge|join|combine)\b.*\b(and|then)\b",
    r"(\b\w+\b.*){4,}",  # 4+ action verbs suggest multi-step
]


class QueryClassifier:
    """
    Two-tier classifier: fast rule-based matching first,
    falls back to LLM classification for ambiguous queries.
    """

    def __init__(self):
        self.generator = CodeGenerator()

    def classify(self, query: str) -> ClassificationResult:
        """Classify a user query. Tries rules first, LLM as fallback."""

        # Tier 1: Rule-based (instant, no LLM call)
        rule_result = self._classify_by_rules(query)
        if rule_result and rule_result.confidence >= 0.8:
            return rule_result

        # Tier 2: LLM-based (slower, handles ambiguous cases)
        return self._classify_by_llm(query)

    def _classify_by_rules(self, query: str) -> ClassificationResult | None:
        lower = query.lower()

        # Check for complex indicators first
        complex_score = sum(
            1 for p in COMPLEX_INDICATORS if re.search(p, lower, re.IGNORECASE)
        )
        if complex_score >= 2:
            return ClassificationResult(
                category=QueryCategory.COMPLEX,
                confidence=min(0.7 + complex_score * 0.1, 0.95),
                sub_tasks=self._extract_sub_tasks(query),
                method="rule",
            )

        # Check each category
        scores: dict[QueryCategory, int] = {}
        for category, patterns in RULE_PATTERNS.items():
            match_count = sum(
                1 for p in patterns if re.search(p, lower, re.IGNORECASE)
            )
            if match_count > 0:
                scores[category] = match_count

        if not scores:
            return None

        best = max(scores, key=scores.get)
        confidence = min(0.6 + scores[best] * 0.15, 0.95)
        return ClassificationResult(
            category=best,
            confidence=confidence,
            sub_tasks=[],
            method="rule",
        )

    def _classify_by_llm(self, query: str) -> ClassificationResult:
        raw = self.generator.generate(
            prompt=f"Query: {query}",
            system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        ).strip().lower()

        category_map = {
            "simple": QueryCategory.SIMPLE,
            "aggregation": QueryCategory.AGGREGATION,
            "visualization": QueryCategory.VISUALIZATION,
            "cleaning": QueryCategory.CLEANING,
            "complex": QueryCategory.COMPLEX,
        }

        for key, cat in category_map.items():
            if key in raw:
                sub_tasks = []
                if cat == QueryCategory.COMPLEX:
                    sub_tasks = self._extract_sub_tasks(query)
                return ClassificationResult(
                    category=cat,
                    confidence=0.7,
                    sub_tasks=sub_tasks,
                    method="llm",
                )

        return ClassificationResult(
            category=QueryCategory.SIMPLE,
            confidence=0.5,
            sub_tasks=[],
            method="llm",
        )

    def _extract_sub_tasks(self, query: str) -> list[str]:
        """Break a complex query into sub-tasks using the LLM."""
        raw = self.generator.generate(
            prompt=f"Break this into numbered sub-steps (max 5):\n{query}",
            system_prompt="List sub-steps as numbered items. Be concise. No code.",
        )
        steps = re.findall(r'\d+[.)] (.+)', raw)
        return steps[:5]