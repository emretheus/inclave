# Enclave CodeRunner

Local, privacy-first code generation system powered by Ollama. Upload a CSV + describe what you need in plain English → get working Python code back.

## What It Does

```
You:   "Group by city and show total revenue"  +  sales.csv
                        ↓
CodeRunner:  analyzes CSV schema → retrieves relevant pandas patterns → generates code
                        ↓
Output:  complete, runnable Python script using pandas
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Ollama (`qwen2.5-coder`) |
| Embeddings | `nomic-embed-text` |
| RAG | LlamaIndex + ChromaDB |
| API | FastAPI |
| Language | Python 3.11+ |

Everything runs **100% locally** — no cloud APIs, no data leaves your machine.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running

### Setup

```bash
# 1. Pull required models
ollama pull qwen2.5-coder:14b
ollama pull nomic-embed-text

# 2. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install ollama chromadb llama-index fastapi uvicorn python-dotenv pandas \
    llama-index-llms-ollama llama-index-embeddings-ollama llama-index-vector-stores-chroma \
    pydantic-settings

# 3. Configure
cp .env.example .env   # edit if needed

# 4. Run
python main.py
```

### Usage

**API:**
```bash
curl -X POST http://localhost:8000/generate \
  -F "csv_file=@data/sample_csvs/sales_data.csv" \
  -F "prompt=Show total revenue by city"
```

**CLI:**
```bash
# Single prompt
python cli.py --csv data/sample_csvs/sales_data.csv --prompt "Show the first 5 rows"

# Interactive mode
python cli.py --csv data/sample_csvs/sales_data.csv
```

## Project Structure

```
src/
├── llm/            # Ollama client + prompt templates
├── rag/            # Indexing, chunking, retrieval
├── csv_engine/     # CSV schema analysis
├── api/            # FastAPI endpoints
└── vectordb/       # ChromaDB wrapper
```

## Docs

- [Phase 1 Implementation Plan](PHASE1_PLAN.md) — step-by-step build guide
- [Reading List](READING_LIST.md) — curated articles for the team

## Team

3-person project. See [PHASE1_PLAN.md](PHASE1_PLAN.md) for task assignments and weekly schedule.

## License

TBD
