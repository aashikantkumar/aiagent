"""
SRS Loader — unified document loading with RAG support.

Refactored to use the new DocumentProcessor and EmbeddingEngine.
Supports: PDF, DOCX, Markdown, plain text.
"""
import os
import uuid
from typing import Optional
from langchain_community.document_loaders import (
    PyMuPDFLoader, Docx2txtLoader, TextLoader
)
from core.logger import get_logger

logger = get_logger(__name__)


def load_srs(path: str) -> str:
    """
    Load SRS text from a file.
    
    Supports: .pdf, .docx, .txt, .md
    Uses LangChain loaders for basic loading (backward compatible).
    """
    ext = path.rsplit('.', 1)[-1].lower()
    
    loader_map = {
        'pdf':  PyMuPDFLoader,
        'docx': Docx2txtLoader,
        'txt':  TextLoader,
        'md':   TextLoader,
    }
    
    if ext not in loader_map:
        raise ValueError(f"Unsupported file extension: {ext}")
        
    loader = loader_map[ext](path)
    docs = loader.load()
    return '\n\n'.join(d.page_content for d in docs)


def load_srs_with_rag(path: str, enable_rag: bool = True) -> dict:
    """
    Load SRS document with optional RAG indexing.
    
    Returns:
        dict with:
          - text: full document text
          - document_id: unique ID for RAG retrieval
          - chunks: number of chunks indexed
          - rag_enabled: whether RAG was set up
    """
    result = {
        "text": "",
        "document_id": str(uuid.uuid4()),
        "chunks": 0,
        "rag_enabled": False,
    }

    # 1. Parse the document
    try:
        from agent.document_processor import DocumentParser, SemanticChunker

        parser = DocumentParser()
        doc = parser.parse(path)
        result["text"] = doc.text

        # 2. Chunk and index for RAG (if enabled and dependencies available)
        if enable_rag and doc.text:
            try:
                from agent.embedding_engine import EmbeddingEngine

                chunker = SemanticChunker(chunk_size=1000, chunk_overlap=200)
                chunks = chunker.chunk_document(doc)

                engine = EmbeddingEngine()
                stored = engine.store_chunks(chunks, document_id=result["document_id"])

                result["chunks"] = stored
                result["rag_enabled"] = True

                logger.info(
                    "srs_loaded_with_rag",
                    file=os.path.basename(path),
                    chunks=stored,
                    document_id=result["document_id"],
                )

            except ImportError as e:
                logger.warning(
                    "rag_dependencies_missing",
                    error=str(e),
                    hint="pip install sentence-transformers chromadb",
                )
            except Exception as e:
                logger.warning("rag_indexing_failed", error=str(e))

    except ImportError:
        # Fallback to basic loader
        result["text"] = load_srs(path)
    except Exception as e:
        # Fallback to basic loader
        logger.warning("advanced_parser_failed", error=str(e), fallback="basic")
        result["text"] = load_srs(path)

    if not result["text"]:
        raise ValueError(f"No text could be extracted from: {path}")

    return result
