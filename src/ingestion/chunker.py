"""
Text chunker — splits Documents into overlapping chunks for embedding.
"""

from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.utils.logger_config import logger


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """
    Split a list of Documents into smaller overlapping chunks.

    Args:
        documents: Raw documents from loaders.
        chunk_size: Target token/character size per chunk.
        chunk_overlap: Number of characters overlapping between consecutive chunks.

    Returns:
        List of chunked Documents with original metadata preserved.
    """
    if not documents:
        logger.warning("chunk_documents received empty document list.")
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    chunks = splitter.split_documents(documents)
    logger.info(
        f"Chunked {len(documents)} docs → {len(chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return chunks
