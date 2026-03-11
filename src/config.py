import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    code_model: str = os.getenv("CODE_MODEL", "qwen2.5-coder:7b")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb"))
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", "./data/knowledge"))


settings = Settings()
