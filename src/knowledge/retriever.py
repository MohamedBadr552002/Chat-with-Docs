"""
Hybrid retriever — combines dense (ChromaDB) and sparse (BM25) retrieval.
Uses Reciprocal Rank Fusion (RRF) to merge results from both retrievers.
"""

from typing import List, Dict

from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

from src.ingestion.vectorstore import get_vectorstore
from src.knowledge.cache import get_cached_retrieval, cache_retrieval
from src.utils.config import TOP_K_RETRIEVAL
from src.utils.logger_config import logger


def _rrf_merge(
    dense_docs: List[Document],
    bm25_docs: List[Document],
    dense_weight: float = 0.6,
    bm25_weight: float = 0.4,
    k: int = 60,
) -> List[Document]:
    """
    Reciprocal Rank Fusion of two ranked document lists.
    Deduplicates by page_content, then sorts by combined RRF score.
    """
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for rank, doc in enumerate(dense_docs):
        key = doc.page_content[:300]
        scores[key] = scores.get(key, 0) + dense_weight * (1 / (k + rank + 1))
        doc_map[key] = doc

    for rank, doc in enumerate(bm25_docs):
        key = doc.page_content[:300]
        scores[key] = scores.get(key, 0) + bm25_weight * (1 / (k + rank + 1))
        doc_map[key] = doc

    ranked = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [doc_map[k] for k in ranked]


def _retrieve_hybrid(question: str, top_k: int) -> List[Document]:
    """
    Run both dense and BM25 retrieval and merge with RRF.
    Falls back to dense-only when the knowledge base is empty.
    """
    vs = get_vectorstore()

    # Dense retrieval
    dense_docs: List[Document] = []
    try:
        dense_docs = vs.similarity_search(question, k=top_k)
    except Exception as e:
        logger.warning(f"Dense retrieval failed: {e}")

    # Fetch stored docs for BM25
    bm25_docs: List[Document] = []
    try:
        raw = vs._collection.get(include=["documents", "metadatas"])
        all_docs = [
            Document(page_content=d, metadata=m or {})
            for d, m in zip(raw["documents"], raw["metadatas"])
        ]
        if all_docs:
            bm25 = BM25Retriever.from_documents(all_docs, k=top_k)
            bm25_docs = bm25.invoke(question)
    except Exception as e:
        logger.warning(f"BM25 retrieval failed: {e}. Using dense-only.")

    if not dense_docs and not bm25_docs:
        return []

    merged = _rrf_merge(dense_docs, bm25_docs)
    return merged[:top_k]


def retrieve_context(
    question: str,
    top_k: int = TOP_K_RETRIEVAL,
    use_cache: bool = True,
) -> List[Document]:
    """
    Retrieve the top-k most relevant chunks for a question using hybrid search.

    Uses Redis cache when available to avoid redundant vector searches.

    Args:
        question: User's question string.
        top_k: Maximum number of chunks to return.
        use_cache: Whether to check/populate Redis cache.

    Returns:
        List of relevant Document chunks.
    """
    if use_cache:
        cached = get_cached_retrieval(question)
        if cached is not None:
            logger.info(f"[CACHE HIT] Retrieval for: '{question[:60]}…'")
            return cached

    logger.info(f"Retrieving context for: '{question[:80]}…'")
    try:
        docs = _retrieve_hybrid(question, top_k=top_k)
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        docs = []

    if not docs:
        logger.warning("No relevant documents found in knowledge base.")

    if use_cache and docs:
        cache_retrieval(question, docs)

    logger.info(f"Retrieved {len(docs)} chunks for question.")
    return docs


def format_context(docs: List[Document], max_chars: int = 6000) -> str:
    """
    Format a list of Documents into a single context string for LLM prompts.
    Truncates at max_chars to stay within context window limits.
    """
    if not docs:
        return "No relevant information found in the knowledge base."

    parts = []
    total = 0
    for i, doc in enumerate(docs, 1):
        src = doc.metadata.get("source", "unknown")
        block = f"[Source {i}: {src}]\n{doc.page_content}"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(block[:remaining] + "…")
            break
        parts.append(block)
        total += len(block)

    return "\n\n---\n\n".join(parts)
