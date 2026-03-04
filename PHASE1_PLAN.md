# Phase 1: Core Engine — Step-by-Step Implementation Guide

> Goal: Local code generator running on Ollama, CSV data processing focused, RAG-powered
> Timeline: Weeks 1-3 | Team: 3 people
> Final deliverable: `POST /generate` endpoint that accepts a CSV + prompt and returns working Python code

---

## Overview: What We Are Building

```
User uploads CSV + writes prompt
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                    FastAPI Server                     │
│                                                       │
│  1. CSV Schema Analyzer                               │
│     └─ extracts column info, types, stats, issues     │
│                                                       │
│  2. RAG Retriever                                     │
│     └─ finds relevant pandas docs & code patterns     │
│                                                       │
│  3. Prompt Engine                                     │
│     └─ combines schema + RAG context + user request   │
│                                                       │
│  4. Ollama Client                                     │
│     └─ sends assembled prompt → receives Python code  │
│                                                       │
│  Response: working Python script                      │
└─────────────────────────────────────────────────────┘
```

**Dependency chain (simple → hard):**
```
Step 1: Install & Play (no code, just get comfortable)
    └──▶ Step 2: First Python Script (talk to Ollama from Python)
        └──▶ Step 3: CSV Schema Analyzer (pure pandas, no LLM)
        └──▶ Step 4: ChromaDB + Embeddings (store & search text)
                  └──▶ Step 5: RAG Pipeline (find relevant docs + schema-aware query)
                            └──▶ Step 6: Prompt Engine (connect everything)
                                  └──▶ Step 6.5: Execution Feedback (run code, fix errors)
                                          └──▶ Step 7: FastAPI + CLI (expose as API)
                                                    └──▶ Step 8: Testing & Evaluation
                                                              └──▶ Step 8.5: Few-Shot Store (save & reuse successes)
                                                                        └──▶ Bonus Step 9: Streamlit Demo UI
```

---

## Technology Choices (Final)

| Component | Choice | Why |
|-----------|--------|-----|
| LLM | `qwen2.5-coder` (via Ollama) | Best open-source code model, runs locally |
| Embedding | `nomic-embed-text` (via Ollama) | 8K context, great for code chunks |
| RAG Framework | LlamaIndex | Simpler than LangChain, faster retrieval |
| Vector DB | ChromaDB | `pip install` and done, no Docker needed |
| API | FastAPI | Auto-generates docs, easy to learn |
| Language | Python 3.11+ | Required by LlamaIndex |

---

## Step 1: Install & Play

> **Goal:** Everyone on the team installs Ollama, talks to an AI model in the terminal, and sees it generate code. No Python, no project setup — just get comfortable with the tool.

**Owner:** Everyone
**Time:** Day 1
**Depends on:** Nothing

### 1.1 What is Ollama?

Ollama is like Docker but for AI models. You download a model, run it, and talk to it — all on your own machine. No internet needed after download, no API keys, no accounts.

### 1.2 Install Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

After install, Ollama runs as a background service automatically. Verify:
```bash
ollama --version
# Should print something like: ollama version 0.5.x
```

**If you see "command not found":** Restart your terminal and try again.

### 1.3 Download Your First Model

Pick ONE based on your computer's RAM:

| Your RAM | Model to Download | Download Size |
|----------|-------------------|---------------|
| 8 GB | `qwen2.5-coder:3b` | ~2 GB |
| 16 GB | `qwen2.5-coder:7b` | ~4.5 GB |
| 24 GB | `qwen2.5-coder:14b` | ~9 GB |
| 32 GB+ | `qwen2.5-coder:32b` | ~20 GB |

```bash
# Example for 16GB RAM machine:
ollama pull qwen2.5-coder:7b
```

This will take a few minutes depending on your internet speed. Wait for it to finish.

Also download the embedding model (small, everyone needs this):
```bash
ollama pull nomic-embed-text
```

### 1.4 Talk to the Model

Now the fun part. Start a chat:

```bash
ollama run qwen2.5-coder:7b
```

You'll see a `>>>` prompt. Try these one by one:

```
>>> Write a Python function that adds two numbers
>>> Write a pandas script that reads a CSV file and shows the first 5 rows
>>> How do I find duplicate rows in a pandas DataFrame?
>>> /bye
```

**What you should see:** The model writes Python code right in your terminal. It's not perfect, but it works. This is what we'll automate.

### 1.5 Try the API (curl)

Ollama also has an HTTP API at `http://localhost:11434`. This is how our Python code will talk to it later.

Open a **new terminal** and try:

```bash
# Ask it to generate code via API
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Write a Python function to count rows in a CSV file",
  "stream": false
}'
```

You'll get a JSON response with the generated code inside the `"response"` field.

Now test embeddings (this turns text into numbers for search):

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "nomic-embed-text",
  "input": "pandas read_csv"
}'
```

You'll see a JSON array of numbers. These numbers represent the "meaning" of the text — we'll use this for search later.

### 1.6 Checkpoint

Before moving on, make sure:

- [ ] `ollama --version` works
- [ ] You can chat with the model via `ollama run qwen2.5-coder:7b`
- [ ] The curl API call returns generated code
- [ ] The curl embed call returns an array of numbers

**Common problems:**

| Problem | Fix |
|---------|-----|
| "model not found" | Run `ollama pull qwen2.5-coder:7b` again |
| curl says "connection refused" | Run `ollama serve` in a separate terminal |
| Very slow response (minutes) | Your model is too big for your RAM — use a smaller one |
| Computer freezes/swaps | Immediately stop Ollama (`Ctrl+C`), switch to smaller model |

---

## Step 2: First Python Script — Talk to Ollama from Code

> **Goal:** Write a simple Python script that sends a prompt to Ollama and prints the response. Then build it into a reusable module.

**Owner:** Person C (others follow along to learn)
**Time:** Day 2-3
**Depends on:** Step 1 (Ollama running and working)

### 2.1 Set Up Python Environment

```bash
cd /path/to/enclave-coderunner

# Create a virtual environment (isolates our packages)
python3 -m venv .venv

# Activate it (you need to do this every time you open a new terminal)
source .venv/bin/activate

# Your terminal should now show (.venv) at the beginning
```

**If `python3` doesn't work:** Try `python3.11` or `python3.12`. We need Python 3.11 or newer.

### 2.2 Install Only What We Need Right Now

Don't install everything at once. Start with just the Ollama package:

```bash
pip install ollama pandas
```

That's it for now. We'll add more packages as we need them in later steps.

### 2.3 Write Your First Script

Create a file called `playground.py` in the project root:

**File: `playground.py`**
```python
"""
Playground script — test Ollama from Python.
Run: python playground.py
"""
import ollama

