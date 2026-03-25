from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import (
    SYSTEM_PROMPT, 
    GENERATION_TEMPLATE, 
    GENERATION_TEMPLATE_NO_RAG,
    VIZ_SYSTEM_PROMPT, 
    CLEANING_SYSTEM_PROMPT, 
    AGGREGATION_SYSTEM_PROMPT,
    COMPLEX_PLANNING_TEMPLATE,
    RERANK_SYSTEM,
    RERANK_TEMPLATE,
    MULTI_TURN_CONTEXT_TEMPLATE,
    REFERENCE_DETECTION_KEYWORDS )
from src.csv_engine.schema_analyzer import SchemaAnalyzer
from src.rag.hybrid_retriever import HybridRetriever
from src.llm.self_healer import SelfHealer  
from dataclasses import dataclass, field
import re
import logging
from src.rag.few_shot_store import FewShotStore
from src.cache.semantic_cache import SemanticCache
from src.llm.judge import JudgeAgent
from src.llm.classifier import QueryClassifier, QueryCategory
from src.memory.session import SessionManager
from src.memory.context import ConversationContextAssembler

logger = logging.getLogger(__name__)

@dataclass
class GenerationResult:
    """Üretim ve test sürecinin tüm sonuçlarını saklayan veri sınıfı."""
    code: str
    csv_schema: str
    rag_context: str
    full_prompt: str
    raw_response: str
    
    execution_success: bool = False
    attempts: int = 0
    execution_output: str = ""
    execution_error: str = ""
    from_cache: bool = False

    judge_verdict: str = "N/A"
    judge_issues: list[str] = field(default_factory=list)
    judge_fixed: bool = False

    query_category: str = "unknown"

    session_id: str | None = None
    is_follow_up: bool = False
    turn_number: int = 0

    retrieval_method: str = "vector"  # vector, bm25 veya hybrid
    cache_stats: dict = field(default_factory=dict)

