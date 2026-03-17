# Phase 1.2: Intelligence Upgrades — Easy-to-Add Enhancements

> **Goal:** Five modular upgrades that significantly improve code quality, speed, and UX without requiring architectural changes to the Phase 1 core engine.
> **Timeline:** Weeks 4-6 (after Phase 1 core is stable)
> **Prerequisites:** Phase 1 complete — `/generate` endpoint working, RAG pipeline operational, execution feedback loop functional.

---

## Overview: What We Are Adding

These five features layer on top of the existing Phase 1 pipeline. Each one is independent — you can implement them in any order and ship them individually.

```
User uploads CSV + writes prompt
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Enhanced Pipeline (Phase 1.2)                 │
│                                                                  │
│  ★ NEW: Semantic Cache                                          │
│     └─ check if similar query was already answered → instant    │
│                                                                  │
│  ★ NEW: Query Classifier                                        │
│     └─ simple → direct | complex → planning | viz/clean/agg    │
│                                                                  │
│  ★ NEW: Multi-Turn Memory                                       │
│     └─ "now make it a bar chart" → knows previous context       │
│                                                                  │
│  ★ UPGRADED: Hybrid RAG (Vector + BM25)                         │
│     └─ dual retrieval + re-ranking → better context             │
│                                                                  │
│  [existing] Prompt Engine → Ollama → Code                       │
│                                                                  │
│  ★ NEW: Judge Agent                                             │
│     └─ second LLM call validates logic before returning         │
│                                                                  │
│  [existing] Execution Feedback → Self-Healer                    │
│                                                                  │
│  Response: validated, working Python script                     │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency chain:**

```
Any order works, but recommended:

Feature 1: Semantic Cache ──────────────────────────┐
Feature 2: Query Classification ────────────────────┤
Feature 3: Multi-Turn Memory ───────────────────────┼── all independent
Feature 4: Hybrid RAG & Search ─────────────────────┤
Feature 5: Judge Agent ─────────────────────────────┘

Recommended implementation order (easiest first):
  1. Semantic Cache        (fastest win, reduces LLM calls immediately)
  2. Judge Agent           (simple second LLM call, big quality boost)
  3. Query Classification  (routing logic, improves prompt quality)
  4. Hybrid RAG            (upgrades existing retriever)
  5. Multi-Turn Memory     (requires session state, most complex)
```

---

## Technology Additions

| Component | Choice | Why |
|-----------|--------|-----|
| BM25 Search | `rank_bm25` | Pure Python, no extra infrastructure |
| Re-ranker | Cross-encoder via Ollama or `sentence-transformers` | Re-scores top results for precision |
| Session Store | In-memory dict + optional Redis | Simple for MVP, Redis for persistence later |
| Cache Similarity | Cosine similarity on embeddings | Already have embedding infrastructure from Phase 1 |

**New pip dependencies:**

```bash
pip install rank-bm25
```

That's it — everything else uses infrastructure already built in Phase 1 (ChromaDB, Ollama embeddings, FastAPI).

---

## Feature 1: Semantic Cache

> **Goal:** If a user asks something semantically similar to a previous query (on a similar dataset), return the cached result instantly. Skip the entire LLM pipeline. Target: ~70% reduction in LLM calls for repeated/similar queries.

**Owner:** TBD
**Time:** 2-3 days
**Depends on:** Phase 1 vector store (`src/vectordb/store.py`)

### 1.1 How It Works

```
User query arrives
       │
       ▼
┌─────────────────────┐
│  Embed the query    │
│  + schema fingerprint│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────┐
│  Search cache collection    │──── similarity >= 0.92? ──── YES ──→ Return cached code
│  (ChromaDB "semantic_cache")│                                       (skip LLM entirely)
└─────────────────────────────┘
          │ NO
          ▼
    [Normal pipeline]
          │
          ▼
    [Code generated]
          │
          ▼
┌─────────────────────────────┐
│  Save to cache:             │
│  - query embedding          │
│  - schema fingerprint       │
│  - generated code           │
│  - execution result         │
│  - timestamp                │
└─────────────────────────────┘
```

### 1.2 Cache Key Design

The cache key is a composite of:
1. **Query embedding** — the semantic meaning of the user's request
2. **Schema fingerprint** — hash of column names + types (so "sum revenue by city" on different CSVs doesn't return wrong results)

```python
schema_fingerprint = hashlib.md5(
    "|".join(f"{col.name}:{col.dtype}" for col in schema.column_info).encode()
).hexdigest()[:12]
```

This ensures:
- "Show total revenue by city" on `sales_data.csv` → cache hit
- "Show total revenue by city" on `employees.csv` → cache miss (different schema)
- "Display sum of revenue per city" on `sales_data.csv` → cache hit (semantically similar)

### 1.3 Build the Semantic Cache

**File: `src/cache/semantic_cache.py`**

```python
import hashlib
import time
from dataclasses import dataclass
from src.vectordb.store import VectorStore


@dataclass
class CacheEntry:
    query: str
    schema_fingerprint: str
    code: str
    execution_output: str
    created_at: float
    hit_count: int = 0