# Step 1: Check if Ollama is running
try:
    models = ollama.list()
    print("Ollama is running!")
    print(f"Available models: {[m.model for m in models.models]}")
except Exception as e:
    print(f"ERROR: Can't connect to Ollama. Is it running? ({e})")
    exit(1)

# Step 2: Send a simple prompt
print("\n--- Generating code ---\n")

response = ollama.chat(
    model="qwen2.5-coder:7b",          # change to your model
    messages=[
        {"role": "user", "content": "Write a Python function that reads a CSV and prints column names"}
    ],
)

print(response["message"]["content"])
```

Run it:
```bash
python playground.py
```

**What you should see:** A list of your models, then generated Python code. If this works, congratulations — you've connected Python to a local AI model.

### 2.4 Try System Prompts

System prompts tell the model how to behave. Add this to `playground.py` (or create a new file):

```python
"""Test system prompts — the model should return ONLY code, no explanations."""
import ollama

response = ollama.chat(
    model="qwen2.5-coder:7b",
    messages=[
        {
            "role": "system",
            "content": "You are a Python expert. Return ONLY code. No explanations, no markdown."
        },
        {
            "role": "user",
            "content": "Write a function that reads a CSV and returns the number of rows and columns"
        }
    ],
    options={
        "temperature": 0.1,    # Lower = more predictable output
    }
)

code = response["message"]["content"]
print(code)

# Check if it's valid Python
try:
    compile(code, "<string>", "exec")
    print("\n✓ Generated code is valid Python!")
except SyntaxError as e:
    print(f"\n✗ Syntax error in generated code: {e}")
```

### 2.5 Create the Project Structure

Now that we understand how Ollama works, let's organize our code properly:

```bash
# Create folders
mkdir -p src/llm src/rag src/csv_engine src/api src/vectordb
mkdir -p data/sample_csvs data/knowledge
mkdir -p tests