class CodePipeline:
    """Ana Orkestra Şefi. Artık kodu üretmekle kalmıyor, çalıştırıp test de ediyor!"""

    def __init__(self):
        self.generator = CodeGenerator()
        self.analyzer = SchemaAnalyzer()

        self.retriever = HybridRetriever(use_llm_reranker=False)
        self.retriever.build_bm25_index()

        self.few_shot = FewShotStore()
        self.healer = SelfHealer()
        self.cache = SemanticCache()
        self.judge = JudgeAgent()
        self.classifier = QueryClassifier()

        self.session_mgr = SessionManager()
        self.context_assembler = ConversationContextAssembler()

    def generate(self, csv_path: str, user_prompt: str, session_id: str | None = None) -> GenerationResult:
        # 1. CSV'yi Analiz Et
        logger.info(f"CSV analiz ediliyor: {csv_path}")
        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()
        schema_fp = schema.get_fingerprint()

        # ---  OTURUM (SESSION) YÖNETİMİ ---
        session = None
        if session_id:
            session = self.session_mgr.get_session(session_id)

        if not session:
            session = self.session_mgr.create_session(csv_path, schema_str)

        # ---  ÇOKLU-TUR (MULTI-TURN) KONTROLÜ ---
        conversation_context = self.context_assembler.build_context(session, user_prompt)

        if conversation_context:
            logger.info(f"🧠 Çoklu-tur algılandı (Oturum: {session.session_id}, Tur: {session.turn_count + 1})")
            enhanced_prompt = conversation_context
        else:
            enhanced_prompt = user_prompt

        # --- CACHE KONTROLÜ ---
        # Eğer çoklu-tur (sohbet devamı) ise cache'i atlıyoruz çünkü bağlam farklıdır.
        if not conversation_context:
            cached = self.cache.lookup(user_prompt, schema_fp)
            if cached:
                logger.info(f"⚡ CACHE HIT! '{user_prompt}' sorusu hafızadan bulundu.")
                
                # Cache'den de dönse, hafızaya sohbet adımı olarak kaydediyoruz
                session.add_turn(
                    user_prompt=user_prompt,
                    query_category="cached",
                    generated_code=cached.code,
                    execution_output=cached.execution_output,
                    success=True
                )
                
                return GenerationResult(
                    code=cached.code,
                    csv_schema=schema_str,
                    rag_context="[from cache]",
                    full_prompt="[from cache]",
                    raw_response="[from cache]",
                    execution_success=True,
                    execution_output=cached.execution_output,
                    from_cache=True,
                    judge_verdict="PASS (Cached)",
                    query_category="cached",
                    session_id=session.session_id,
                    turn_number=session.turn_count,
                    is_follow_up = session.turn_count > 1,
                    cache_stats=self.cache.stats(),
                    retrieval_method="semantic_cache"
                )

        # --- SINIFLANDIRMA (CLASSIFY) ---
        classification = self.classifier.classify(user_prompt)
        category = classification.category
        logger.info(f"Sorgu Sınıflandırıldı: {category.value.upper()} (Güven: {classification.confidence:.2f})")

        skip_rag = (category == QueryCategory.SIMPLE)
        skip_judge = (category == QueryCategory.SIMPLE)

        # 2. İlgili kalıpları (RAG) getir
        rag_context = ""
        if not skip_rag:
            logger.info(f"Sorgu için bağlam (context) aranıyor: {user_prompt}")
            rag_context = self.retriever.retrieve(user_prompt, top_k=3, schema_hint=schema_str)
        else:
            logger.info("Basit sorgu (SIMPLE). RAG bypass ediliyor.")

        similar_code = self.few_shot.find_similar(user_prompt)
        if similar_code:
            logger.info("🧠 Hafızada anlamsal olarak benzer bir başarılı kod bulundu!")
            few_shot_context = f"Here is a proven working code for a similar past request. Adapt it if needed:\n```python\n{similar_code}\n```"
        else:
            few_shot_context = "No past examples available."

        # 3. Prompt'u (İstemi) birleştir
        template_str = self._get_template(category, bool(rag_context))

        if category == QueryCategory.COMPLEX:
            prompt = template_str.format(
                sub_tasks="\n".join([f"- {task}" for task in classification.sub_tasks]),
                csv_schema=schema_str,
                rag_context=rag_context if rag_context else "No external context.",
            )
        else:
            prompt = template_str.format(
                rag_context=rag_context if rag_context else "No external context.",
                csv_schema=schema_str,
                user_prompt=user_prompt,
                file_path=csv_path,  
                few_shot_context=few_shot_context,
            )

        # 4. Kodu Üret (Ollama)
        system_prompt_to_use = self._get_system_prompt(category)
        logger.info(f"İlk kod taslağı Ollama'ya yazdırılıyor... (Şablon: {category.value.upper()})")
        
        raw_response = self.generator.generate(
            prompt=prompt,
            system_prompt=system_prompt_to_use,
        )

        # 5. Yanıtı Temizle (Sadece kodu al)
        initial_code = self._extract_code(raw_response)

        # 6. SANDBOX & SELF-HEALING ---
        logger.info("Üretilen kod Sandbox'ta test ediliyor (Kendi kendini iyileştirme döngüsü)...")
        healed = self.healer.run_with_retry(initial_code)

        judge_verdict_str = "N/A"
        judge_issues_list = []
        judge_fixed_bool = False

        # EĞER KOD BAŞARIYLA ÇALIŞTIYSA İKİ HAFIZAYA DA KAYDET
        if healed["success"]:
            if skip_judge:
                logger.info("Basit sorgu olduğu için Hakem (Judge) bypass edildi.")
                judge_verdict_str = "PASS"
            else:
                logger.info("Kod hatasız çalıştı. Mantık Hakemi (Judge) inceliyor...")
                verdict = self.judge.review(
                    user_prompt=user_prompt,
                    csv_schema=schema_str,
                    code=healed["code"],
                    execution_output=healed.get("output", "")
                )
                
                judge_verdict_str = verdict.verdict
                judge_issues_list = verdict.issues
                logger.info(f"Hakem Kararı: {judge_verdict_str}")

                if verdict.verdict == "FAIL" and verdict.suggested_fix:
                    logger.warning("Hakem mantık hatası buldu! Düzeltme uygulanıyor...")
                    # Hakemin düzeltmesini tekrar Sandbox'a atıyoruz!
                    fixed_healed = self.healer.run_with_retry(verdict.suggested_fix)
                    
                    if fixed_healed["success"]:
                        logger.info("Hakemin düzeltmesi başarıyla çalıştı!")
                        healed = fixed_healed  # Orijinal kodu hakemin koduyla değiştir
                        judge_fixed_bool = True
                        judge_verdict_str = "PASS"
                    else:
                        logger.error("Hakemin düzeltmesi de patladı. Orijinal koda geri dönülüyor.")

        # Hafızalara Kayıt (Few-Shot & Semantic Cache)
        if healed["success"] and "FAIL" not in judge_verdict_str:
            self.few_shot.save(
                query=user_prompt, 
                schema_summary=schema_str[:200], 
                code=healed["code"]
            )
            # Çoklu-tur sorularını global Cache'e atmak kafa karıştırabilir, ama orijinal prompt ile kaydedebiliriz
            if not conversation_context:
                self.cache.store_result(
                    query=user_prompt, 
                    schema_fingerprint=schema_fp, 
                    code=healed["code"],
                    execution_output=healed.get("output", "")
                )

        # ---  BU TURU OTURUMA KAYDET (Oturum Geçmişi) ---
        session.add_turn(
            user_prompt=user_prompt,
            query_category=category.value,
            generated_code=healed["code"],
            execution_output=healed.get("output", ""),
            success=healed["success"],
        )

        return GenerationResult(
            code=healed["code"],
            csv_schema=schema_str,
            rag_context=rag_context,
            full_prompt=prompt,
            raw_response=raw_response,
            execution_success=healed["success"],
            attempts=healed["attempts"],
            execution_output=healed.get("output", ""),
            execution_error=healed.get("last_error", ""),
            from_cache=False,
            judge_verdict=judge_verdict_str,
            judge_issues=judge_issues_list,
            judge_fixed=judge_fixed_bool,
            query_category=category.value,
            session_id=session.session_id,
            turn_number=session.turn_count,
            is_follow_up = session.turn_count > 1,
            retrieval_method="hybrid" if rag_context else "direct",
            cache_stats=self.cache.stats()
        )
    
    def _get_system_prompt(self, category: QueryCategory) -> str:
        """Kategoriye uygun uzmanlık promptunu seçer."""
        prompts = {
            QueryCategory.SIMPLE: SYSTEM_PROMPT,
            QueryCategory.VISUALIZATION: VIZ_SYSTEM_PROMPT,
            QueryCategory.CLEANING: CLEANING_SYSTEM_PROMPT,
            QueryCategory.AGGREGATION: AGGREGATION_SYSTEM_PROMPT,
            QueryCategory.COMPLEX: SYSTEM_PROMPT,
        }
        return prompts.get(category, SYSTEM_PROMPT)

    def _get_template(self, category: QueryCategory, has_rag: bool) -> str:
        """Kategoriye ve RAG durumuna göre formatlanacak şablonu seçer."""
        if category == QueryCategory.COMPLEX:
            return COMPLEX_PLANNING_TEMPLATE
        if has_rag:
            return GENERATION_TEMPLATE
        return GENERATION_TEMPLATE_NO_RAG

    def _extract_code(self, response: str) -> str:
        """Yapay zekanın yanıtından sadece Python kodunu Regex ile çıkarır."""
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        pattern = r'```\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        return response.strip()