# Phase 1.2: Two-Mode Intelligence + Chat UI

> **Goal:** Add intelligent code review and evaluation with two operation modes, plus a simple chat interface for end users.
> **Timeline:** Weeks 4-5 (after Phase 1 core is stable)
> **Prerequisites:** Phase 1 complete — `/generate` endpoint working, RAG pipeline operational, execution feedback loop functional.

---

## Overview: What We Are Building

Two operation modes managed via `.env`, plus a chat UI that ties everything together.

```
User uploads CSV + writes prompt (or chats)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Enhanced Pipeline (Phase 1.2)                       │
│                                                                  │
│  [1] Semantic Cache                                             │
│      └─ similar query answered before? → return instantly       │
│                                                                  │
│  [2] Query Classifier (rule-based + LLM fallback)              │
│      └─ simple → skip review/judge | complex → full pipeline   │
│                                                                  │
│  [3] Code Generation (Ollama — always local)                    │
│      └─ RAG context + few-shot + schema → code                 │
│                                                                  │
│  [4] Code Validator                                             │
│      └─ auto-fix missing imports, syntax check                  │
│                                                                  │
│  [5] Execute + Self-Heal (max 3 attempts)                       │
│                                                                  │
│  [6] Review & Evaluation (MODE-DEPENDENT)                       │
│      ├─ MODE=local  → Local Reviewer Agent (Ollama)             │
│      └─ MODE=cloud  → Cloud Judge (Groq) + Local Reviewer      │
│                                                                  │
│  [7] Chat UI (Streamlit) — conversational interface             │
│                                                                  │
│  Response: validated, reviewed Python script + feedback          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Two Operation Modes

### Mode 1: `local` — Fully Offline

Everything runs on your machine. No internet needed after setup.

```
Code Generation: Ollama (qwen2.5-coder)
Code Review:     Ollama (same model, reviewer prompt)
Judge:           DISABLED
Privacy:         100% local — no data leaves your machine
```

**Best for:** Privacy-sensitive data, offline environments, air-gapped systems.

### Mode 2: `cloud` — Cloud-Enhanced

Code generation stays local, but evaluation uses a free cloud LLM for independent scoring.

```
Code Generation: Ollama (qwen2.5-coder) — LOCAL
Code Review:     Ollama (reviewer prompt) — LOCAL
Judge:           Groq / Gemini / OpenRouter — CLOUD (free tier)
Privacy:         Code + schema sent to cloud judge (NO raw CSV data)
```

**Best for:** Better evaluation quality, independent scoring (avoids self-evaluation bias).

### Configuration via `.env`

```env
# Mode: "local" or "cloud"
PIPELINE_MODE=local

# Cloud Judge (only used when PIPELINE_MODE=cloud)
JUDGE_PROVIDER=groq
JUDGE_API_KEY=your_groq_api_key_here
JUDGE_MODEL=
JUDGE_PASS_THRESHOLD=6.0
```

---

## Feature List

| # | Feature | New/Upgraded | Complexity |
|---|---------|-------------|------------|
| 1 | Semantic Cache | NEW | Easy |
| 2 | Query Classifier | NEW | Easy |
| 3 | Code Validator | NEW | Easy |
| 4 | Local Reviewer Agent | NEW | Medium |
| 5 | Cloud Judge Agent | NEW | Medium |
| 6 | Two-Mode Pipeline | NEW | Medium |
| 7 | Chat UI (Streamlit) | NEW | Medium |

**Dependency chain:**

```
Feature 1: Semantic Cache ──────────┐
Feature 2: Query Classifier ────────┤
Feature 3: Code Validator ──────────┼── independent, any order
Feature 4: Local Reviewer Agent ────┤
Feature 5: Cloud Judge Agent ───────┘
                                    │
