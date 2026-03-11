from src.vectordb.store import VectorStore
from src.rag.chunking import MarkdownCodeChunker
from src.config import settings


class KnowledgeIndexer:
    """Indexes knowledge documents into the vector store."""

    def __init__(self):
        self.store = VectorStore(collection_name="knowledge")
        self.chunker = MarkdownCodeChunker()

    def index_knowledge_dir(self, force_reindex: bool = False):
        knowledge_dir = settings.knowledge_dir

        if force_reindex:
            self.store.reset()

        if self.store.count() > 0 and not force_reindex:
            return

        chunks = self.chunker.chunk_directory(knowledge_dir)
        if not chunks:
            return

        self.store.add_documents(
            doc_ids=[c.id for c in chunks],
            texts=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    def get_stats(self) -> dict:
        return {"total_chunks": self.store.count()}
