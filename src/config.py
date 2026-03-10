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

# Settings object for modules that use dot-notation (settings.embed_model etc.)
class Settings:
    ollama_base_url = OLLAMA_BASE_URL
    code_model = CODE_MODEL
    embed_model = EMBED_MODEL
    chroma_persist_dir = CHROMA_PERSIST_DIR
    knowledge_dir = KNOWLEDGE_DIR

settings = Settings()