Feature 6: Two-Mode Pipeline ───────┤── integrates 1-5
Feature 7: Chat UI ─────────────────┘── uses pipeline
```

---

## Technology Additions

| Component | Choice | Why |
|-----------|--------|-----|
| Cloud Judge | Groq free tier (Llama 3.3 70B) | Fastest free inference, OpenAI-compatible API |
| HTTP Client | httpx | Lightweight, no SDK lock-in |
| Cache | ChromaDB (reuse existing) | Already have embedding infrastructure |
| Classifier | Rule-based + LLM fallback | Rules are instant, LLM handles edge cases |

**No new infrastructure.** Everything builds on Phase 1's existing stack.

---

## Feature 1: Semantic Cache

> **Goal:** Skip LLM calls entirely when a very similar query was already answered for the same CSV.

**File:** `src/cache/semantic_cache.py`

### How It Works

```
User query + CSV schema fingerprint
        │
        ▼
┌─ Embed query ──→ Search cache (cosine ≥ 0.92) ──→ HIT? Return code
│                                                      │
│                                              MISS? Continue pipeline
```

- Uses ChromaDB embeddings (same as RAG)
- Cache key = query embedding + schema fingerprint (MD5 of column names + types)
- Threshold: 0.92 cosine similarity (very close match required)
- TTL: 7 days (auto-expire old entries)
- Schema-aware: same query on different CSVs = cache miss

### Implementation

```python
@dataclass
class CacheEntry:
    query: str
    schema_fingerprint: str
    code: str
    execution_output: str
    created_at: float

class SemanticCache:
    SIMILARITY_THRESHOLD = 0.92
    MAX_AGE_SECONDS = 86400 * 7  # 7 days

    def __init__(self):
        self.store = VectorStore(collection_name="semantic_cache")

    def lookup(self, query: str, schema_fingerprint: str) -> CacheEntry | None:
        """Search for cached result. Returns None on miss."""
        ...

    def store_result(self, query, schema_fingerprint, code, execution_output):
        """Save successful result for future lookups."""
        ...
```

### Checkpoint
- [ ] Cache stores successful generation results
- [ ] Similar queries return cached code (< 100ms)
- [ ] Different CSV schemas don't match
- [ ] Entries expire after 7 days

---

## Feature 2: Query Classifier

> **Goal:** Classify queries to optimize pipeline routing. Simple queries skip review/judge.

**File:** `src/llm/classifier.py`

### Classification Categories

| Category | Example | Pipeline Effect |
|----------|---------|----------------|
| `simple` | "Show first 5 rows" | Skip RAG, skip review, skip judge |
| `aggregation` | "Total revenue by city" | Full pipeline |
| `visualization` | "Bar chart of sales" | Full pipeline |
| `cleaning` | "Fill null values with 0" | Full pipeline |
| `complex` | "First clean, then group, then plot" | Full pipeline + sub-task extraction |

### Two-Tier Classification

```
Tier 1: Regex rules (instant, no LLM call)
  ├─ "show.*rows" → simple
  ├─ "plot|chart|histogram" → visualization
  ├─ "group.*by|total.*per" → aggregation
  └─ No match? → Tier 2

Tier 2: LLM classification (Ollama, ~2s)
  └─ Send query to model with category list → parse response
```

### Performance Impact

| Query Type | Without Classifier | With Classifier |
|-----------|-------------------|-----------------|
| "Show first 5 rows" | ~20s (full pipeline) | ~6s (skip RAG+review+judge) |
| "Group by city, plot revenue" | ~25s | ~25s (no change) |

### Checkpoint
- [ ] Simple queries classified by rules (no LLM call)
- [ ] Complex queries get LLM-based classification
- [ ] Simple queries skip RAG + review + judge
- [ ] Classification accuracy ≥ 85%

---

## Feature 3: Code Validator

> **Goal:** Auto-fix missing imports and validate syntax before execution.

**File:** `src/llm/code_validator.py`

### What It Fixes

```python
# Generated code uses pd.read_csv but forgot the import
# Validator detects "pd." pattern → adds "import pandas as pd"

