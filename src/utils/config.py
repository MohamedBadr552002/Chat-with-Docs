import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_TTL = int(os.getenv("REDIS_TTL", 3600))

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "knowledge_base")

GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "gemini-1.5-flash")
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 4))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 5))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