class SemanticCache:
    """
    Caches query→code mappings using semantic similarity.
    Uses ChromaDB for embedding storage and cosine similarity search.
    """

    SIMILARITY_THRESHOLD = 0.92
    MAX_AGE_SECONDS = 86400 * 7  # 7 days
    MAX_ENTRIES = 1000

    def __init__(self):
        self.store = VectorStore(collection_name="semantic_cache")

    def _make_cache_text(self, query: str, schema_fingerprint: str) -> str:
        return f"[schema:{schema_fingerprint}] {query}"

    def lookup(self, query: str, schema_fingerprint: str) -> CacheEntry | None:
        """
        Search for a semantically similar cached result.
        Returns CacheEntry if found with sufficient similarity, None otherwise.
        """
        cache_text = self._make_cache_text(query, schema_fingerprint)
        results = self.store.search(cache_text, top_k=3)

        for r in results:
            if r["score"] < self.SIMILARITY_THRESHOLD:
                continue

            meta = r["metadata"]
            if meta.get("schema_fingerprint") != schema_fingerprint:
                continue

            age = time.time() - meta.get("created_at", 0)
            if age > self.MAX_AGE_SECONDS:
                continue

            return CacheEntry(
                query=meta.get("original_query", query),
                schema_fingerprint=schema_fingerprint,
                code=meta.get("code", ""),
                execution_output=meta.get("execution_output", ""),
                created_at=meta.get("created_at", 0),
                hit_count=meta.get("hit_count", 0) + 1,
            )

        return None

    def store_result(
        self,
        query: str,
        schema_fingerprint: str,
        code: str,
        execution_output: str = "",
    ):
        """Save a successful generation result to the cache."""
        cache_text = self._make_cache_text(query, schema_fingerprint)
        doc_id = hashlib.md5(f"{query}:{schema_fingerprint}".encode()).hexdigest()

        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[cache_text],
            metadatas=[{
                "original_query": query,
                "schema_fingerprint": schema_fingerprint,
                "code": code,
                "execution_output": execution_output[:500],
                "created_at": time.time(),
                "hit_count": 0,
            }],
        )

    def invalidate(self, schema_fingerprint: str):
        """Remove all cached entries for a specific schema (e.g. when data changes)."""
        # ChromaDB doesn't support delete-by-metadata natively,
        # so we search and delete by ID
        results = self.store.search(f"[schema:{schema_fingerprint}]", top_k=100)
        ids_to_delete = [
            r["id"] for r in results
            if r["metadata"].get("schema_fingerprint") == schema_fingerprint
        ]
        if ids_to_delete:
            self.store.collection.delete(ids=ids_to_delete)

    def stats(self) -> dict:
        return {
            "total_cached": self.store.count(),
            "max_entries": self.MAX_ENTRIES,
            "similarity_threshold": self.SIMILARITY_THRESHOLD,
            "max_age_days": self.MAX_AGE_SECONDS / 86400,
        }
```

### 1.4 Integrate into Pipeline

Update `src/llm/pipeline.py` — add cache check at the beginning of `generate()`:

```python
from src.cache.semantic_cache import SemanticCache

class CodePipeline:
    def __init__(self):
        # ... existing init ...
        self.cache = SemanticCache()

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        # 1. Analyze CSV (needed for cache key too)
        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()
        schema_fp = self._schema_fingerprint(schema)

        # ★ CACHE CHECK — try to return instantly
        cached = self.cache.lookup(user_prompt, schema_fp)
        if cached:
            logger.info(f"Cache HIT (similarity >= {self.cache.SIMILARITY_THRESHOLD})")
            return GenerationResult(
                code=cached.code,
                csv_schema=schema_str,
                rag_context="[from cache]",
                full_prompt="[from cache]",
                raw_response="[from cache]",
                from_cache=True,
            )

        # ... rest of existing pipeline ...

        # ★ CACHE STORE — save successful results
        if result.execution_success:
            self.cache.store_result(
                query=user_prompt,
                schema_fingerprint=schema_fp,
                code=result.code,
                execution_output=result.execution_output,
            )

        return result
```

### 1.5 Cache Tuning Guide

| Parameter | Default | Tune When |
|-----------|---------|-----------|
| `SIMILARITY_THRESHOLD` | 0.92 | Lower (0.85) for more cache hits but risk wrong results. Higher (0.95) for precision. |
| `MAX_AGE_SECONDS` | 7 days | Shorter if knowledge base changes frequently |
| `MAX_ENTRIES` | 1000 | Increase for high-traffic deployments |

### 1.6 Testing the Cache

```python
# test_cache_manual.py
from src.cache.semantic_cache import SemanticCache

cache = SemanticCache()

# Store a result
cache.store_result(
    query="Show total revenue by city",
    schema_fingerprint="abc123",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00\n...",
)

# Test exact match
hit = cache.lookup("Show total revenue by city", "abc123")
assert hit is not None
print(f"Exact match: {hit.code[:50]}...")

# Test semantic similarity (should also hit)
hit = cache.lookup("Display sum of revenue per city", "abc123")
assert hit is not None
print(f"Semantic match: {hit.code[:50]}...")

# Test different schema (should miss)
miss = cache.lookup("Show total revenue by city", "xyz789")
assert miss is None
print("Different schema: cache miss (correct)")

print(f"\nCache stats: {cache.stats()}")
```

### 1.7 Checkpoint

- [ ] Cache stores successful generation results
- [ ] Semantically similar queries return cached code (threshold 0.92)
- [ ] Different schemas produce cache misses
- [ ] Expired entries (>7 days) are not returned
- [ ] API response includes `from_cache: true/false` field
- [ ] Cache reduces average response time by 80%+ for repeat queries

---

## Feature 2: Judge Agent

> **Goal:** After code is generated (and optionally after execution), a second LLM call reviews the code for **logic errors** — things that won't cause runtime exceptions but produce wrong results. Example: using `.mean()` when the user asked for `.sum()`, or grouping by the wrong column.

**Owner:** TBD
**Time:** 2-3 days
**Depends on:** Phase 1 Ollama client (`src/llm/ollama_client.py`)

### 2.1 How It Works

```
Generated code
       │
       ▼
┌──────────────────────┐
│   Execution Feedback │──── runtime error? ──── Self-Healer fixes it
│   (existing Step 6.5)│
└──────────┬───────────┘
           │ code runs OK
           ▼
┌──────────────────────────────────────────┐
│  ★ Judge Agent (second LLM call)         │
│                                           │
│  Input:                                   │
│   - Original user prompt                  │
│   - CSV schema                            │
│   - Generated code                        │
│   - Execution output (stdout)             │
│                                           │
│  Question: "Does this code correctly      │
│  fulfill the user's request?"             │
│                                           │
│  Output:                                  │
│   - verdict: PASS / FAIL / WARN           │
│   - issues: list of logic problems found  │
│   - suggested_fix: corrected code (if FAIL)│
└──────────────────────────────────────────┘
           │
           ├── PASS ──→ Return code to user
           ├── WARN ──→ Return code + warnings
           └── FAIL ──→ Apply fix → re-execute → return
```

### 2.2 What the Judge Catches (vs. What It Doesn't)

| Caught by Judge | Caught by Self-Healer | Neither |
|-----------------|----------------------|---------|
| Wrong aggregation (mean vs sum) | `NameError` (typo in column) | Aesthetic preferences |
| Wrong column in groupby | `ImportError` (missing import) | Performance issues |
| Missing filter condition | `FileNotFoundError` | Style/formatting |
| Incorrect sort order | `SyntaxError` | Edge cases on unseen data |
| Wrong chart type for data | `TypeError` | Security vulnerabilities |
| Off-by-one in date ranges | `KeyError` | |

### 2.3 Build the Judge Agent

**File: `src/llm/judge.py`**

```python
import json
import re
from dataclasses import dataclass
from src.llm.ollama_client import CodeGenerator

