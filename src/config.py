"""Project configuration. Reads from .env file. Change values in .env, not here."""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# --- OLLAMA & MODELLER ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CODE_MODEL = os.getenv("CODE_MODEL", "qwen2.5-coder:14b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# --- DEPOLAMA YOLLARI ---
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb"))
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", "./data/knowledge"))

# --- HİBRİT RAG AYARLARI ---
VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", 0.6))
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", 0.4))
MIN_RETRIEVAL_SCORE = float(os.getenv("MIN_RETRIEVAL_SCORE", 0.3))

# --- SEMANTİK CACHE (ÖNBELLEK) ---
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_THRESHOLD", 0.92))
CACHE_MAX_AGE_SECONDS = int(os.getenv("CACHE_MAX_AGE", 604800)) # 7 Gün
CACHE_MAX_ENTRIES = int(os.getenv("MAX_ENTRIES", 1000)) 

# --- OTURUM & HAFIZA (MEMORY) ---
SESSION_TTL = int(os.getenv("SESSION_TTL", 3600)) # 1 Saat
CONTEXT_WINDOW_SIZE = int(os.getenv("CONTEXT_WINDOW", 3))

# --- SELF-HEALER & JUDGE ---
MAX_HEAL_ATTEMPTS = int(os.getenv("MAX_HEAL_ATTEMPTS", 3))