# Create __init__.py files (tells Python these are packages)
touch src/__init__.py
touch src/llm/__init__.py
touch src/rag/__init__.py
touch src/csv_engine/__init__.py
touch src/api/__init__.py
touch src/vectordb/__init__.py
```

Your project should now look like:
```
enclave-coderunner/
├── .gitignore
├── .env.example
├── README.md
├── PHASE1_PLAN.md
├── playground.py           ← your test scripts
├── src/
│   ├── __init__.py
│   ├── llm/
│   │   └── __init__.py
│   ├── rag/
│   │   └── __init__.py
│   ├── csv_engine/
│   │   └── __init__.py
│   ├── api/
│   │   └── __init__.py
│   └── vectordb/
│       └── __init__.py
├── data/
│   ├── sample_csvs/
│   └── knowledge/
└── tests/
```

### 2.6 Create the Config File

**File: `.env.example`**
```env
OLLAMA_BASE_URL=http://localhost:11434
CODE_MODEL=qwen2.5-coder:7b
EMBED_MODEL=nomic-embed-text
CHROMA_PERSIST_DIR=./data/chromadb
KNOWLEDGE_DIR=./data/knowledge
```

Copy it to create your local config:
```bash
cp .env.example .env
# Edit .env if your model name is different
```

Now create a simple config loader — no fancy libraries yet, just plain Python:

**File: `src/config.py`**
```python
"""
Project configuration. Reads from .env file.
Change values in .env, not here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CODE_MODEL = os.getenv("CODE_MODEL", "qwen2.5-coder:7b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Storage paths
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./data/knowledge"))
```

Install `python-dotenv`:
```bash
pip install python-dotenv
```

Test it:
```bash
python -c "from src.config import CODE_MODEL; print(f'Using model: {CODE_MODEL}')"
# Should print: Using model: qwen2.5-coder:7b
```

### 2.7 Build the Ollama Wrapper Module

Now move our playground code into a proper module:

**File: `src/llm/ollama_client.py`**
```python
"""
Ollama client wrapper.
Sends prompts to the local Ollama server and returns generated code.
"""
import ollama
from src.config import OLLAMA_BASE_URL, CODE_MODEL


class CodeGenerator:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_BASE_URL)
        self.model = CODE_MODEL

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to Ollama and return the response text.

        Args:
            prompt: What you want the model to do (e.g., "Write a function that...")
            system_prompt: Instructions for how the model should behave

        Returns:
            The model's response as a string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0.1,      # Low = more predictable code output
                "num_predict": 2048,      # Max length of response
            },
        )
        return response["message"]["content"]

    def health_check(self) -> bool:
        """Check if Ollama is running and our model is available."""
        try:
            self.client.show(self.model)
            return True
        except Exception:
            return False
```

### 2.8 Test the Module

```python
# test_ollama_manual.py (run this to verify, don't commit)
from src.llm.ollama_client import CodeGenerator

gen = CodeGenerator()

# Check connection
if not gen.health_check():
    print("ERROR: Can't reach Ollama or model not found!")
    print("Make sure 'ollama serve' is running and you pulled the model.")
    exit(1)

print("Ollama connected!\n")

# Test code generation
code = gen.generate(
    system_prompt="You are a Python expert. Return only code, no explanation.",
    prompt="Write a function that reads a CSV file and prints the first 5 rows using pandas.",
)
print("--- Generated Code ---")
print(code)

# Verify syntax
try:
    compile(code, "<string>", "exec")
    print("\n✓ Valid Python syntax!")
except SyntaxError as e:
    print(f"\n✗ Syntax error: {e}")
```

Run: `python test_ollama_manual.py`

### 2.9 Checkpoint

Before moving on, make sure:

- [ ] `python playground.py` runs and generates code
- [ ] `from src.config import CODE_MODEL` works
- [ ] `from src.llm.ollama_client import CodeGenerator` works
- [ ] `CodeGenerator().health_check()` returns `True`
- [ ] `CodeGenerator().generate("Write hello world")` returns Python code

**Common problems:**

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'src'` | Make sure you're running from the project root folder |
| `ConnectionError` | Run `ollama serve` in another terminal |
| Model is very slow | Switch to a smaller model in `.env` |
| Code has markdown ``` around it | We'll handle this in Step 6 — it's expected for now |

### 2.10 What to Watch For

- If response is slow (>30s for a short prompt), your model is too large for your hardware. Change `CODE_MODEL` in `.env` to a smaller one.
- `temperature: 0.1` keeps output deterministic. We'll tune this later.
- `num_predict: 2048` caps response length. Increase if code gets truncated.
- The model sometimes wraps code in \`\`\`python blocks — that's normal, we'll strip it later.

---

## Step 3: CSV Schema Analyzer

**Owner:** Person A
**Time:** Day 2-4
**Depends on:** Step 1 (Python environment only, no Ollama needed)

This component takes a CSV file path and produces a structured schema description that will be injected into the LLM prompt. **This is the most important component for our CSV-first approach.**

### 3.1 Build the Analyzer

**File: `src/csv_engine/schema_analyzer.py`**
```python
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
import json

@dataclass
class ColumnInfo:
    name: str
    dtype: str
    null_pct: float
    unique_count: int
    sample_values: list
    # Numeric columns only
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    # Type suggestion
    suggested_type: str | None = None

@dataclass
class CSVSchema:
    filename: str
    rows: int
    columns: int
    encoding: str
    delimiter: str
    column_info: list[ColumnInfo]
    potential_issues: list[str] = field(default_factory=list)

    def to_prompt_string(self) -> str:
        """Format schema as a string for LLM prompt injection."""
        lines = [
            f"File: {self.filename} ({self.rows:,} rows, {self.columns} columns)",
            f"Encoding: {self.encoding}, Delimiter: '{self.delimiter}'",
            "",
            "Columns:",
        ]
        for col in self.column_info:
            parts = [f"  - {col.name} ({col.dtype}"]
            if col.suggested_type:
                parts[0] += f" → {col.suggested_type} recommended"
            parts[0] += f", null: {col.null_pct:.1f}%"
            parts[0] += f", {col.unique_count} unique"
            if col.min_val is not None:
                parts[0] += f", range: {col.min_val}-{col.max_val}, mean: {col.mean_val:.1f}"
            parts[0] += ")"
            samples = ", ".join(str(v) for v in col.sample_values[:3])
            parts.append(f"    examples: [{samples}]")
            lines.extend(parts)

        if self.potential_issues:
            lines.append("")
            lines.append("Potential issues:")
            for issue in self.potential_issues:
                lines.append(f"  ⚠ {issue}")

        return "\n".join(lines)


class SchemaAnalyzer:
    """Analyzes a CSV file and extracts structured schema information."""

    def analyze(self, file_path: str | Path, sample_rows: int = 5) -> CSVSchema:
        path = Path(file_path)
        encoding = self._detect_encoding(path)
        delimiter = self._detect_delimiter(path, encoding)

        df = pd.read_csv(path, encoding=encoding, delimiter=delimiter)

        columns = []
        issues = []

        for col_name in df.columns:
            col = df[col_name]
            null_pct = (col.isna().sum() / len(df)) * 100
            unique_count = col.nunique()
            sample_vals = col.dropna().head(sample_rows).tolist()

            col_info = ColumnInfo(
                name=col_name,
                dtype=str(col.dtype),
                null_pct=round(null_pct, 1),
                unique_count=unique_count,
                sample_values=sample_vals,
            )

            # Numeric stats
            if pd.api.types.is_numeric_dtype(col):
                col_info.min_val = float(col.min()) if not col.isna().all() else None
                col_info.max_val = float(col.max()) if not col.isna().all() else None
                col_info.mean_val = float(col.mean()) if not col.isna().all() else None

            # Type suggestions
            if col.dtype == "object":
                suggestion = self._suggest_type(col)
                if suggestion:
                    col_info.suggested_type = suggestion
                    issues.append(f"Column '{col_name}' is string but looks like {suggestion}")

            # Null warning
            if 0 < null_pct <= 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values")
            elif null_pct > 50:
                issues.append(f"Column '{col_name}' has {null_pct:.1f}% null values — consider dropping")

            columns.append(col_info)

        # Duplicate check
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            issues.append(f"{dup_count} duplicate rows found")

        return CSVSchema(
            filename=path.name,
            rows=len(df),
            columns=len(df.columns),
            encoding=encoding,
            delimiter=delimiter,
            column_info=columns,
            potential_issues=issues,
        )

    def _detect_encoding(self, path: Path) -> str:
        """Try utf-8 first, fall back to latin-1."""
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(path, encoding=enc) as f:
                    f.read(1024)
                return enc
            except (UnicodeDecodeError, Exception):
                continue
        return "utf-8"

    def _detect_delimiter(self, path: Path, encoding: str) -> str:
        """Detect delimiter by checking first line."""
        import csv
        with open(path, encoding=encoding) as f:
            sample = f.read(4096)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                return dialect.delimiter
            except csv.Error:
                return ","

    def _suggest_type(self, col: pd.Series) -> str | None:
        """Check if a string column might actually be datetime or numeric."""
        sample = col.dropna().head(20)
        if len(sample) == 0:
            return None

        # Try datetime
        try:
            pd.to_datetime(sample)
            return "datetime"
        except (ValueError, TypeError):
            pass

        # Try numeric
        try:
            pd.to_numeric(sample)
            return "numeric"
        except (ValueError, TypeError):
            pass

        return None
```

### 3.2 Create Sample CSV for Testing

**File: `data/sample_csvs/sales_data.csv`**
```csv
date,city,product,revenue,quantity,discount,customer_id,notes
2024-01-15,Istanbul,Widget A,1500.50,10,0.05,C001,First order
2024-01-16,Ankara,Widget B,2300.00,15,0.10,C002,
2024-01-16,Istanbul,Widget A,1800.75,12,0.05,C001,Repeat customer
2024-01-17,Izmir,Widget C,950.25,5,0.00,C003,
2024-01-18,Istanbul,Widget B,3200.00,20,0.15,C004,Bulk order
2024-01-19,Ankara,Widget A,1100.00,8,,C005,
2024-01-20,Izmir,Widget C,875.50,4,0.00,C003,
2024-01-21,Istanbul,Widget A,2100.25,14,0.10,C006,
2024-01-22,Ankara,Widget B,1750.00,11,0.05,C002,
2024-01-23,Istanbul,Widget C,650.00,3,0.00,C007,Small order
2024-01-23,Istanbul,Widget C,650.00,3,0.00,C007,Small order
```

### 3.3 Test the Analyzer

```python
# test_schema_manual.py
from src.csv_engine.schema_analyzer import SchemaAnalyzer

analyzer = SchemaAnalyzer()
schema = analyzer.analyze("data/sample_csvs/sales_data.csv")

print(schema.to_prompt_string())
print("\n--- Raw Issues ---")
for issue in schema.potential_issues:
    print(f"  - {issue}")
```

**Checkpoint — expected output should include:**
```
File: sales_data.csv (11 rows, 8 columns)
Encoding: utf-8, Delimiter: ','

Columns:
  - date (object → datetime recommended, null: 0.0%, 10 unique)
    examples: [2024-01-15, 2024-01-16, 2024-01-16]
  - revenue (float64, null: 0.0%, 10 unique, range: 650.0-3200.0, mean: 1541.5)
    examples: [1500.5, 2300.0, 1800.75]
  - discount (float64, null: 9.1%, 4 unique, range: 0.0-0.15, mean: 0.05)
  ...

Potential issues:
  ⚠ Column 'date' is string but looks like datetime
  ⚠ Column 'discount' has 9.1% null values
  ⚠ 1 duplicate rows found
```

### 3.4 Write Unit Tests

**File: `tests/test_schema_analyzer.py`**
```python
import pytest
from src.csv_engine.schema_analyzer import SchemaAnalyzer

@pytest.fixture
def analyzer():
    return SchemaAnalyzer()

def test_basic_analysis(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    assert schema.rows == 11
    assert schema.columns == 8
    assert schema.delimiter == ","

def test_detects_datetime_suggestion(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    date_col = next(c for c in schema.column_info if c.name == "date")
    assert date_col.suggested_type == "datetime"

def test_detects_nulls(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    discount_col = next(c for c in schema.column_info if c.name == "discount")
    assert discount_col.null_pct > 0

def test_detects_duplicates(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    assert any("duplicate" in issue.lower() for issue in schema.potential_issues)

def test_prompt_string_not_empty(analyzer):
    schema = analyzer.analyze("data/sample_csvs/sales_data.csv")
    prompt_str = schema.to_prompt_string()
    assert len(prompt_str) > 100
    assert "sales_data.csv" in prompt_str
```

Run: `pytest tests/test_schema_analyzer.py -v`

**Checkpoint:** All 5 tests pass.

---

## Step 4: ChromaDB + Embeddings Setup

**Owner:** Person B
**Time:** Day 3-4
**Depends on:** Step 1

Build the vector store abstraction layer. This is independent from RAG — just embed text and search.

### 4.1 Build the Vector Store Wrapper

**File: `src/vectordb/store.py`**
```python
import chromadb
from chromadb.config import Settings as ChromaSettings
import ollama
from src.config import settings
from pathlib import Path

class VectorStore:
    """Thin wrapper around ChromaDB. Swappable to Qdrant later."""

    def __init__(self, collection_name: str = "knowledge"):
        self.persist_dir = str(settings.chroma_persist_dir)
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.embed_client = ollama.Client(host=settings.ollama_base_url)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via Ollama nomic-embed-text."""
        response = self.embed_client.embed(
            model=settings.embed_model,
            input=texts,
        )
        return response["embeddings"]

    def add_documents(self, doc_ids: list[str], texts: list[str], metadatas: list[dict] | None = None):
        """Add documents with their embeddings to the store."""
        embeddings = self._embed(texts)
        self.collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search for similar documents. Returns list of {id, text, score, metadata}."""
        query_embedding = self._embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "score": 1 - results["distances"][0][i],  # cosine distance → similarity
                "metadata": results["metadatas"][0][i],
            })
        return items

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        """Delete all documents. Use for re-indexing."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )
```

### 4.2 Test Embedding + Search

```python
# test_vectordb_manual.py
from src.vectordb.store import VectorStore