JUDGE_SYSTEM_PROMPT = """You are a code review expert. Your job is to verify that
generated Python code correctly fulfills the user's request.

You check for LOGIC errors — things that run without exceptions but produce
wrong results. You do NOT check for style, performance, or formatting.

Respond in this exact JSON format:
{
  "verdict": "PASS" | "FAIL" | "WARN",
  "issues": ["issue 1", "issue 2"],
  "suggested_fix": "corrected code here (only if verdict is FAIL)"
}"""

JUDGE_TEMPLATE = """## User Request
{user_prompt}

## CSV Schema
{csv_schema}

## Generated Code
```python
{code}
```

## Execution Output
{execution_output}

Does this code correctly fulfill the user's request? Check for logic errors:
- Is the right column being used?
- Is the right aggregation function used (sum vs mean vs count)?
- Is the groupby/filter/sort correct?
- Does the output format match what the user asked for?
- Are there any off-by-one or boundary errors?"""


@dataclass
class JudgeVerdict:
    verdict: str        # PASS, FAIL, WARN
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
```

### 2.4 Integrate into Pipeline

Add the judge step after execution feedback in `src/llm/pipeline.py`:

```python
from src.llm.judge import JudgeAgent

class CodePipeline:
    def __init__(self):
        # ... existing init ...
        self.judge = JudgeAgent()

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        # ... existing steps 1-5 ...
        # ... existing execution feedback ...

        # ★ JUDGE STEP — validate logic correctness
        if healed["success"]:
            verdict = self.judge.review(
                user_prompt=user_prompt,
                csv_schema=schema_str,
                code=healed["code"],
                execution_output=healed["output"],
            )

            result.judge_verdict = verdict.verdict
            result.judge_issues = verdict.issues

            if verdict.verdict == "FAIL" and verdict.suggested_fix:
                # Re-execute the judge's suggested fix
                fixed_result = self.healer.run_with_retry(verdict.suggested_fix)
                if fixed_result["success"]:
                    result.code = fixed_result["code"]
                    result.judge_fixed = True

        return result
```

### 2.5 Performance Consideration

The judge adds one extra LLM call per generation. To keep latency acceptable:

| Strategy | When to Apply |
|----------|---------------|
| **Skip judge for cached results** | Always — cached code was already validated |
| **Skip judge for simple queries** | When query classifier says "simple" (Feature 3) |
| **Use a smaller/faster model for judge** | If available (e.g., `qwen2.5-coder:3b` for judge) |
| **Make judge async** | Return code immediately, run judge in background, notify if issues found |

### 2.6 Testing the Judge

```python
# test_judge_manual.py
from src.llm.judge import JudgeAgent

judge = JudgeAgent()

# Test 1: Code that should PASS
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].sum())",
    execution_output="Istanbul  8600.50\nAnkara   5150.00",
)
print(f"Test 1 — Expected PASS, got: {verdict.verdict}")
assert verdict.verdict == "PASS"

# Test 2: Code with wrong aggregation (mean instead of sum)
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('city')['revenue'].mean())",
    execution_output="Istanbul  1720.10\nAnkara   1716.67",
)
print(f"Test 2 — Expected FAIL, got: {verdict.verdict}")
print(f"Issues: {verdict.issues}")

# Test 3: Code with wrong column
verdict = judge.review(
    user_prompt="Show total revenue by city",
    csv_schema="Columns: city(object), revenue(float64), product(object)",
    code="import pandas as pd\ndf = pd.read_csv(csv_path)\nprint(df.groupby('product')['revenue'].sum())",
    execution_output="Widget A  6501.50\nWidget B  7250.00\nWidget C  2475.75",
)
print(f"Test 3 — Expected FAIL, got: {verdict.verdict}")
print(f"Issues: {verdict.issues}")
```

### 2.7 Checkpoint

- [ ] Judge returns PASS for correct code
- [ ] Judge catches wrong aggregation (mean vs sum)
- [ ] Judge catches wrong groupby column
- [ ] Judge's suggested fix is valid Python
- [ ] Pipeline applies judge fix and re-executes when verdict is FAIL
- [ ] API response includes `judge_verdict` and `judge_issues` fields
- [ ] Judge adds <5 seconds latency to total generation time

---

## Feature 3: Query Classification

> **Goal:** Classify incoming queries into categories so the pipeline can route them optimally. Simple queries go direct to LLM (fast path). Complex queries get a planning step first. Visualization, cleaning, and aggregation queries each get specialized prompt templates.

**Owner:** TBD
**Time:** 2-3 days
**Depends on:** Phase 1 Ollama client

### 3.1 Classification Taxonomy

```
User Query
    │
    ├── SIMPLE (direct generation, no planning needed)
    │   Examples: "show first 5 rows", "print column names", "count rows"
    │
    ├── AGGREGATION (groupby, pivot, statistics)
    │   Examples: "total revenue by city", "average salary by department"
    │
    ├── VISUALIZATION (charts, plots, graphs)
    │   Examples: "bar chart of revenue", "scatter plot age vs salary"
    │
    ├── CLEANING (nulls, types, duplicates, transforms)
    │   Examples: "fill missing values", "convert date column", "remove duplicates"
    │
    └── COMPLEX (multi-step, requires planning)
        Examples: "merge two files, clean nulls, group by region, and plot top 10"
```

### 3.2 Why Classification Helps

| Category | What Changes |
|----------|-------------|
| SIMPLE | Skip RAG retrieval, use lighter prompt template, skip judge |
| AGGREGATION | Inject groupby/pivot patterns from RAG, emphasize correct aggregation in prompt |
| VISUALIZATION | Add matplotlib/seaborn patterns, include "save figure" and "show plot" instructions |
| CLEANING | Add data cleaning patterns, emphasize dtype handling and null strategies |
| COMPLEX | Break into sub-steps first, generate code for each step, then combine |

### 3.3 Build the Query Classifier

**File: `src/llm/classifier.py`**

```python
import re
from dataclasses import dataclass
from enum import Enum
from src.llm.ollama_client import CodeGenerator


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

