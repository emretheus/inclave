from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import SYSTEM_PROMPT, GENERATION_TEMPLATE, GENERATION_TEMPLATE_NO_RAG
from src.llm.code_validator import CodeValidator
from src.csv_engine.schema_analyzer import SchemaAnalyzer
from src.rag.retriever import KnowledgeRetriever
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    code: str
    csv_schema: str
    rag_context: str
    full_prompt: str
    raw_response: str
    warnings: list


class CodePipeline:
    """
    Main orchestrator. Takes CSV path + user prompt → returns generated Python code.

    Flow:
    1. Analyze CSV → extract schema
    2. Query RAG → find relevant pandas patterns
    3. Assemble prompt → system + schema + RAG context + user request
    4. Send to Ollama → get generated code
    5. Clean response → extract code block if wrapped in markdown
    6. Validate → auto-fix missing imports
    """

    def __init__(self):
        self.generator = CodeGenerator()
        self.analyzer = SchemaAnalyzer()
        self.retriever = KnowledgeRetriever()

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        # 1. Analyze CSV
        logger.info(f"Analyzing CSV: {csv_path}")
        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()

        # 2. Retrieve relevant patterns
        logger.info(f"Retrieving context for: {user_prompt}")
        rag_context = self.retriever.retrieve(user_prompt, top_k=3)

        # 3. Assemble prompt
        if rag_context:
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

        # 4. Generate code
        logger.info("Sending to Ollama...")
        raw_response = self.generator.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        # 5. Clean response
        code = self._extract_code(raw_response)
        
        # 6. Validate and fix
        code, warnings = CodeValidator.validate(code)
        if warnings:
            for w in warnings:
                logger.warning(w)


        return GenerationResult(
            code=code,
            csv_schema=schema_str,
            rag_context=rag_context,
            full_prompt=prompt,
            raw_response=raw_response,
            warnings=warnings,
        )

    def _extract_code(self, response: str) -> str:
        """Extract Python code from response, handling markdown code blocks."""
        # Try to find ```python ... ``` blocks
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        # Try generic ``` blocks
        pattern = r'```\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        # No code blocks found, return as-is
        return response.strip()