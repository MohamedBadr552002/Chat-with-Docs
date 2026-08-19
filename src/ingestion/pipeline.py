"""
Ingestion pipeline — orchestrates load → chunk → embed → store.
Supports files (PDF, DOCX, TXT, code, PPT/PPTX, WAV), URLs, and Wikipedia.
"""

import hashlib
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

from src.ingestion.loaders import load_file, load_url, load_wikipedia
from src.ingestion.chunker import chunk_documents
from src.ingestion.vectorstore import add_documents, collection_count
from src.knowledge.cache import get_redis_client
from src.utils.config import REDIS_TTL
from src.utils.logger_config import logger


def _source_hash(source: str) -> str:
    """Compute a short hash to use as a Redis cache key."""
    return hashlib.md5(source.encode()).hexdigest()[:16]


def _already_ingested(source: str) -> bool:
    """
    Check Redis to see if this source was already ingested.
    Avoids redundant reprocessing of the same file/URL.
    """
    redis = get_redis_client()
    if redis is None:
        return False
    key = f"ingested:{_source_hash(source)}"
    return redis.exists(key) == 1


def _mark_ingested(source: str) -> None:
    """Mark a source as ingested in Redis with a TTL."""
    redis = get_redis_client()
    if redis is None:
        return
    key = f"ingested:{_source_hash(source)}"
    redis.setex(key, REDIS_TTL, "1")


def ingest_file(file_path: str, force: bool = False) -> dict:
    """
    Full ingestion pipeline for a local file.

    Args:
        file_path: Absolute or relative path to the file.
        force: If True, re-ingest even if already cached.

    Returns:
        dict with status, chunks_added, source.
    """
    source = str(Path(file_path).resolve())

    if not force and _already_ingested(source):
        logger.info(f"[CACHE HIT] Source already ingested: {source}")
        return {"status": "cached", "chunks_added": 0, "source": source}

    logger.info(f"Ingesting file: {source}")
    docs = load_file(source)
    chunks = chunk_documents(docs)
    ids = add_documents(chunks)
    _mark_ingested(source)

    logger.info(f"Ingestion complete: {source} → {len(ids)} chunks stored.")
    return {"status": "success", "chunks_added": len(ids), "source": source}


def ingest_url(url: str, force: bool = False) -> dict:
    """
    Full ingestion pipeline for a web page URL.
    """
    if not force and _already_ingested(url):
        logger.info(f"[CACHE HIT] URL already ingested: {url}")
        return {"status": "cached", "chunks_added": 0, "source": url}

    logger.info(f"Ingesting URL: {url}")
    docs = load_url(url)
    chunks = chunk_documents(docs)
    ids = add_documents(chunks)
    _mark_ingested(url)

    logger.info(f"URL ingestion complete: {url} → {len(ids)} chunks stored.")
    return {"status": "success", "chunks_added": len(ids), "source": url}


def ingest_wikipedia(query: str, force: bool = False) -> dict:
    """
    Full ingestion pipeline for a Wikipedia query.
    """
    wiki_key = f"wikipedia:{query}"
    if not force and _already_ingested(wiki_key):
        logger.info(f"[CACHE HIT] Wikipedia already ingested: {query}")
        return {"status": "cached", "chunks_added": 0, "source": wiki_key}

    logger.info(f"Ingesting Wikipedia: {query}")
    docs = load_wikipedia(query)
    chunks = chunk_documents(docs)
    ids = add_documents(chunks)
    _mark_ingested(wiki_key)

    logger.info(f"Wikipedia ingestion complete: '{query}' → {len(ids)} chunks stored.")
    return {"status": "success", "chunks_added": len(ids), "source": wiki_key}


def get_knowledge_stats() -> dict:
    """Return current knowledge base statistics."""
    return {
        "total_chunks": collection_count(),
    }