CLASSIFIER_SYSTEM_PROMPT = """Classify this data analysis query into exactly one category.
Respond with ONLY the category name, nothing else.

Categories:
- simple: Basic display/info operations (show rows, describe, column names)
- aggregation: Grouping, pivoting, statistical summaries
- visualization: Charts, plots, graphs, visual outputs
- cleaning: Handling nulls, type conversion, deduplication, transforms
- complex: Multi-step operations requiring planning"""


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
```

### 3.4 Category-Specific Prompt Templates

**File: `src/llm/prompts.py`** — add new templates:

```python
VIZ_SYSTEM_PROMPT = """You are a Python data visualization expert.
You generate clean, runnable Python code using matplotlib and pandas.

Rules:
- Always import matplotlib.pyplot as plt
- Always call plt.tight_layout() before plt.show()
- Use descriptive axis labels and title
- Use appropriate chart type for the data
- For categorical data: bar chart. For time series: line chart.
  For distribution: histogram. For correlation: scatter/heatmap.
- Save figure to 'output.png' AND call plt.show()
- Use a clean style: plt.style.use('seaborn-v0_8-whitegrid')"""

CLEANING_SYSTEM_PROMPT = """You are a Python data cleaning expert.
You generate clean, runnable code for data preprocessing.

Rules:
- Always show before/after comparison (row count, null count)
- Explain each cleaning step with a print statement
- Create a cleaned copy: df_clean = df.copy()
- Save cleaned result to 'cleaned_output.csv'
- Handle encoding issues gracefully"""

AGGREGATION_SYSTEM_PROMPT = """You are a Python data analysis expert.
You generate clean, runnable code for data aggregation.

Rules:
- Use .groupby() with explicit column selection
- Always use .reset_index() after groupby for clean DataFrames
- Name aggregated columns clearly with .agg() and named aggregations
- Sort results by the aggregated value (descending) for readability
- Print results as formatted table"""

COMPLEX_PLANNING_TEMPLATE = """## Task
The user has a complex, multi-step request. Break it into steps and generate code.

## Sub-tasks
{sub_tasks}

## CSV Schema
{csv_schema}

## Relevant Patterns
{rag_context}

Generate a single, complete Python script that performs all steps in order.
Add a print statement between steps to show progress.
Use csv_path variable for the input file."""
```

### 3.5 Integrate into Pipeline

```python
from src.llm.classifier import QueryClassifier, QueryCategory

class CodePipeline:
    def __init__(self):
        # ... existing init ...
        self.classifier = QueryClassifier()

    def generate(self, csv_path: str, user_prompt: str) -> GenerationResult:
        # ★ CLASSIFY first
        classification = self.classifier.classify(user_prompt)
        logger.info(f"Query classified as: {classification.category} "
                     f"(confidence: {classification.confidence}, method: {classification.method})")

        # Route based on category
        system_prompt = self._get_system_prompt(classification.category)
        template = self._get_template(classification.category)
        skip_judge = classification.category == QueryCategory.SIMPLE
        skip_rag = classification.category == QueryCategory.SIMPLE

        # ... rest of pipeline with category-aware prompts ...

    def _get_system_prompt(self, category: QueryCategory) -> str:
        prompts = {
            QueryCategory.SIMPLE: SYSTEM_PROMPT,
            QueryCategory.VISUALIZATION: VIZ_SYSTEM_PROMPT,
            QueryCategory.CLEANING: CLEANING_SYSTEM_PROMPT,
            QueryCategory.AGGREGATION: AGGREGATION_SYSTEM_PROMPT,
            QueryCategory.COMPLEX: SYSTEM_PROMPT,
        }
        return prompts.get(category, SYSTEM_PROMPT)
```

### 3.6 Testing the Classifier

```python
# test_classifier_manual.py
from src.llm.classifier import QueryClassifier, QueryCategory

classifier = QueryClassifier()

test_cases = [
    ("show first 5 rows", QueryCategory.SIMPLE),
    ("bar chart of revenue by city", QueryCategory.VISUALIZATION),
    ("fill missing values with mean", QueryCategory.CLEANING),
    ("total revenue by city and product", QueryCategory.AGGREGATION),
    ("merge with employees, clean nulls, then plot top 10 by salary", QueryCategory.COMPLEX),
    ("count rows", QueryCategory.SIMPLE),
    ("histogram of age distribution", QueryCategory.VISUALIZATION),
    ("remove duplicate entries", QueryCategory.CLEANING),
    ("pivot table by department and quarter", QueryCategory.AGGREGATION),
]

correct = 0
for query, expected in test_cases:
    result = classifier.classify(query)
    match = "✓" if result.category == expected else "✗"
    if result.category == expected:
        correct += 1
    print(f"  {match} '{query}' → {result.category.value} "
          f"(expected: {expected.value}, confidence: {result.confidence:.2f}, method: {result.method})")

print(f"\nAccuracy: {correct}/{len(test_cases)} ({correct/len(test_cases)*100:.0f}%)")
```

### 3.7 Checkpoint

- [ ] Rule-based classification handles 80%+ of common queries without LLM call
- [ ] LLM fallback correctly classifies ambiguous queries
- [ ] COMPLEX queries are broken into sub-tasks
- [ ] Each category uses its specialized system prompt
- [ ] SIMPLE queries skip RAG retrieval and judge (faster response)
- [ ] API response includes `query_category` field
- [ ] Classifier accuracy >= 85% on test suite

---

## Feature 4: Hybrid RAG & Search

> **Goal:** Upgrade the existing vector-only RAG with BM25 keyword search and a re-ranking step. Vector search finds semantically similar content, BM25 finds exact keyword matches. Re-ranking combines both for better retrieval quality.

**Owner:** TBD
**Time:** 3-4 days
**Depends on:** Phase 1 RAG pipeline (`src/rag/retriever.py`)

### 4.1 Why Hybrid?

| Query | Vector Search Finds | BM25 Finds | Best Result |
|-------|-------------------|------------|-------------|
| "how to handle missing data" | Chunks about null handling, imputation | Chunks containing "missing", "NaN", "fillna" | Both contribute |
| "pd.merge on customer_id" | Chunks about joining/merging | Chunks containing exact "pd.merge" text | BM25 wins (exact API name) |
| "combine sales data" | Chunks about merging, concatenating | Nothing (no keyword match) | Vector wins (semantic) |

**Hybrid = Vector handles meaning, BM25 handles exact terms, re-ranker picks the best.**

### 4.2 Architecture

```
User query + schema hint
        │
        ├────────────────┐
        ▼                ▼
  Vector Search     BM25 Search
  (ChromaDB)        (rank_bm25)
  top-K results     top-K results
        │                │
        └───────┬────────┘
                ▼
        Merge & Deduplicate
        (union of both result sets)
                │
                ▼
        ★ Re-Ranker
        (cross-encoder or LLM-based)
        Score each result against the query
                │
                ▼
        Top-N re-ranked results
        (used as RAG context)