IMPORT_FIXES = {
    "pd.":   "import pandas as pd",
    "np.":   "import numpy as np",
    "plt.":  "import matplotlib.pyplot as plt",
    "json.": "import json",
    "Path(": "from pathlib import Path",
    ...
}
```

### Checkpoint
- [ ] Missing `import pandas as pd` auto-fixed
- [ ] Missing `import matplotlib.pyplot as plt` auto-fixed
- [ ] Syntax errors detected and reported
- [ ] No false positives (doesn't add imports for code that already has them)

---

## Feature 4: Local Reviewer Agent

> **Goal:** Agentic code reviewer using local Ollama that gives actionable feedback and can generate improved code.

**File:** `src/llm/reviewer.py`

### How It Works

Unlike the self-healer (which only fixes runtime errors), the reviewer checks for **logic correctness and completeness**:

```
Generated code + user request + CSV schema
        │
        ▼
┌─ Reviewer Agent (Ollama) ─────────────────────┐
│                                                │
│  Checks:                                       │
│  - Does code do what user asked?               │
│  - Are the right columns/aggregations used?    │
│  - Are null values handled?                    │
│  - Is visualization correct?                   │
│                                                │
│  Returns:                                      │
│  - Issues (severity: high/medium/low)          │
│  - Improvement suggestions                     │
│  - Improved code (if high-severity issues)     │
└────────────────────────────────────────────────┘
```

### ReviewResult Dataclass

```python
@dataclass
class ReviewIssue:
    severity: str  # high, medium, low
    description: str

@dataclass
class ReviewResult:
    issues: list[ReviewIssue]
    suggestions: list[str]
    improved_code: str  # empty if no issues
    summary: str
    error: str | None
```

### Two Methods

1. **`review()`** — Analyze code, return structured feedback (JSON)
2. **`improve()`** — Take review feedback, generate fixed code

If `review()` finds high-severity issues → automatically calls `improve()`.

### Checkpoint
- [ ] Reviewer identifies wrong column usage
- [ ] Reviewer identifies missing null handling
- [ ] Reviewer generates improved code for high-severity issues
- [ ] Graceful degradation on LLM parse errors

---

## Feature 5: Cloud Judge Agent

> **Goal:** Independent code quality evaluation using a free cloud LLM (different model = avoids self-evaluation bias).

**File:** `src/judge/judge_agent.py`, `src/judge/providers.py`

### Why a Separate Cloud Model?

When the same Ollama model generates AND reviews code, it tends to approve its own output (self-evaluation bias). Using a **different model family** (e.g., Llama 3.3 70B on Groq) gives truly independent evaluation.

### Provider Abstraction

```python
class JudgeProvider(ABC):
    def chat(self, messages, temperature) -> str: ...

class GroqProvider(JudgeProvider): ...      # api.groq.com
class GeminiProvider(JudgeProvider): ...    # generativelanguage.googleapis.com
class OpenRouterProvider(JudgeProvider): ... # openrouter.ai
```

All use `httpx` with 60s timeout. No provider-specific SDKs needed.

### Scoring System

```json
{
  "correctness": 8,
  "intent_alignment": 9,
  "code_quality": 7,
  "overall": 8.2,
  "feedback": "Code correctly groups by species but misses null handling.",
  "pass": true
}
```

- **correctness** (40%): Does it run? Correct output?
- **intent_alignment** (40%): Does it do what user asked?
- **code_quality** (20%): Clean, readable, proper imports?
- **pass threshold**: overall ≥ 6.0 (configurable via `JUDGE_PASS_THRESHOLD`)

### Privacy

The judge receives:
- User's text prompt
- CSV **schema only** (column names, types, stats — NO raw data rows)
- Generated code
- Whether execution succeeded + output length (NOT actual output content)

**No raw CSV data is ever sent to the cloud.**

### Free Tier Options

| Provider | Model | Rate Limit | Signup |
|----------|-------|-----------|--------|
| **Groq** (recommended) | Llama 3.3 70B | Generous free tier | console.groq.com |
| Google Gemini | Gemini 2.5 Flash | 1000 req/day | ai.google.dev |
| OpenRouter | Various :free models | 50 req/day | openrouter.ai |

### Checkpoint
- [ ] Judge returns scores for all 3 dimensions
- [ ] JSON parsing works even with markdown-wrapped responses
- [ ] Graceful degradation on network errors (pipeline continues)
- [ ] Different provider swap works via `.env`

---

## Feature 6: Two-Mode Pipeline Integration

> **Goal:** Wire all features together with mode-based routing.

**File:** `src/llm/pipeline.py` (updated), `src/config.py` (updated)

### Updated Pipeline Flow

```
[1]  CSV Schema Analysis
[2]  Query Classification → determines skip flags
[3]  Semantic Cache Check → HIT? Return instantly
[4]  RAG Retrieval (skip for simple queries)
[5]  Few-Shot Lookup
[6]  Prompt Assembly
[7]  Code Generation (Ollama)
[8]  Code Validation (auto-fix imports)
[9]  Execute + Self-Heal
[10] Review & Evaluation (MODE-DEPENDENT):
     ├─ MODE=local:  Local Reviewer only
     └─ MODE=cloud:  Cloud Judge + Local Reviewer
