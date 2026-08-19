"""
ChromaDB vector store manager.
Provides add / retrieve operations on the persistent knowledge collection.
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma
from src.ingestion.embeddings import get_embeddings
from src.utils.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from src.utils.logger_config import logger

try:
    import streamlit as st
    _st_cache = st.cache_resource
except Exception:
    import functools
    _st_cache = lambda f: functools.lru_cache(maxsize=1)(f)

_vectorstore: Optional[Chroma] = None


def get_vectorstore() -> Chroma:
    """Return the singleton ChromaDB vectorstore, creating it if needed."""
    global _vectorstore
    if _vectorstore is None:
        logger.info(
            f"Initialising ChromaDB: collection='{CHROMA_COLLECTION_NAME}' "
            f"persist_dir='{CHROMA_PERSIST_DIR}'"
        )
        _vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR,
        )
    return _vectorstore


def add_documents(documents: List[Document]) -> List[str]:
    """
    Add chunked documents to the vector store.

    Returns:
        List of inserted document IDs.
    """
    if not documents:
        logger.warning("add_documents called with empty list — skipping.")
        return []

    vs = get_vectorstore()
    ids = vs.add_documents(documents)
    logger.info(f"Added {len(documents)} chunks to ChromaDB → IDs: {ids[:3]}…")
    return ids


def reset_vectorstore() -> None:
    """Delete and reinitialise the collection (useful for re-ingestion)."""
    global _vectorstore
    logger.warning("Resetting ChromaDB collection.")
    vs = get_vectorstore()
    vs.delete_collection()
    _vectorstore = None
    get_vectorstore()
    logger.info("ChromaDB collection reset complete.")


def collection_count() -> int:
    """Return the number of chunks currently stored."""
    try:
        vs = get_vectorstore()
        return vs._collection.count()
    except Exception:
        return 0