```

### 4.3 Build the BM25 Index

**File: `src/rag/bm25_index.py`**

```python
import json
import re
from pathlib import Path
from dataclasses import dataclass
from rank_bm25 import BM25Okapi


@dataclass
class BM25Document:
    doc_id: str
    text: str
    metadata: dict


class BM25Index:
    """
    BM25 keyword search index. Complements vector search
    by finding exact keyword/API name matches.
    """

    def __init__(self):
        self.documents: list[BM25Document] = []
        self.bm25: BM25Okapi | None = None
        self._tokenized_corpus: list[list[str]] = []

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer: lowercase, split on non-alphanumeric, keep underscores."""
        text = text.lower()
        tokens = re.findall(r'[a-z_][a-z0-9_.]*', text)
        return [t for t in tokens if len(t) > 1]

    def build(self, documents: list[BM25Document]):
        """Build the BM25 index from a list of documents."""
        self.documents = documents
        self._tokenized_corpus = [self._tokenize(doc.text) for doc in documents]
        self.bm25 = BM25Okapi(self._tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search using BM25 scoring."""
        if not self.bm25 or not self.documents:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        scored_docs = list(zip(self.documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc, score in scored_docs[:top_k]:
            if score <= 0:
                break
            results.append({
                "id": doc.doc_id,
                "text": doc.text,
                "score": float(score),
                "metadata": doc.metadata,
                "source": "bm25",
            })
        return results

    def save(self, path: str | Path):
        """Persist document list to JSON (BM25 index is rebuilt on load)."""
        data = [{"id": d.doc_id, "text": d.text, "metadata": d.metadata}
                for d in self.documents]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load(self, path: str | Path):
        """Load documents from JSON and rebuild BM25 index."""
        data = json.loads(Path(path).read_text())
        docs = [BM25Document(doc_id=d["id"], text=d["text"], metadata=d["metadata"])
                for d in data]
        self.build(docs)
```

### 4.4 Build the Re-Ranker

**File: `src/rag/reranker.py`**

```python
from src.llm.ollama_client import CodeGenerator


class LLMReranker:
    """
    Re-ranks retrieved chunks using the LLM as a cross-encoder.
    Scores each chunk's relevance to the query on a 0-10 scale.
    """

    RERANK_SYSTEM = """Score how relevant this document is to the query.
Respond with ONLY a number from 0 to 10.
10 = perfectly relevant, 0 = completely irrelevant."""

    RERANK_TEMPLATE = """Query: {query}

Document:
{document}

Relevance score (0-10):"""

    def __init__(self):
        self.generator = CodeGenerator()

    def rerank(self, query: str, results: list[dict], top_n: int = 3) -> list[dict]:
        """
        Re-rank a list of search results by asking the LLM to score each.
        Returns top_n results sorted by relevance score.
        """
        if len(results) <= top_n:
            return results

        scored = []
        for r in results:
            try:
                raw = self.generator.generate(
                    prompt=self.RERANK_TEMPLATE.format(
                        query=query,
                        document=r["text"][:500],
                    ),
                    system_prompt=self.RERANK_SYSTEM,
                )
                score = self._parse_score(raw)
            except Exception:
                score = r.get("score", 0.5)

            scored.append({**r, "rerank_score": score})

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_n]

    def _parse_score(self, raw: str) -> float:
        """Extract a numeric score from LLM response."""
        import re
        match = re.search(r'(\d+(?:\.\d+)?)', raw.strip())
        if match:
            score = float(match.group(1))
            return min(max(score / 10.0, 0.0), 1.0)
        return 0.5


class SimpleReranker:
    """
    Lightweight re-ranker that combines vector and BM25 scores
    using Reciprocal Rank Fusion (RRF). No LLM call needed.

    Use this for low-latency scenarios; use LLMReranker for higher quality.
    """

    def rerank(self, results: list[dict], top_n: int = 3, k: int = 60) -> list[dict]:
        """
        Reciprocal Rank Fusion: combines rankings from multiple sources.
        RRF(d) = Σ 1/(k + rank_i(d))
        """
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        # Group by source (vector vs bm25)
        sources: dict[str, list[dict]] = {}
        for r in results:
            source = r.get("source", "vector")
            sources.setdefault(source, []).append(r)
            doc_map[r["id"]] = r

        # Calculate RRF scores
        for source, docs in sources.items():
            docs.sort(key=lambda x: x["score"], reverse=True)
            for rank, doc in enumerate(docs):
                rrf = 1.0 / (k + rank + 1)
                doc_scores[doc["id"]] = doc_scores.get(doc["id"], 0) + rrf

        ranked = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return [
            {**doc_map[doc_id], "rerank_score": score}
            for doc_id, score in ranked[:top_n]
        ]
```

### 4.5 Build the Hybrid Retriever

**File: `src/rag/hybrid_retriever.py`**

```python
from src.vectordb.store import VectorStore
from src.rag.bm25_index import BM25Index, BM25Document
from src.rag.reranker import SimpleReranker, LLMReranker
from src.rag.chunking import MarkdownCodeChunker
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Combines vector search (semantic) + BM25 (keyword) with re-ranking.
    Drop-in replacement for the Phase 1 KnowledgeRetriever.
    """

    def __init__(self, use_llm_reranker: bool = False):
        self.vector_store = VectorStore(collection_name="knowledge")
        self.bm25_index = BM25Index()
        self.reranker = LLMReranker() if use_llm_reranker else SimpleReranker()
        self._bm25_built = False

    def build_bm25_index(self, force: bool = False):
        """Build BM25 index from the same knowledge documents used by vector store."""
        bm25_path = settings.chroma_persist_dir / "bm25_docs.json"

        if not force and bm25_path.exists():
            self.bm25_index.load(bm25_path)
            self._bm25_built = True
            logger.info(f"BM25 index loaded: {len(self.bm25_index.documents)} docs")
            return

        chunker = MarkdownCodeChunker()
        chunks = chunker.chunk_directory(settings.knowledge_dir)

        docs = [
            BM25Document(doc_id=c.id, text=c.text, metadata=c.metadata)
            for c in chunks
        ]
        self.bm25_index.build(docs)
        self.bm25_index.save(bm25_path)
        self._bm25_built = True
        logger.info(f"BM25 index built: {len(docs)} docs")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.3,
        schema_hint: str = "",
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> str:
        """
        Hybrid retrieval: vector + BM25, merged and re-ranked.
        Returns formatted context string for prompt injection.
        """
        enriched_query = query
        if schema_hint:
            enriched_query = f"{query} | {schema_hint}"

        # Vector search (semantic similarity)
        vector_results = self.vector_store.search(enriched_query, top_k=top_k * 2)
        for r in vector_results:
            r["source"] = "vector"
            r["score"] = r["score"] * vector_weight

        # BM25 search (keyword matching)
        bm25_results = []
        if self._bm25_built:
            bm25_results = self.bm25_index.search(query, top_k=top_k * 2)
            for r in bm25_results:
                max_bm25 = max((x["score"] for x in bm25_results), default=1.0)
                r["score"] = (r["score"] / max_bm25) * bm25_weight if max_bm25 > 0 else 0

        # Merge and deduplicate
        all_results = vector_results + bm25_results
        seen_ids = set()
        unique_results = []
        for r in all_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)

        if not unique_results:
            return ""

        # Re-rank
        reranked = self.reranker.rerank(unique_results, top_n=top_k)

        # Filter by minimum score
        relevant = [r for r in reranked if r.get("rerank_score", r["score"]) >= min_score]

        if not relevant:
            return ""

        # Format as context string
        context_parts = []
        for r in relevant:
            source = r.get("source", "hybrid")
            title = r.get("metadata", {}).get("title", "Reference")
            context_parts.append(f"### {title} [{source}]\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)
```

### 4.6 Integrate into Pipeline

Replace the existing `KnowledgeRetriever` with `HybridRetriever`:

```python
# In src/llm/pipeline.py
from src.rag.hybrid_retriever import HybridRetriever

class CodePipeline:
    def __init__(self):
        # ... existing init ...
        self.retriever = HybridRetriever(use_llm_reranker=False)
        self.retriever.build_bm25_index()
```

### 4.7 Performance Comparison

Run the same test queries with both retrievers and compare:

```python
# test_hybrid_vs_vector.py
from src.rag.retriever import KnowledgeRetriever
from src.rag.hybrid_retriever import HybridRetriever

vector_only = KnowledgeRetriever()
hybrid = HybridRetriever(use_llm_reranker=False)
hybrid.build_bm25_index()

test_queries = [
    "pd.read_csv encoding parameter",      # exact API name → BM25 should help
    "how to handle missing data",           # semantic → vector should help
    "groupby sum reset_index",              # mix of API names + concept
    "convert string column to datetime",    # both should find relevant chunks
    "df.merge on customer_id",              # exact API name → BM25 wins
]

for q in test_queries:
    v_result = vector_only.retrieve(q, top_k=3)
    h_result = hybrid.retrieve(q, top_k=3)
    print(f"\nQuery: {q}")
    print(f"  Vector only: {len(v_result)} chars")
    print(f"  Hybrid:      {len(h_result)} chars")
    # Manual inspection: which context is more relevant?
```

### 4.8 Checkpoint

- [ ] BM25 index builds from the same knowledge documents as vector store
- [ ] BM25 search returns results for exact keyword queries (e.g., "pd.merge")
- [ ] Hybrid retriever combines both result sets without duplicates
- [ ] Re-ranker (RRF) produces better ordering than either source alone
- [ ] Hybrid retriever is a drop-in replacement for `KnowledgeRetriever`
- [ ] End-to-end generation quality improves (measure on test suite from Step 8)
- [ ] No significant latency increase (< 500ms added)

---

## Feature 5: Multi-Turn Memory

> **Goal:** Enable conversational interactions where the user can refer to previous queries and results. "Make this a bar chart" should know that "this" refers to the previous groupby result. The agent maintains context across turns within a session.

**Owner:** TBD
**Time:** 3-4 days
**Depends on:** Phase 1 pipeline working

### 5.1 How It Works

```
Turn 1: "Show total revenue by city"
         → generates groupby code
         → saves to session memory

Turn 2: "Now make it a bar chart"
         → session memory provides:
           - previous query
           - previous generated code
           - previous CSV schema
         → prompt includes: "The user previously asked for X and got Y.
           Now they want to modify it."
         → generates code that builds on the previous result
```

### 5.2 Session Memory Design

```python
Session {
    session_id: str,
    created_at: datetime,
    csv_path: str,
    csv_schema: CSVSchema,
    turns: [
        Turn {
            turn_id: int,
            user_prompt: str,
            query_category: str,
            generated_code: str,
            execution_output: str,
            success: bool,
            timestamp: datetime,
        },
        ...
    ]
}
```

### 5.3 Build the Session Manager

**File: `src/memory/session.py`**

```python
import uuid
import time
from dataclasses import dataclass, field


@dataclass
class Turn:
    turn_id: int
    user_prompt: str
    query_category: str
    generated_code: str
    execution_output: str
    success: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    session_id: str
    csv_path: str
    csv_schema_str: str
    turns: list[Turn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def last_turn(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    @property
    def last_successful_turn(self) -> Turn | None:
        for turn in reversed(self.turns):
            if turn.success:
                return turn
        return None

    def add_turn(self, **kwargs) -> Turn:
        turn = Turn(turn_id=self.turn_count + 1, **kwargs)
        self.turns.append(turn)
        return turn

    def get_context_window(self, max_turns: int = 3) -> list[Turn]:
        """Return the last N turns for context injection."""
        return self.turns[-max_turns:]


class SessionManager:
    """
    Manages conversation sessions. In-memory for MVP,
    can be backed by Redis or a database later.
    """

    MAX_SESSIONS = 100
    SESSION_TTL = 3600  # 1 hour

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, csv_path: str, csv_schema_str: str) -> Session:
        """Create a new conversation session."""
        self._cleanup_expired()

        session_id = str(uuid.uuid4())[:8]
        session = Session(
            session_id=session_id,
            csv_path=csv_path,
            csv_schema_str=csv_schema_str,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session and (time.time() - session.created_at) > self.SESSION_TTL:
            del self._sessions[session_id]
            return None
        return session

    def _cleanup_expired(self):
        """Remove expired sessions and enforce max limit."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if (now - s.created_at) > self.SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]

        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(self._sessions.values(), key=lambda s: s.created_at)
            del self._sessions[oldest.session_id]

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "csv_path": s.csv_path,
                "turns": s.turn_count,
                "created_at": s.created_at,
            }
            for s in self._sessions.values()
        ]