[11] Cache Store (save successful result)
[12] Return GenerationResult
```

### Updated GenerationResult

```python
@dataclass
class GenerationResult:
    # Existing
    code: str
    csv_schema: str
    rag_context: str
    full_prompt: str
    raw_response: str
    execution_success: bool | None = None
    execution_output: str = ""
    attempts: int = 0
    plot_paths: list[str] = field(default_factory=list)

    # Phase 1.2 additions
    query_category: str = ""
    cache_hit: bool = False
    warnings: list[str] = field(default_factory=list)
    judge_score: float | None = None
    judge_feedback: str = ""
    judge_passed: bool | None = None
    judge_details: dict | None = None
    review: ReviewResult | None = None
    improved_code: str = ""
```

### Updated Settings

```python
@dataclass
class Settings:
    # Existing
    ollama_base_url: str
    code_model: str
    embed_model: str
    chroma_persist_dir: Path
    knowledge_dir: Path

    # Phase 1.2
    pipeline_mode: str       # "local" or "cloud"
    judge_provider: str      # "groq", "gemini", "openrouter"
    judge_api_key: str
    judge_model: str
    judge_pass_threshold: float
```

---

## Feature 7: Chat UI (Streamlit)

> **Goal:** A simple conversational interface where end users can upload CSV and chat with the system.

**File:** `streamlit_demo.py` (add Chat tab)

### Chat Tab Design

```
┌─────────────────────────────────────────────────────────┐
│  💬 Chat                                                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🧬 Welcome! Upload a CSV and ask me anything.   │   │
│  │                                                   │   │
│  │ 👤 Show basic stats for this dataset             │   │
│  │                                                   │   │
│  │ 🧬 Here are the statistics:                      │   │
│  │ [code block]                                      │   │
│  │ [execution output]                                │   │
│  │ [plot image]                                      │   │
│  │                                                   │   │
│  │ 👤 Now group by species and show avg body mass   │   │
│  │                                                   │   │
│  │ 🧬 Here's the groupby result:                    │   │
│  │ [code block]                                      │   │
│  │ [output table]                                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [text input] _________________________ [Send]          │
└─────────────────────────────────────────────────────────┘
```

### Implementation

- Uses `st.chat_message()` for chat bubbles
- Chat history stored in `st.session_state["messages"]`
- Each user message triggers `pipeline.generate(csv_path, message)`
- Assistant response shows: code + output + plots (if any)
- Review/judge feedback shown as expandable details
- Preset prompts as quick-start suggestions

### Key Behavior
- CSV must be loaded first (via upload or sample dataset)
- Each message is independent (no multi-turn context — Phase 2 scope)
- Chat history is displayed but not sent to LLM
- Auto-execute is always ON in chat mode

---

## Updated Project Structure

```
src/
├── cache/
│   ├── __init__.py
│   └── semantic_cache.py        ← NEW: embedding-based cache
├── judge/
│   ├── __init__.py
│   ├── providers.py             ← NEW: Groq/Gemini/OpenRouter abstraction
│   ├── prompts.py               ← NEW: judge evaluation prompt
│   ├── judge_agent.py           ← NEW: JudgeAgent + JudgeResult
│   └── store.py                 ← NEW: JSONL persistence for analytics
├── llm/
│   ├── classifier.py            ← NEW: query classification
│   ├── code_validator.py        ← NEW: import fixer + syntax checker
│   ├── reviewer.py              ← NEW: local Ollama reviewer agent
│   ├── ollama_client.py
│   ├── pipeline.py              ← MODIFIED: two-mode pipeline
│   ├── prompts.py
│   ├── executor.py
│   └── self_healer.py
├── config.py                    ← MODIFIED: mode + judge settings
├── api/routes.py                ← MODIFIED: new response fields
└── ...existing...

