from __future__ import annotations
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