```

### 5.4 Build the Context Assembler

**File: `src/memory/context.py`**

```python
from src.memory.session import Session, Turn

MULTI_TURN_CONTEXT_TEMPLATE = """## Conversation History
The user has been working with the same CSV file. Here is the recent context:

{history}

## Current Request
The user now says: "{current_prompt}"

Generate code that fulfills the current request. You may build upon
or modify the previous code if the user is referring to it.
Important: The new code should be a complete, standalone script
(include all imports and csv_path loading)."""

REFERENCE_DETECTION_KEYWORDS = [
    "this", "that", "it", "the same", "previous",
    "above", "last", "again", "also", "modify",
    "change", "update", "instead", "but", "now",
    "make it", "turn it", "convert it",
]


class ConversationContextAssembler:
    """
    Assembles conversation history into a prompt-injectable context block.
    Detects when the user is referencing previous turns.
    """

    def is_follow_up(self, prompt: str) -> bool:
        """Detect if the current prompt references previous context."""
        lower = prompt.lower()
        return any(kw in lower for kw in REFERENCE_DETECTION_KEYWORDS)

    def build_context(self, session: Session, current_prompt: str) -> str | None:
        """
        Build conversation context for multi-turn prompts.
        Returns None if this appears to be a standalone query.
        """
        if not session.turns:
            return None

        if not self.is_follow_up(current_prompt):
            return None

        window = session.get_context_window(max_turns=3)
        history_parts = []

        for turn in window:
            status = "succeeded" if turn.success else "failed"
            part = f"Turn {turn.turn_id}: User asked: \"{turn.user_prompt}\"\n"
            part += f"Status: {status}\n"
            if turn.success and turn.generated_code:
                code_preview = turn.generated_code[:500]
                part += f"Generated code:\n```python\n{code_preview}\n```\n"
            if turn.execution_output:
                output_preview = turn.execution_output[:300]
                part += f"Output:\n```\n{output_preview}\n```"
            history_parts.append(part)

        history = "\n---\n".join(history_parts)

        return MULTI_TURN_CONTEXT_TEMPLATE.format(
            history=history,
            current_prompt=current_prompt,
        )