streamlit_demo.py                ← MODIFIED: chat tab + review/judge UI
requirements.txt                 ← MODIFIED: + httpx
.env.example                     ← MODIFIED: mode + judge config
```

---

## Implementation Order

### Week 1: Core Features (independent, can parallelize)

| Day | Task | Owner |
|-----|------|-------|
| 1 | Feature 1: Semantic Cache | Any |
| 1 | Feature 3: Code Validator | Any |
| 2 | Feature 2: Query Classifier | Any |
| 2-3 | Feature 4: Local Reviewer Agent | Any |
| 2-3 | Feature 5: Cloud Judge Agent + Providers | Any |

### Week 2: Integration + UI

| Day | Task | Owner |
|-----|------|-------|
| 4 | Feature 6: Two-Mode Pipeline Integration | Any |
| 4 | Update config.py, .env.example, routes.py | Any |
| 5 | Feature 7: Chat UI in Streamlit | Any |
| 5 | Update existing Streamlit tabs (review/judge panels) | Any |
| 6 | Testing + polish | Everyone |

---

## Testing Plan

| Feature | Test File | Key Tests |
|---------|-----------|-----------|
| Semantic Cache | `tests/test_semantic_cache.py` | hit, miss, schema mismatch, expiry |
| Query Classifier | `tests/test_classifier.py` | rule-based, LLM fallback, accuracy |
| Code Validator | `tests/test_code_validator.py` | import fixing, syntax check |
| Local Reviewer | `tests/test_reviewer.py` | JSON parse, issues, improve, graceful errors |
| Cloud Judge | `tests/test_judge_agent.py` | scoring, parse, network error, disabled state |
| Judge Providers | `tests/test_judge_providers.py` | Groq, Gemini, OpenRouter request format |

---

## Success Criteria

Phase 1.2 is **DONE** when:

- [ ] `PIPELINE_MODE=local` works fully offline (no internet needed)
- [ ] `PIPELINE_MODE=cloud` adds Groq judge scoring to results
- [ ] Semantic cache serves repeated queries in < 100ms
- [ ] Query classifier skips RAG/review for simple queries (measurable speedup)
- [ ] Code validator auto-fixes missing imports
- [ ] Local reviewer identifies logic issues and generates improved code
- [ ] Cloud judge scores code on correctness/intent/quality (0-10)
- [ ] Chat UI allows conversational interaction with CSV data
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Switching modes via `.env` requires zero code changes

---

## What NOT to Build in Phase 1.2

Explicitly out of scope — save for Phase 2/3:

- ❌ Multi-turn conversation memory (chat history → LLM context)
- ❌ Hybrid RAG (BM25 + Vector + re-ranking)
- ❌ Agentic RAG / query routing
- ❌ AST-based code chunking
- ❌ Streaming responses
- ❌ User authentication
- ❌ Production web UI (React/Next.js)
- ❌ Docker containerized execution
- ❌ Custom model fine-tuning

---

*Last updated: 2026-03-25*