store = VectorStore(collection_name="test")
store.reset()

# Add some pandas-related snippets
store.add_documents(
    doc_ids=["1", "2", "3"],
    texts=[
        "pd.read_csv('file.csv') reads a CSV file into a DataFrame",
        "df.groupby('column').mean() groups data and calculates averages",
        "df.to_excel('output.xlsx') exports DataFrame to Excel format",
    ],
    metadatas=[
        {"source": "pandas_docs", "topic": "io"},
        {"source": "pandas_docs", "topic": "groupby"},
        {"source": "pandas_docs", "topic": "io"},
    ],
)

print(f"Documents stored: {store.count()}")

results = store.search("how to read csv file in pandas", top_k=2)
for r in results:
    print(f"  Score: {r['score']:.3f} | {r['text'][:80]}")
```

**Checkpoint:** The `read_csv` snippet should rank #1 with highest similarity score. If scores are all very close or the wrong result ranks first, something is wrong with the embedding.

---

## Step 5: RAG Pipeline with LlamaIndex

**Owner:** Person B
**Time:** Day 5-8
**Depends on:** Step 4 (vector store working)

### 5.1 Prepare Knowledge Documents

The RAG pipeline needs content to retrieve from. For MVP, we index:
1. **pandas code patterns** — common operations as documented snippets
2. **CSV handling recipes** — encoding, delimiter, dtype patterns

**File: `data/knowledge/pandas_csv_patterns.md`**

Create a file with 30-50 common pandas patterns, structured like this:

```markdown
## Reading CSV Files
```python
# Basic CSV read
df = pd.read_csv('file.csv')

# With encoding and delimiter
df = pd.read_csv('file.csv', encoding='utf-8', delimiter=';')

# Read specific columns only
df = pd.read_csv('file.csv', usecols=['name', 'age', 'salary'])

# Handle large files with chunking
for chunk in pd.read_csv('large_file.csv', chunksize=10000):
    process(chunk)
```

## Handling Missing Values
```python
# Check for nulls
df.isnull().sum()

# Fill with mean (numeric columns)
df['column'] = df['column'].fillna(df['column'].mean())

# Fill with mode (categorical columns)
df['column'] = df['column'].fillna(df['column'].mode()[0])

# Drop rows with any null
df_clean = df.dropna()

# Drop rows where specific column is null
df_clean = df.dropna(subset=['important_column'])
```

## Grouping and Aggregation
```python
# Group by single column
result = df.groupby('city')['revenue'].sum()

# Group by multiple columns with multiple aggregations
result = df.groupby(['city', 'product']).agg(
    total_revenue=('revenue', 'sum'),
    avg_quantity=('quantity', 'mean'),
    order_count=('revenue', 'count')
).reset_index()

# Pivot table
pivot = pd.pivot_table(df, values='revenue', index='city', columns='product', aggfunc='sum')
```

... (continue for all categories: merging, datetime, visualization, export, etc.)
```

> **Important:** This file should be 200-400 lines of real, tested pandas patterns. The quality of RAG output directly depends on the quality of this knowledge base. Each team member adds patterns from their experience.

### 5.2 Build the Document Chunker

**File: `src/rag/chunking.py`**
```python
from pathlib import Path
import re

@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict

class MarkdownCodeChunker:
    """Splits markdown files into chunks by ## headers.
    Each chunk = one section with its code blocks."""

    def chunk_file(self, file_path: str | Path) -> list[Chunk]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        sections = re.split(r'\n(?=## )', content)

        chunks = []
        for i, section in enumerate(sections):
            section = section.strip()
            if not section or len(section) < 20:
                continue

            # Extract title from first line
            title_match = re.match(r'## (.+)', section)
            title = title_match.group(1) if title_match else f"section_{i}"

            chunks.append(Chunk(
                id=f"{path.stem}_{i}_{title.lower().replace(' ', '_')[:40]}",
                text=section,
                metadata={
                    "source": path.name,
                    "title": title,
                    "chunk_index": i,
                },
            ))
        return chunks

    def chunk_directory(self, dir_path: str | Path) -> list[Chunk]:
        """Chunk all markdown files in a directory."""
        all_chunks = []
        for md_file in Path(dir_path).glob("*.md"):
            all_chunks.extend(self.chunk_file(md_file))
        return all_chunks
```

### 5.3 Build the Indexer

**File: `src/rag/indexer.py`**
```python
from src.vectordb.store import VectorStore
from src.rag.chunking import MarkdownCodeChunker
from src.config import settings
from pathlib import Path

class KnowledgeIndexer:
    """Indexes knowledge documents into the vector store."""

    def __init__(self):
        self.store = VectorStore(collection_name="knowledge")
        self.chunker = MarkdownCodeChunker()

    def index_knowledge_dir(self, force_reindex: bool = False):
        """Index all markdown files in the knowledge directory."""
        knowledge_dir = settings.knowledge_dir

        if force_reindex:
            self.store.reset()

        if self.store.count() > 0 and not force_reindex:
            print(f"Knowledge already indexed ({self.store.count()} chunks). Use force_reindex=True to rebuild.")
            return

        chunks = self.chunker.chunk_directory(knowledge_dir)
        if not chunks:
            print(f"No markdown files found in {knowledge_dir}")
            return

        # Batch insert (ChromaDB handles batching internally)
        self.store.add_documents(
            doc_ids=[c.id for c in chunks],
            texts=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )
        print(f"Indexed {len(chunks)} chunks from {knowledge_dir}")

    def get_stats(self) -> dict:
        return {"total_chunks": self.store.count()}
```

### 5.4 Build the Retriever

**File: `src/rag/retriever.py`**
```python
from src.vectordb.store import VectorStore

class KnowledgeRetriever:
    """Retrieves relevant knowledge chunks for a given query."""

    def __init__(self):
        self.store = VectorStore(collection_name="knowledge")

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.3,
                 schema_hint: str = "") -> str:
        """
        Search for relevant chunks and format them as context string.
        Returns empty string if nothing relevant found.

        schema_hint: optional column type info to enrich the query
                     (e.g. "columns: revenue(float64), city(object)")
        """
        # Schema-aware query: enrich with column types so retrieval
        # finds patterns that match the actual data types
        enriched_query = query
        if schema_hint:
            enriched_query = f"{query} | {schema_hint}"

        results = self.store.search(enriched_query, top_k=top_k)

        # Filter by minimum relevance score
        relevant = [r for r in results if r["score"] >= min_score]

        if not relevant:
            return ""

        context_parts = []
        for r in relevant:
            context_parts.append(f"### {r['metadata'].get('title', 'Reference')}\n{r['text']}")

        return "\n\n---\n\n".join(context_parts)
```

### 5.5 Test the Full RAG Flow

```python
# test_rag_manual.py
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import KnowledgeRetriever

# Step 1: Index
indexer = KnowledgeIndexer()
indexer.index_knowledge_dir(force_reindex=True)
print(indexer.get_stats())

# Step 2: Retrieve
retriever = KnowledgeRetriever()

# Test queries
test_queries = [
    "how to read a CSV file",
    "fill missing values in dataframe",
    "group by column and sum",
    "export to excel",
    "find duplicate rows",
]

for q in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    context = retriever.retrieve(q, top_k=2)
    if context:
        print(f"Context (first 200 chars): {context[:200]}...")
    else:
        print("No relevant context found")
```

**Checkpoint:**
- Indexing completes without errors and reports chunk count
- Each test query returns relevant pandas code patterns
- "read a CSV file" should return the CSV reading section, not the Excel export section
- If retrieval is irrelevant, the knowledge documents need better content or chunking needs adjustment

---

## Step 6: Prompt Engine — Connecting Everything

**Owner:** Person A
**Time:** Day 7-10
**Depends on:** Step 2 (Ollama client), Step 3 (CSV analyzer), Step 5 (RAG retriever)

This is where all components come together.

### 6.1 Define Prompt Templates

**File: `src/llm/prompts.py`**
```python
SYSTEM_PROMPT = """You are a Python data analyst and developer.
You generate clean, runnable Python code that works with CSV files.

Rules:
- Use pandas, numpy, and matplotlib only
- Always include necessary imports at the top
- Take the CSV file path as a parameter (use variable `csv_path`)
- Always produce complete, copy-paste ready scripts
- Add brief comments explaining each step
- Include basic error handling for file operations
- For large files, consider using chunksize parameter"""

GENERATION_TEMPLATE = """## Relevant Code Patterns
{rag_context}

## CSV File Information
{csv_schema}

## User Request
{user_prompt}

Generate a complete, runnable Python script that fulfills the user's request.
The script should use the variable `csv_path` for the input file path.
Return ONLY the Python code, no explanations before or after."""

GENERATION_TEMPLATE_NO_RAG = """## CSV File Information
{csv_schema}

## User Request
{user_prompt}

Generate a complete, runnable Python script that fulfills the user's request.
The script should use the variable `csv_path` for the input file path.
Return ONLY the Python code, no explanations before or after."""
```

### 6.2 Build the Pipeline Orchestrator

**File: `src/llm/pipeline.py`**
```python
from src.llm.ollama_client import CodeGenerator
from src.llm.prompts import SYSTEM_PROMPT, GENERATION_TEMPLATE, GENERATION_TEMPLATE_NO_RAG
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

