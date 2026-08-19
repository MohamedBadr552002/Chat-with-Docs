"""
Embedding model provider — returns a cached HuggingFaceEmbeddings instance.
"""

from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils.config import EMBEDDING_MODEL
from src.utils.logger_config import logger


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Return a singleton HuggingFaceEmbeddings instance.
    Uses sentence-transformers all-MiniLM-L6-v2 by default.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("Embedding model loaded.")
    return embeddings
