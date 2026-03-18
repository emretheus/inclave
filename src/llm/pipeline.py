from src.llm.classifier import QueryClassifier, QueryCategory
from src.llm.judge import JudgeAgent
from src.cache.semantic_cache import SemanticCache
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
    judge_verdict: str = "SKIPPED"
    judge_issues: list = None


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
        self.cache = SemanticCache()
        self.judge = JudgeAgent()
        self.classifier = QueryClassifier() 

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        # 1. Analyze CSV
        logger.info(f"Analyzing CSV: {csv_path}")
        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()
        schema_fp = self._schema_fingerprint(schema)

        # ★ CACHE CHECK — return instantly if similar query exists
        cached = self.cache.lookup(user_prompt, schema_fp)
        if cached:
            logger.info("Cache HIT — returning cached result")
            return GenerationResult(
                code=cached.code,
                csv_schema=schema_str,
                rag_context="[from cache]",
                full_prompt="[from cache]",
                raw_response="[from cache]",
                warnings=[],
            )

        # ★ CLASSIFY — determine query type for routing
        classification = self.classifier.classify(user_prompt)
        logger.info(f"Query classified as: {classification.category.value} "
                    f"(confidence: {classification.confidence:.2f}, method: {classification.method})")

        # Skip RAG for simple queries — faster response
        skip_rag = classification.category == QueryCategory.SIMPLE
        skip_judge = classification.category == QueryCategory.SIMPLE

        # 2. Retrieve relevant patterns
        logger.info(f"Retrieving context for: {user_prompt}")
        rag_context = ""
        if not skip_rag:
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

        # ★ JUDGE STEP — validate logic correctness & skip for simple queries
        if not skip_judge:
            verdict = self.judge.review(
                user_prompt=user_prompt,
                csv_schema=schema_str,
                code=code,
            )
            logger.info(f"Judge verdict: {verdict.verdict}")

            if verdict.verdict == "FAIL" and verdict.suggested_fix:
                logger.info("Judge found issues — applying suggested fix")
                code = verdict.suggested_fix
                code, warnings = CodeValidator.validate(code)

        else:
            logger.info("Simple query — skipping judge")

        # ★ CACHE STORE — save for future similar queries
        self.cache.store_result(
            query=user_prompt,
            schema_fingerprint=schema_fp,
            code=code,
        )

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

    def _schema_fingerprint(self, schema) -> str:
        """Create a unique fingerprint for a CSV schema."""
        import hashlib
        content = "|".join(
            f"{col.name}:{col.dtype}" for col in schema.column_info
        )
        return hashlib.md5(content.encode()).hexdigest()[:12]