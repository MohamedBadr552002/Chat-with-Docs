"""Lightweight Chroma metadata access for UI and health checks."""

from functools import lru_cache

from src.utils.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR


@lru_cache(maxsize=1)
def _collection():
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_or_create_collection(CHROMA_COLLECTION_NAME)


def collection_count() -> int:
    """Return the chunk count without loading LangChain or embeddings."""
    try:
        return _collection().count()
    except Exception:
        return 0


def collection_metadata() -> list:
    """Return stored metadata without constructing the LangChain vectorstore."""
    try:
        return _collection().get(include=["metadatas"]).get("metadatas", [])
    except Exception:
        return []
