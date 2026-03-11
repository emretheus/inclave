import re
import logging
from dataclasses import dataclass, field
from typing import List

from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import (
    SYSTEM_PROMPT,
    GENERATION_TEMPLATE,
    GENERATION_TEMPLATE_NO_RAG,
    GENERATION_TEMPLATE_WITH_EXAMPLE,
)
from src.csv_engine.schema_analyzer import SchemaAnalyzer
from src.rag.retriever import KnowledgeRetriever
from src.rag.few_shot_store import FewShotStore
from src.llm.self_healer import SelfHealer

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    code: str
    csv_schema: str
    rag_context: str
    full_prompt: str
    raw_response: str
    execution_success: bool | None = None
    execution_output: str = ""
    attempts: int = 0
    plot_paths: list[str] = field(default_factory=list)


class CodePipeline:
    """
    Main orchestrator: CSV path + user prompt -> generated Python code.

    Flow:
    1. Analyze CSV -> extract schema
    2. Check few-shot store for similar past successes
    3. Query RAG -> find relevant pandas patterns
    4. Assemble prompt -> system + schema + RAG context + user request
    5. Send to Ollama -> get generated code
    6. Clean response -> extract code block if wrapped in markdown
    7. Execute and self-heal if needed
    8. Save successful results to few-shot store
    """

    def __init__(self, auto_execute: bool = True):
        self.generator = CodeGenerator()
        self.analyzer = SchemaAnalyzer()
        self.retriever = KnowledgeRetriever()
        self.few_shot = FewShotStore()
        self.healer = SelfHealer(max_attempts=3)
        self.auto_execute = auto_execute

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        logger.info(f"Analyzing CSV: {csv_path}")
        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()

        # Schema hint for enriched retrieval
        col_hints = ", ".join(
            f"{c.name}({c.dtype})" for c in schema.column_info
        )

        logger.info(f"Retrieving context for: {user_prompt}")
        rag_context = self.retriever.retrieve(
            user_prompt, top_k=3, schema_hint=col_hints
        )

        few_shot_example = self.few_shot.find_similar(user_prompt)

        if few_shot_example and rag_context:
            prompt = GENERATION_TEMPLATE_WITH_EXAMPLE.format(
                few_shot_example=few_shot_example,
                rag_context=rag_context,
                csv_schema=schema_str,
                user_prompt=user_prompt,
            )
        elif rag_context:
            prompt = GENERATION_TEMPLATE.format(
                rag_context=rag_context,
                csv_schema=schema_str,
                user_prompt=user_prompt,
            )
        else:
            prompt = GENERATION_TEMPLATE_NO_RAG.format(
                csv_schema=schema_str,
                user_prompt=user_prompt,
            )

        logger.info("Sending to Ollama...")
        raw_response = self.generator.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        code = self._extract_code(raw_response)

        # Inject csv_path at the top so the code can actually run
        if "csv_path" in code and not re.search(
            r"^csv_path\s*=", code, re.MULTILINE
        ):
            code = f'csv_path = "{csv_path}"\n\n{code}'

        result = GenerationResult(
            code=code,
            csv_schema=schema_str,
            rag_context=rag_context,
            full_prompt=prompt,
            raw_response=raw_response,
        )

        if self.auto_execute:
            logger.info("Running code with self-healing...")
            healed = self.healer.run_with_retry(code)
            result.code = healed["code"]
            result.execution_success = healed["success"]
            result.execution_output = healed.get("output", "")
            result.attempts = healed["attempts"]
            result.plot_paths = healed.get("plot_paths", [])

            if healed["success"]:
                self.few_shot.save(
                    query=user_prompt,
                    schema_summary=schema_str[:200],
                    code=healed["code"],
                )

        return result

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