class CodePipeline:
    """
    Main orchestrator. Takes CSV path + user prompt → returns generated Python code.

    Flow:
    1. Analyze CSV → extract schema
    2. Query RAG → find relevant pandas patterns
    3. Assemble prompt → system + schema + RAG context + user request
    4. Send to Ollama → get generated code
    5. Clean response → extract code block if wrapped in markdown
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

        return GenerationResult(
            code=code,
            csv_schema=schema_str,
            rag_context=rag_context,
            full_prompt=prompt,
            raw_response=raw_response,
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

        # No code blocks found, return as-is (model returned raw code)
        return response.strip()
```

### 6.3 Test the Full Pipeline

```python
# test_pipeline_manual.py
from src.llm.pipeline import CodePipeline

pipeline = CodePipeline()

# Test 1: Basic read
result = pipeline.generate(
    csv_path="data/sample_csvs/sales_data.csv",
    user_prompt="Read the CSV and show basic statistics for all numeric columns"
)
print("=== Generated Code ===")
print(result.code)
print("\n=== Schema Used ===")
print(result.csv_schema)
print(f"\n=== RAG Context Length: {len(result.rag_context)} chars ===")
```

**Checkpoint — the generated code should:**
- Start with `import pandas as pd`
- Use `csv_path` variable (not hardcoded path)
- Call `pd.read_csv(csv_path)` and `.describe()`
- Be syntactically valid Python
- Include comments

**Test with multiple prompts:**
```python
test_prompts = [
    "Show the first 5 rows",
    "Fill missing discount values with 0",
    "Group by city and show total revenue per city",
    "Find and remove duplicate rows",
    "Create a bar chart of revenue by product",
]

for prompt in test_prompts:
    print(f"\n{'='*60}")
    print(f"Prompt: {prompt}")
    result = pipeline.generate("data/sample_csvs/sales_data.csv", prompt)
    print(result.code[:300])
    print("...")
```

---

## Step 6.5: Execution Feedback — Run Code, Fix Errors

> **Goal:** Don't deliver broken code. Run the generated code, and if it fails, feed the error back to the LLM to fix it. Simple retry loop, max 3 attempts.

**Owner:** Person C
**Time:** Day 10-11
**Depends on:** Step 6 (pipeline producing code)

### 6.5.1 Build the Code Executor

**File: `src/llm/executor.py`**
```python
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: str
    return_code: int

class CodeExecutor:
    """Runs generated Python code in a subprocess and captures output/errors."""

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Run code in isolated subprocess. Returns output or error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ['python', tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.cwd()),  # so relative CSV paths work
            )
            return ExecutionResult(
                success=(result.returncode == 0),
                output=result.stdout[:2000],  # cap output
                error=result.stderr[:2000],
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False, output="", error="Timeout: code took too long", return_code=-1
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
```

### 6.5.2 Build the Self-Healer

**File: `src/llm/self_healer.py`**
```python
from src.llm.ollama_client import CodeGenerator
from src.llm.executor import CodeExecutor, ExecutionResult

FIX_PROMPT = """The following Python code produced an error. Fix it.

Code:
```python
{code}
```

Error:
{error}

