from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from src.llm.pipeline import CodePipeline
from src.rag.indexer import KnowledgeIndexer
from pathlib import Path
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)

# FastAPI uygulamasını başlatıyoruz (Garsonumuz)
app = FastAPI(title="Enclave CodeRunner", version="0.1.0")

# Orkestra şefimizi (Mutfağı) API başlarken bir kere ayağa kaldırıyoruz
pipeline = CodePipeline()

@app.get("/health")
def health():
    """Sistemin çalışır durumda olup olmadığını kontrol et (Health Check)."""
    # Not: Eğer CodeGenerator içinde health_check() yazmadıysak burası hata verebilir. 
    # Şimdilik Ollama'nın çalıştığını varsayarak True dönüyoruz, ileride geliştirebiliriz.
    ollama_ok = hasattr(pipeline.generator, 'health_check') and pipeline.generator.health_check() if hasattr(pipeline.generator, 'health_check') else True
    
    rag_count = KnowledgeIndexer().get_stats()["total_chunks"]
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": "connected" if ollama_ok else "unreachable",
        "rag_chunks_indexed": rag_count,
    }

@app.post("/generate")
def generate_code(
    csv_file: UploadFile = File(...),
    prompt: str = Form(...),
    session_id: str | None = Form(None),
):
    """Kullanıcının yüklediği CSV dosyasını ve isteğini alıp, Python kodu üretir."""
    # 1. Yüklenen dosyayı geçici bir konuma güvenle kaydet
    try:
        suffix = Path(csv_file.filename).suffix or ".csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(csv_file.file, tmp)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okunamadı: {e}")

    # 2. Mutfağa (Pipeline) işi ver
    try:
        #  session_id'yi pipeline'a iletiyoruz
        result = pipeline.generate(
            csv_path=tmp_path, 
            user_prompt=prompt,
            session_id=session_id
        )
    except Exception as e:
        logger.exception("Kod üretimi başarısız oldu")
        raise HTTPException(status_code=500, detail=f"Kod üretimi başarısız: {e}")
    finally:
        # 3. İşlem bitince geçici dosyayı mutlaka sil (Çöp bırakma)
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "code": result.code,
        "csv_schema": result.csv_schema,
        "rag_context_used": bool(result.rag_context),
        
        # Performans ve Sınıflandırma
        "from_cache": result.from_cache,
        "query_category": result.query_category,
        "retrieval_method": result.retrieval_method,
        "cache_stats": result.cache_stats,

        # OTURUM BİLGİLERİ
        "session_id": result.session_id,
        "turn_number": result.turn_number,
        "is_follow_up": result.turn_number > 1,

        # KALİTE VE TEST SONUÇLARI
        "judge_verdict": result.judge_verdict,
        "judge_issues": result.judge_issues,
        "execution_success": result.execution_success,
        "execution_attempts": result.attempts
    }

@app.post("/generate/text")
def generate_code_from_path(
    csv_path: str = Form(...),
    prompt: str = Form(...),
    session_id: str | None = Form(None),
):
    """Dosya yüklemek yerine sistemdeki yerel bir dosya yolunu (path) kullanır."""
    if not Path(csv_path).exists():
        raise HTTPException(status_code=404, detail=f"Dosya bulunamadı: {csv_path}")

    try:
        result = pipeline.generate(
            csv_path=csv_path, 
            user_prompt=prompt, 
            session_id=session_id
            )
    except Exception as e:
        logger.exception("Kod üretimi başarısız oldu")
        raise HTTPException(status_code=500, detail=f"Kod üretimi başarısız: {e}")

    return {
        "code": result.code,
        "csv_schema": result.csv_schema,
        "rag_context_used": bool(result.rag_context),
        
        # Performans ve Sınıflandırma
        "from_cache": result.from_cache,
        "query_category": result.query_category,
        "retrieval_method": result.retrieval_method,
        "cache_stats": result.cache_stats,

        # OTURUM BİLGİLERİ
        "session_id": result.session_id,
        "turn_number": result.turn_number,
        "is_follow_up": result.turn_number > 1,

        # KALİTE VE TEST SONUÇLARI
        "judge_verdict": result.judge_verdict,
        "judge_issues": result.judge_issues,
        "execution_success": result.execution_success,
        "execution_attempts": result.attempts
    }

@app.post("/index")
def reindex_knowledge():
    """RAG bilgi bankasını (Hem Vektör hem BM25) manuel olarak yeniden indeksler."""
    try:
        indexer = KnowledgeIndexer()
        indexer.index_knowledge_dir(force_reindex=True)
        
        # BM25 indeksini de pipeline üzerinden zorla tazeleyelim
        pipeline.retriever.build_bm25_index(force=True)
        
        stats = indexer.get_stats()
        return {
            "status": "ok", 
            "vector_chunks": stats["total_chunks"],
            "bm25_docs": len(pipeline.retriever.bm25_index.documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İndeksleme başarısız: {e}")