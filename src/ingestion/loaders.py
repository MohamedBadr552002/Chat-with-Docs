"""
Loaders for all supported knowledge source types:
PDF, DOCX, TXT, source code, PPT/PPTX, URL, Wikipedia, WAV (speech-to-text).
"""

import os
import tempfile
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from src.utils.logger_config import logger


def load_pdf(file_path: str) -> List[Document]:
    """Load a PDF file and return a list of Documents."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        logger.info(f"Loaded PDF: {file_path} → {len(docs)} pages")
        return docs
    except Exception as e:
        logger.error(f"Failed to load PDF {file_path}: {e}")
        raise


def load_docx(file_path: str) -> List[Document]:
    """Load a DOCX file."""
    try:
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        logger.info(f"Loaded DOCX: {file_path} → {len(docs)} docs")
        return docs
    except Exception as e:
        logger.error(f"Failed to load DOCX {file_path}: {e}")
        raise


def load_txt(file_path: str) -> List[Document]:
    """Load a plain text or source-code file."""
    try:
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)
        docs = loader.load()
        logger.info(f"Loaded TXT/code: {file_path} → {len(docs)} docs")
        return docs
    except Exception as e:
        logger.error(f"Failed to load TXT {file_path}: {e}")
        raise


def load_pptx(file_path: str) -> List[Document]:
    """Load a PowerPoint presentation (PPT/PPTX)."""
    try:
        from pptx import Presentation
        prs = Presentation(file_path)
        slides_text = []
        for i, slide in enumerate(prs.slides):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text.strip())
            if texts:
                slides_text.append(
                    Document(
                        page_content="\n".join(texts),
                        metadata={"source": file_path, "slide": i + 1},
                    )
                )
        logger.info(f"Loaded PPTX: {file_path} → {len(slides_text)} slides")
        return slides_text
    except Exception as e:
        logger.error(f"Failed to load PPTX {file_path}: {e}")
        raise


def load_url(url: str) -> List[Document]:
    """Load a web page via URL."""
    try:
        from langchain_community.document_loaders import WebBaseLoader
        loader = WebBaseLoader(url)
        docs = loader.load()
        logger.info(f"Loaded URL: {url} → {len(docs)} docs")
        return docs
    except Exception as e:
        logger.error(f"Failed to load URL {url}: {e}")
        raise


def load_wikipedia(query: str, lang: str = "en", load_max_docs: int = 2) -> List[Document]:
    """Load Wikipedia pages matching the query."""
    try:
        from langchain_community.document_loaders import WikipediaLoader
        loader = WikipediaLoader(query=query, lang=lang, load_max_docs=load_max_docs)
        docs = loader.load()
        logger.info(f"Loaded Wikipedia '{query}' → {len(docs)} docs")
        return docs
    except Exception as e:
        logger.error(f"Failed to load Wikipedia '{query}': {e}")
        raise


def load_wav(file_path: str) -> List[Document]:
    """
    Transcribe a WAV audio file using OpenAI Whisper and return a Document.
    Falls back to a stub message if Whisper is unavailable.
    """
    try:
        import whisper
        logger.info(f"Transcribing WAV: {file_path}")
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        transcript = result.get("text", "").strip()
        doc = Document(
            page_content=transcript,
            metadata={"source": file_path, "type": "audio_transcript"},
        )
        logger.info(f"Transcribed WAV: {file_path} → {len(transcript)} chars")
        return [doc]
    except ImportError:
        logger.warning("openai-whisper not installed. Returning placeholder.")
        return [
            Document(
                page_content="[Audio transcription unavailable: openai-whisper not installed]",
                metadata={"source": file_path, "type": "audio_transcript"},
            )
        ]
    except Exception as e:
        logger.error(f"Failed to transcribe WAV {file_path}: {e}")
        raise


# ─── Supported code file extensions ──────────────────────────────────────────
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go",
    ".rb", ".php", ".swift", ".kt", ".rs", ".scala", ".sh",
    ".html", ".css", ".sql", ".r", ".m",
}


def load_file(file_path: str) -> List[Document]:
    """
    Auto-detect file type and dispatch to the correct loader.
    Supports: PDF, DOCX, TXT, source code, PPT/PPTX, WAV.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext == ".docx":
        return load_docx(file_path)
    elif ext in {".txt"} | CODE_EXTENSIONS:
        return load_txt(file_path)
    elif ext in {".ppt", ".pptx"}:
        return load_pptx(file_path)
    elif ext == ".wav":
        return load_wav(file_path)
    else:
        # Attempt generic text load
        logger.warning(f"Unknown extension '{ext}', attempting text load: {file_path}")
        return load_txt(file_path)