Return ONLY the fixed Python code, no explanations."""

class SelfHealer:
    """Try to run code, if it fails send error back to LLM to fix. Max 3 attempts."""

    def __init__(self, max_attempts: int = 3):
        self.executor = CodeExecutor()
        self.generator = CodeGenerator()
        self.max_attempts = max_attempts

    def run_with_retry(self, code: str) -> dict:
        """Returns {code, success, attempts, output, last_error}."""
        for attempt in range(1, self.max_attempts + 1):
            result = self.executor.execute(code)

            if result.success:
                return {
                    "code": code,
                    "success": True,
                    "attempts": attempt,
                    "output": result.output,
                    "last_error": None,
                }

            # Not last attempt — ask LLM to fix
            if attempt < self.max_attempts:
                code = self.generator.generate(
                    prompt=FIX_PROMPT.format(code=code, error=result.error),
                    system_prompt="You are a Python expert. Fix the code. Return ONLY code.",
                )

        return {
            "code": code,
            "success": False,
            "attempts": self.max_attempts,
            "output": "",
            "last_error": result.error,
        }
```

### 6.5.3 Integrate into Pipeline

Update `src/llm/pipeline.py` — at the end of `generate()`, add:

```python
# After generating code, try to run it
from src.llm.self_healer import SelfHealer

healer = SelfHealer(max_attempts=3)
healed = healer.run_with_retry(code)

# Use the healed code (may be same as original if it worked first try)
result.code = healed["code"]
result.execution_success = healed["success"]
result.attempts = healed["attempts"]
```

**Checkpoint:**
- Code that has a typo in column name → LLM gets the NameError → fixes the column name
- Code with missing import → LLM gets ImportError → adds the import
- Code that works on first try → returns in 1 attempt (no extra LLM calls)

---

## Step 7: FastAPI Endpoints + CLI

**Owner:** Person A (API) + Person C (CLI)
**Time:** Day 9-12
**Depends on:** Step 6 (pipeline working)

### 7.1 Build the API

**File: `src/api/routes.py`**
```python
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
from pathlib import Path
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)
app = FastAPI(title="Enclave CodeRunner", version="0.1.0")
pipeline = CodePipeline()

@app.get("/health")
def health():
    """Check if the system is operational."""
    ollama_ok = pipeline.generator.health_check()
    rag_count = KnowledgeIndexer().get_stats()["total_chunks"]
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": "connected" if ollama_ok else "unreachable",
        "rag_chunks_indexed": rag_count,
    }

@app.post("/generate")
async def generate_code(
    csv_file: UploadFile = File(...),
    prompt: str = Form(...),
):
    """
    Upload a CSV file + natural language prompt → receive generated Python code.

    Example:
        curl -X POST http://localhost:8000/generate \
          -F "csv_file=@data.csv" \
          -F "prompt=Show the first 5 rows"
    """
    # Save uploaded file to temp location
    try:
        suffix = Path(csv_file.filename).suffix or ".csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(csv_file.file, tmp)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {e}")

    # Generate code
    try:
        result = pipeline.generate(csv_path=tmp_path, user_prompt=prompt)
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=f"Code generation failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "code": result.code,
        "csv_schema": result.csv_schema,
        "rag_context_used": bool(result.rag_context),
    }

@app.post("/generate/text")
async def generate_code_from_path(
    csv_path: str = Form(...),
    prompt: str = Form(...),
):
    """
    Like /generate but accepts a local file path instead of upload.
    Useful for CLI and testing.
    """
    if not Path(csv_path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {csv_path}")

    try:
        result = pipeline.generate(csv_path=csv_path, user_prompt=prompt)
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=f"Code generation failed: {e}")

    return {
        "code": result.code,
        "csv_schema": result.csv_schema,
        "rag_context_used": bool(result.rag_context),
    }

@app.post("/index")
async def reindex_knowledge():
    """Re-index the knowledge base. Call after adding new documents to data/knowledge/."""
    try:
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)
        stats = indexer.get_stats()
        return {"status": "ok", **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
```

**File: `main.py`** (server entrypoint)
```python
import uvicorn
from src.api.routes import app
from src.rag.indexer import KnowledgeIndexer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def startup():
    """Index knowledge on first run if not already indexed."""
    indexer = KnowledgeIndexer()
    stats = indexer.get_stats()
    if stats["total_chunks"] == 0:
        logger.info("First run — indexing knowledge base...")
        indexer.index_knowledge_dir()
    else:
        logger.info(f"Knowledge base ready ({stats['total_chunks']} chunks)")

if __name__ == "__main__":
    startup()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 7.2 Build the CLI

**File: `cli.py`**
```python
"""Interactive CLI for testing code generation."""
import argparse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer

def main():
    parser = argparse.ArgumentParser(description="Enclave CodeRunner CLI")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--prompt", help="Generation prompt (interactive if omitted)")
    parser.add_argument("--index", action="store_true", help="Re-index knowledge base and exit")
    args = parser.parse_args()

    if args.index:
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)
        print(f"Done. {indexer.get_stats()}")
        return

    pipeline = CodePipeline()

    if args.prompt:
        # Single-shot mode
        result = pipeline.generate(args.csv, args.prompt)
        print(result.code)
    else:
        # Interactive mode
        print(f"CSV loaded: {args.csv}")
        print("Type your prompts (Ctrl+C to exit):\n")
        while True:
            try:
                prompt = input(">>> ")
                if not prompt.strip():
                    continue
                result = pipeline.generate(args.csv, prompt)
                print(f"\n{result.code}\n")
            except KeyboardInterrupt:
                print("\nBye.")
                break

if __name__ == "__main__":
    main()
```

### 7.3 Verify Everything Works

```bash
# Terminal 1: Start the API server
python main.py

# Terminal 2: Test the health endpoint
curl http://localhost:8000/health

# Terminal 2: Test code generation via API
curl -X POST http://localhost:8000/generate \
  -F "csv_file=@data/sample_csvs/sales_data.csv" \
  -F "prompt=Show total revenue by city"

# Terminal 2: Test CLI single-shot
python cli.py --csv data/sample_csvs/sales_data.csv --prompt "Show the first 5 rows"

# Terminal 2: Test CLI interactive
python cli.py --csv data/sample_csvs/sales_data.csv
>>> Show basic statistics
>>> Group by product, show average revenue
>>> Find duplicate rows
```

**Checkpoint:**
- `/health` returns `{"status": "ok", "ollama": "connected", "rag_chunks_indexed": N}`
- `/generate` returns JSON with `code` field containing valid Python
- CLI prints generated code for each prompt
- Generated code references `csv_path` and uses pandas correctly

---

## Step 8: Testing & Quality Evaluation

**Owner:** Person B (lead), everyone contributes
**Time:** Day 11-15
**Depends on:** Step 7 (API + CLI working)

### 8.1 Create Test CSV Collection

Create 3-4 diverse CSVs in `data/sample_csvs/`:

| File | Description | Rows | Challenges |
|------|-------------|------|------------|
| `sales_data.csv` | Sales records | 11 | Dates as strings, nulls, duplicates |
| `employees.csv` | HR data | 50+ | Mixed types, multiple date formats |
| `weather.csv` | Time series | 365 | Missing values, numeric outliers |
| `messy_data.csv` | Intentionally dirty | 30 | Wrong delimiters, encoding issues, mixed types |

### 8.2 Run the 10 Test Scenarios

For each scenario, record: prompt → generated code → does it run? → correct output?

| # | CSV File | Prompt | Runs? | Correct? | Notes |
|---|----------|--------|-------|----------|-------|
| 1 | sales_data.csv | "Show the first 5 rows" | | | |
| 2 | sales_data.csv | "Fill null discount values with 0" | | | |
| 3 | sales_data.csv | "Convert date column to datetime" | | | |
| 4 | sales_data.csv | "Group by city, show total revenue" | | | |
| 5 | weather.csv | "Plot monthly temperature trend" | | | |
| 6 | sales_data.csv + employees.csv | "Merge by customer_id" | | | |
| 7 | weather.csv | "Find outliers using IQR method" | | | |
| 8 | sales_data.csv | "Export to Excel with sheet name 'Sales'" | | | |
| 9 | employees.csv | "Create correlation matrix and heatmap" | | | |
| 10 | sales_data.csv | "Find and remove duplicate rows" | | | |

**How to test each scenario:**
```bash
# Generate
python cli.py --csv data/sample_csvs/sales_data.csv --prompt "Show the first 5 rows" > /tmp/generated.py

# Check syntax
python -c "compile(open('/tmp/generated.py').read(), 'test', 'exec'); print('Syntax OK')"

# Run it (add csv_path variable)
echo "csv_path = 'data/sample_csvs/sales_data.csv'" | cat - /tmp/generated.py | python
```

### 8.3 Calculate Success Rate

```
Runs successfully:    ___ / 10
Correct output:       ___ / 10
Success rate:         ___%
```

**MVP target: 70%+ correct output (7/10 scenarios produce correct results).**

### 8.4 Common Failure Modes to Watch

| Failure | Likely Cause | Fix |
|---------|-------------|-----|
| Code has syntax errors | Model returns markdown text mixed with code | Improve `_extract_code()` in pipeline |
| Hardcoded file paths | System prompt not strong enough | Add "NEVER hardcode file paths" to system prompt |
| Wrong column names used | CSV schema not injected properly | Check `to_prompt_string()` output |
| Missing imports | Model assumes they're already imported | Add "Always include all imports" to system prompt |
| Uses libraries we don't want | Model uses sklearn, seaborn, etc. | Be explicit in system prompt about allowed libraries |
| Code is correct but verbose | Model over-explains in comments | Add "Be concise" to system prompt |

### 8.5 Iterate on Prompt Templates

After the first test pass, adjust prompts based on failures:

1. If the model wraps code in explanations → add "Return ONLY Python code"
2. If it uses wrong column names → ensure schema is injected clearly
3. If RAG context is irrelevant → check knowledge base content and chunking
4. If code doesn't handle edge cases → add examples to system prompt

---

## Step 8.5: Few-Shot Store — Learn from Successes

> **Goal:** Save successful generation results so the system gets better over time. When a similar query comes in, show the LLM a proven working example.

**Owner:** Person B
**Time:** Day 14-15
**Depends on:** Step 6.5 (execution feedback — we need to know which code actually ran)

### 8.5.1 Save Successful Generations

**File: `src/rag/few_shot_store.py`**
```python
from src.vectordb.store import VectorStore
import json
import hashlib

class FewShotStore:
    """Stores successful query→code pairs for retrieval as examples."""

    def __init__(self):
        self.store = VectorStore(collection_name="few_shot_examples")

    def save(self, query: str, schema_summary: str, code: str):
        """Save a successful generation as a few-shot example."""
        doc_id = hashlib.md5(f"{query}:{schema_summary}".encode()).hexdigest()
        text = f"Query: {query}\nSchema: {schema_summary}\nCode:\n{code}"
        self.store.add_documents(
            doc_ids=[doc_id],
            texts=[text],
            metadatas=[{"query": query, "type": "few_shot"}],
        )

    def find_similar(self, query: str, top_k: int = 1) -> str:
        """Find similar past successful examples."""
        results = self.store.search(query, top_k=top_k)
        if results and results[0]["score"] >= 0.5:
            return results[0]["text"]
        return ""

    def count(self) -> int:
        return self.store.count()
```

### 8.5.2 Integrate into Pipeline

In `pipeline.generate()`, after execution feedback confirms success:

```python
# If code ran successfully, save as few-shot example for future queries
from src.rag.few_shot_store import FewShotStore

few_shot = FewShotStore()
if healed["success"]:
    few_shot.save(query=user_prompt, schema_summary=schema_str[:200], code=healed["code"])

# Before generating, check few-shot store for similar past examples
similar_example = few_shot.find_similar(user_prompt)
if similar_example:
    # Add to prompt as "Here's a similar working example: ..."
```

**Checkpoint:**
- After 10+ successful generations, few-shot store should have 10+ entries
- Similar queries should retrieve relevant past examples
- System should produce better results over time as more examples accumulate

---

## Bonus Step 9: Streamlit Demo UI

> **Goal:** A visual interface to demo the full pipeline. Upload CSV, see schema insights, pick a prompt (or write your own), generate code, see execution results — all in one page. Not production UI, just a demo/testing tool.

**Owner:** Anyone
**Time:** Day 15-16
**Depends on:** Step 6.5 (execution feedback), Step 8.5 (few-shot store) — but can start with just Step 3 + Step 6

### 9.1 Install Streamlit

```bash
pip install streamlit
```

### 9.2 Build the Demo App

**File: `streamlit_demo.py`**

The UI should have these sections:

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar                                                │
│  ├── Ollama status (🟢/🟡)                              │
│  ├── RAG stats (chunks indexed)                         │
│  └── Few-shot count                                     │
│                                                         │
│  Main Area                                              │
│  ├── CSV Upload / Sample Dataset button                 │
│  ├── 📊 Metric Cards (rows, columns, nulls, issues)    │
│  └── Tabs:                                              │
│      ├── 🔍 Column Details (table)                      │
│      ├── ⚠️ Issues (alerts)                             │
│      ├── 💡 Insights (auto-generated)                   │
│      ├── 📋 LLM Prompt Preview                          │
│      └── 🤖 Code Generation                             │
│          ├── Preset prompts (buttons)                    │
│          ├── Custom prompt (text area)                   │
│          ├── Generated code (syntax highlighted)        │
│          ├── Execution result (✅/❌ + output)           │
│          └── Attempt count (1st try / 2nd try / ...)    │
└─────────────────────────────────────────────────────────┘
```

### 9.3 Key Features

```python
# Pseudo-code for the generation tab
import streamlit as st
from src.llm.pipeline import CodePipeline
from src.llm.self_healer import SelfHealer

pipeline = CodePipeline()
healer = SelfHealer(max_attempts=3)

# User writes prompt or picks preset
user_prompt = st.text_area("What do you want to do with this CSV?")

if st.button("Generate Code"):
    # 1. Pipeline generates code (schema + RAG + LLM)
    result = pipeline.generate(csv_path, user_prompt)
    st.code(result.code, language="python")

    # 2. Execution feedback
    healed = healer.run_with_retry(result.code)

    if healed["success"]:
        st.success(f"✅ Code runs! ({healed['attempts']} attempt(s))")
        st.text(healed["output"])
    else:
        st.error(f"❌ Failed after {healed['attempts']} attempts")
        st.code(healed["last_error"])
```

### 9.4 Preset Prompts

Include dataset-specific preset prompts. For Titanic:

```python
TITANIC_PROMPTS = {
    "🚢 Survival by Gender": "Calculate survival rate by Sex, show bar chart",
    "💰 Class & Fare": "Average Fare by Pclass, bar chart with passenger count",
    "👶 Age Distribution": "Histogram of Age for survived vs died, handle NaN",
    "👨‍👩‍👧 Family Effect": "Create family_size from SibSp+Parch, survival rate by family size",
    "🚪 Embarkation Analysis": "Survival rate and avg fare by Embarked, dual-axis chart",
    "📊 Summary Pivot": "Pivot table: Pclass x Sex with survival rate, avg age, avg fare",
}
```

For generic CSVs, show general-purpose prompts:

```python
GENERIC_PROMPTS = {
    "📊 Basic Stats": "Show descriptive statistics for all numeric columns",
    "🔍 Null Analysis": "Show null counts and percentages, suggest how to handle them",
    "📈 Distribution": "Plot histogram for each numeric column",
    "🔗 Correlation": "Show correlation matrix heatmap for numeric columns",
    "📋 Top Values": "Show value counts for each categorical column",
}
```

### 9.5 Checkpoint

- Streamlit runs without errors: `streamlit run streamlit_demo.py`
- CSV upload works and shows schema analysis
- Preset prompts fill the text area on click
- Code generation produces syntax-valid Python
- Execution feedback shows ✅/❌ result with attempt count
- Sample Titanic dataset is included for quick demo

> **Not:** This is an internal demo tool, not a production UI. Keep it simple. A proper web frontend is Phase 2 scope.

---

## Success Criteria Summary

Phase 1 is **DONE** when all of these are true:

- [ ] `ollama serve` runs with `qwen2.5-coder` model loaded
- [ ] `python cli.py --csv file.csv --prompt "..."` returns working code
- [ ] `POST /generate` API endpoint accepts CSV upload + prompt, returns code
- [ ] `POST /index` re-indexes knowledge base
- [ ] `/health` reports system status
- [ ] CSV Schema Analyzer correctly extracts types, nulls, issues from test CSVs
- [ ] RAG retrieves relevant pandas patterns for common queries
- [ ] RAG query is enriched with schema/column type info
- [ ] Execution feedback catches and auto-fixes broken code (max 3 retries)
- [ ] Successful generations are saved as few-shot examples
- [ ] 7/10 test scenarios produce correct, runnable Python code (target: 8/10 with feedback loop)
- [ ] All unit tests pass (`pytest tests/ -v`)

---

## What NOT to Build in Phase 1

Explicitly out of scope — save for Phase 2/3:

- ❌ Web UI (Phase 2) — *Streamlit demo is for internal testing only*
- ❌ Full sandboxing / containerized execution (Phase 3) — *basic subprocess is enough for now*
- ❌ Multi-file code generation
- ❌ Streaming responses
- ❌ User authentication
- ❌ Conversation memory / multi-turn chat
- ❌ Custom model fine-tuning
- ❌ AST-based code chunking (use simple markdown chunking for MVP, upgrade later)
- ❌ Agentic RAG / query routing (Phase 2 — keep retrieval simple for now)

---

*Last updated: 2026-03-04*
