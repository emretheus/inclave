import uvicorn
import logging

from src.api.routes import app
from src.rag.indexer import KnowledgeIndexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def startup():
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