```

### 5.5 Integrate into Pipeline

```python
from src.memory.session import SessionManager
from src.memory.context import ConversationContextAssembler

class CodePipeline:
    def __init__(self):
        # ... existing init ...
        self.session_mgr = SessionManager()
        self.context_assembler = ConversationContextAssembler()

    def generate(
        self,
        csv_path: str,
        user_prompt: str,
        session_id: str | None = None,
    ) -> GenerationResult:

        # Get or create session
        session = None
        if session_id:
            session = self.session_mgr.get_session(session_id)

        schema = self.analyzer.analyze(csv_path)
        schema_str = schema.to_prompt_string()

        if not session:
            session = self.session_mgr.create_session(csv_path, schema_str)

        # Check if this is a follow-up turn
        conversation_context = self.context_assembler.build_context(session, user_prompt)

        if conversation_context:
            # Multi-turn: inject conversation history into prompt
            logger.info(f"Multi-turn detected (session: {session.session_id}, "
                         f"turn: {session.turn_count + 1})")
            enhanced_prompt = conversation_context
        else:
            enhanced_prompt = user_prompt

        # ... rest of pipeline uses enhanced_prompt ...

        # Save this turn to session
        session.add_turn(
            user_prompt=user_prompt,
            query_category=classification.category.value if classification else "unknown",
            generated_code=result.code,
            execution_output=result.execution_output or "",
            success=result.execution_success,
        )

        result.session_id = session.session_id
        result.turn_number = session.turn_count
        return result
```

### 5.6 Update API Routes

```python
# In src/api/routes.py — update the /generate endpoint

@app.post("/generate")
async def generate_code(
    csv_file: UploadFile = File(...),
    prompt: str = Form(...),
    session_id: str | None = Form(None),  # ★ NEW: optional session ID
):
    # ... existing file handling ...

    result = pipeline.generate(
        csv_path=tmp_path,
        user_prompt=prompt,
        session_id=session_id,
    )

    return {
        "code": result.code,
        "csv_schema": result.csv_schema,
        "rag_context_used": bool(result.rag_context),
        "session_id": result.session_id,       # ★ return for next turn
        "turn_number": result.turn_number,
        "is_follow_up": result.turn_number > 1,
    }
```

### 5.7 CLI Multi-Turn Mode

Update `cli.py` to support conversations:

```python
def interactive_mode(csv_path: str):
    """Interactive multi-turn conversation mode."""
    pipeline = CodePipeline()
    session_id = None

    print(f"CSV loaded: {csv_path}")
    print("Type your prompts (Ctrl+C to exit):")
    print("Each prompt can reference previous results.\n")

    while True:
        try:
            prompt = input(f"[turn {turn}] >>> " if session_id else ">>> ")
            if not prompt.strip():
                continue

            result = pipeline.generate(csv_path, prompt, session_id=session_id)
            session_id = result.session_id

            if result.turn_number > 1:
                print(f"  (follow-up on turn {result.turn_number - 1})")

            print(f"\n{result.code}\n")
        except KeyboardInterrupt:
            print("\nBye.")
            break
```

### 5.8 Example Conversation

```
>>> Show total revenue by city
import pandas as pd
csv_path = 'data/sample_csvs/sales_data.csv'
df = pd.read_csv(csv_path)
result = df.groupby('city')['revenue'].sum().sort_values(ascending=False)
print(result)

[turn 2] >>> Now make it a bar chart
  (follow-up on turn 1)
import pandas as pd
import matplotlib.pyplot as plt
csv_path = 'data/sample_csvs/sales_data.csv'
df = pd.read_csv(csv_path)
result = df.groupby('city')['revenue'].sum().sort_values(ascending=False)
result.plot(kind='bar', title='Total Revenue by City')
plt.ylabel('Revenue')
plt.tight_layout()
plt.savefig('output.png')
plt.show()

[turn 3] >>> Add a horizontal line for the average
  (follow-up on turn 2)
import pandas as pd
import matplotlib.pyplot as plt
csv_path = 'data/sample_csvs/sales_data.csv'
df = pd.read_csv(csv_path)
result = df.groupby('city')['revenue'].sum().sort_values(ascending=False)
ax = result.plot(kind='bar', title='Total Revenue by City')
avg = result.mean()
ax.axhline(y=avg, color='red', linestyle='--', label=f'Average: {avg:,.0f}')
plt.ylabel('Revenue')
plt.legend()
plt.tight_layout()
plt.savefig('output.png')
plt.show()
```

### 5.9 Checkpoint

- [ ] Session is created on first query and returned in response
- [ ] Follow-up queries are detected (keywords like "this", "make it", "now")
- [ ] Conversation history is injected into the prompt for follow-ups
- [ ] Generated code builds upon previous results
- [ ] Session expires after 1 hour of inactivity
- [ ] API accepts optional `session_id` parameter
- [ ] CLI supports multi-turn conversations
- [ ] Non-follow-up queries in the same session work normally (no unwanted context)

---

## Integration: Putting All Five Features Together

### Updated Pipeline Flow

```
Request arrives (CSV + prompt + optional session_id)
    │
    ▼
[1] Schema Analyzer (existing)
    │
    ▼
[2] ★ Semantic Cache check ──── HIT? ──→ Return instantly
    │ MISS
    ▼
[3] ★ Query Classifier ──→ determines category + skip flags
    │
    ▼
[4] ★ Multi-Turn Memory ──→ enriches prompt with conversation history
    │
    ▼
[5] ★ Hybrid RAG (vector + BM25 + re-rank) ──→ retrieves context
    │
    ▼
[6] Prompt Assembly (existing, now category-aware)
    │
    ▼
[7] Ollama Generation (existing)
    │
    ▼
[8] Code Extraction (existing)
    │
    ▼
[9] Execution Feedback + Self-Healer (existing)
    │
    ▼
[10] ★ Judge Agent ──→ validates logic ──→ may trigger re-generation
    │
    ▼
[11] ★ Cache Store (save successful result)
    │
    ▼
[12] ★ Session Store (save turn to memory)
    │
    ▼
Response (code + metadata + session_id)
```

### Updated API Response Format

```json
{
  "code": "import pandas as pd\n...",
  "csv_schema": "File: sales_data.csv (11 rows, 8 columns)...",
  "rag_context_used": true,

  "from_cache": false,
  "query_category": "aggregation",
  "session_id": "a1b2c3d4",
  "turn_number": 2,
  "is_follow_up": true,

  "judge_verdict": "PASS",
  "judge_issues": [],
  "execution_success": true,
  "execution_attempts": 1,

  "retrieval_method": "hybrid",
  "cache_stats": {
    "total_cached": 47,
    "hit_rate": "32%"
  }
}
```

### Updated Project Structure

```
src/
├── api/
│   └── routes.py              (updated with session_id param)
├── cache/
│   └── semantic_cache.py      ★ NEW
├── csv_engine/
│   └── schema_analyzer.py     (unchanged)
├── llm/
│   ├── classifier.py          ★ NEW
│   ├── executor.py            (unchanged)
│   ├── judge.py               ★ NEW
│   ├── ollama_client.py       (unchanged)
│   ├── pipeline.py            (updated: integrates all features)
│   ├── prompts.py             (updated: category-specific templates)
│   └── self_healer.py         (unchanged)
├── memory/
│   ├── context.py             ★ NEW
│   └── session.py             ★ NEW
├── rag/
│   ├── bm25_index.py          ★ NEW
│   ├── chunking.py            (unchanged)
│   ├── few_shot_store.py      (unchanged)
│   ├── hybrid_retriever.py    ★ NEW
│   ├── indexer.py             (updated: also builds BM25 index)
│   ├── reranker.py            ★ NEW
│   └── retriever.py           (kept as fallback, replaced by hybrid)
├── vectordb/
│   └── store.py               (unchanged)
└── config.py                  (updated with new settings)
```

---

## Testing Plan

### Unit Tests per Feature

| Feature | Test File | Key Tests |
|---------|-----------|-----------|
| Semantic Cache | `tests/test_semantic_cache.py` | cache hit, cache miss, schema mismatch, expiry |
| Judge Agent | `tests/test_judge.py` | correct code passes, wrong agg fails, fix applied |
| Query Classifier | `tests/test_classifier.py` | 9 category tests, rule vs LLM fallback |
| Hybrid RAG | `tests/test_hybrid_retriever.py` | BM25 index build, hybrid vs vector-only |
| Multi-Turn Memory | `tests/test_session.py` | session CRUD, follow-up detection, context assembly |

### Integration Test: Full Pipeline with All Features

```python
# tests/test_integration_phase1_2.py

def test_full_pipeline_with_all_features():
    pipeline = CodePipeline()

    # Turn 1: aggregation query
    r1 = pipeline.generate("data/sample_csvs/sales_data.csv",
                           "Show total revenue by city")
    assert r1.execution_success
    assert r1.query_category == "aggregation"
    session_id = r1.session_id

    # Turn 2: follow-up visualization
    r2 = pipeline.generate("data/sample_csvs/sales_data.csv",
                           "Now make it a bar chart",
                           session_id=session_id)
    assert r2.is_follow_up
    assert "plt" in r2.code or "plot" in r2.code

    # Turn 3: repeat query → should hit cache
    r3 = pipeline.generate("data/sample_csvs/sales_data.csv",
                           "Show total revenue by city")
    assert r3.from_cache

    # Verify judge ran (not on cached result)
    assert r1.judge_verdict in ("PASS", "WARN")
```

---

## Success Criteria

Phase 1.2 is **DONE** when:

- [ ] **Semantic Cache:** 70%+ of repeated/similar queries served from cache (<100ms)
- [ ] **Judge Agent:** Catches wrong aggregation/groupby errors in 80%+ of test cases
- [ ] **Query Classifier:** 85%+ accuracy on classification test suite
- [ ] **Hybrid RAG:** Measurable improvement in retrieval relevance vs. vector-only
- [ ] **Multi-Turn Memory:** 3-turn conversations produce correct, context-aware code
- [ ] All five features work together without conflicts
- [ ] No regression in Phase 1 test scenarios (still 7/10+ pass)
- [ ] Average response time: <5s for cached, <15s for fresh generation with judge

---

## What NOT to Build in Phase 1.2

Save for Phase 2/3:

- Long-term memory across sessions (user preferences, learned patterns)
- GPU-accelerated re-ranker (use Ollama for now)
- Distributed cache (Redis/Memcached) — in-memory ChromaDB is enough
- Fine-tuned classifier model — rule-based + Ollama is sufficient
- Streaming judge feedback — batch is fine for now
- Multi-user session isolation — single-user MVP first

---

*Last updated: 2026-03-16*
