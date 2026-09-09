"""
Document Management Module

Extracts and manages document ingestion logic with support for multiple file formats,
chunking, metadata enrichment, and multi-backend storage (local FAISS + optional Supabase).

Example:
    >>> from embeddings_rag import AdvancedRAG
    >>> dm = DocumentManager(rag=AdvancedRAG(llm=None))
    >>> asset = dm.ingest("report.pdf", {"category": "Reporting", "priority": "High"})
    >>> assert asset.chunk_count > 0
    >>> assert dm.get_document(asset.doc_id) is not None
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import numpy as np
from docx import Document
from PIL import Image
import pandas as pd
import pytesseract
from pypdf import PdfReader
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from langdetect import detect as langdetect_detect
except ImportError:
    def langdetect_detect(text: str) -> str:  # type: ignore
        return "unknown"

from embeddings_rag import AdvancedRAG

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class DocumentIngestionError(Exception):
    """Raised when document parsing or ingestion fails.
    
    Provides clear, user-friendly error messages for UI display.
    """
    def __init__(self, file_path: str, format: str, cause: Exception):
        self.file_path = file_path
        self.format = format
        self.cause = cause
        msg = (
            f"Failed to ingest '{Path(file_path).name}' (format: {format}). "
            f"Original error: {str(cause)}"
        )
        super().__init__(msg)


class UnsupportedFormatError(Exception):
    """Raised when file format is not in supported_formats."""
    
    SUPPORTED_FORMATS = [".pdf", ".csv", ".xlsx", ".xls", ".docx", ".tiff", ".tif", ".png", ".jpg"]
    
    def __init__(self, file_path: str, extension: str):
        self.file_path = file_path
        self.extension = extension
        msg = (
            f"Unsupported file format '{extension}' for '{Path(file_path).name}'. "
            f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
        )
        super().__init__(msg)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class DocumentAsset:
    """Represents an ingested document with metadata and chunk information."""
    
    doc_id: str
    filename: str
    category: str
    chunk_count: int
    ingested_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    _supabase_synced: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "category": self.category,
            "chunk_count": self.chunk_count,
            "ingested_at": self.ingested_at,
            "metadata": self.metadata,
            "_supabase_synced": self._supabase_synced,
        }


# ============================================================================
# DOCUMENT PARSERS
# ============================================================================

def _read_pdf(path: Path) -> str:
    """Extract text from PDF using PyPDF."""
    try:
        reader = PdfReader(str(path))
        texts = []
        for page_idx, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                if text.strip():
                    texts.append(f"[Page {page_idx + 1}]\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_idx + 1}: {e}")
                texts.append(f"[Page {page_idx + 1} - extraction failed]")
        # If PyPDF extracted no text (likely image-based PDF), try OCR via PyMuPDF rendering
        if not texts and fitz is not None:
            try:
                doc = fitz.open(str(path))
                ocr_texts = []
                for i, page in enumerate(doc):
                    try:
                        page_text = page.get_text().strip()
                        if page_text:
                            ocr_texts.append(f"[Page {i+1}]\n{page_text}")
                            continue
                        # Render page to image and OCR
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        mode = "RGB" if pix.n < 4 else "RGBA"
                        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                        ocr_result = pytesseract.image_to_string(img, lang="eng")
                        if ocr_result and ocr_result.strip():
                            ocr_texts.append(f"[Page {i+1} - ocr]\n{ocr_result}")
                    except Exception as e:
                        logger.warning(f"OCR fallback failed for page {i+1}: {e}")
                        ocr_texts.append(f"[Page {i+1} - ocr failed]")
                if ocr_texts:
                    return "\n".join(ocr_texts)
            except Exception as e:
                logger.warning(f"PyMuPDF OCR fallback failed: {e}")

        return "\n".join(texts)
    except Exception as e:
        raise DocumentIngestionError(str(path), ".pdf", e)


def _read_excel(path: Path) -> str:
    """Extract text from Excel using pandas."""
    try:
        excel_file = pd.ExcelFile(str(path))
        sheets_text = []
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet_name)
            sheet_header = f"[Sheet: {sheet_name}]\n"
            
            # Include column headers
            headers = " | ".join(str(col) for col in df.columns)
            rows = []
            for _, row in df.iterrows():
                row_str = " | ".join(str(v) for v in row.tolist() if pd.notna(v))
                if row_str.strip():
                    rows.append(row_str)
            
            sheet_text = sheet_header + headers + "\n" + "\n".join(rows)
            sheets_text.append(sheet_text)
        
        return "\n".join(sheets_text)
    except Exception as e:
        raise DocumentIngestionError(str(path), path.suffix, e)


def _read_docx(path: Path) -> str:
    """Extract text from Word document using python-docx."""
    try:
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        
        # Also extract table content
        tables_text = []
        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                table_rows.append(" | ".join(cells))
            tables_text.append("\n".join(table_rows))
        
        all_text = paragraphs + tables_text
        return "\n".join(all_text)
    except Exception as e:
        raise DocumentIngestionError(str(path), ".docx", e)


def _read_csv(path: Path) -> str:
    """Extract text from CSV using pandas."""
    try:
        df = pd.read_csv(path)
        headers = " | ".join(str(col) for col in df.columns)
        rows = []
        for _, row in df.iterrows():
            row_str = " | ".join(str(v) for v in row.tolist() if pd.notna(v))
            if row_str.strip():
                rows.append(row_str)
        return f"[CSV]\n{headers}\n" + "\n".join(rows)
    except Exception as e:
        raise DocumentIngestionError(str(path), ".csv", e)


def _read_image_ocr(path: Path) -> str:
    """Extract text from image using pytesseract OCR."""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng")
        if not text.strip():
            logger.warning(f"OCR extracted no text from {path.name}")
        return text
    except Exception as e:
        raise DocumentIngestionError(str(path), path.suffix, e)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def detect_language(text: str) -> str:
    """
    Detect language of text using langdetect.
    
    Returns ISO 639-1 code ('en', 'am', etc.) or 'unknown' on failure.
    Never raises an exception.
    
    Args:
        text: Text to detect language for (uses first 500 chars)
    
    Returns:
        ISO language code or 'unknown'
    """
    try:
        if not text or not text.strip():
            return "unknown"
        # Use only first 500 characters for performance
        result = langdetect_detect(text[:500])
        return str(result) if result else "unknown"
    except Exception as e:
        logger.debug(f"Language detection failed: {e}")
        return "unknown"


def _chunk_text(text: str, chunk_size: int = 1600, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Overlap between chunks in characters
    
    Returns:
        List of text chunks, filtering out very small tail chunks
    """
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        # Skip tiny tail chunks
        if len(chunk) > 50:
            chunks.append(chunk)
    return chunks


# ============================================================================
# DOCUMENT MANAGER
# ============================================================================

class DocumentManager:
    """
    Manages document ingestion, storage, and retrieval.
    
    Supports multiple file formats (PDF, Excel, Word, images with OCR),
    automatic chunking with metadata enrichment, and optional Supabase sync.
    
    Attributes:
        rag: AdvancedRAG instance for vector indexing
        supabase_client: Optional Supabase client for remote sync
        documents: Dict mapping doc_id to DocumentAsset
        supported_formats: List of supported file extensions
    """
    
    SUPPORTED_FORMATS = [".pdf", ".csv", ".xlsx", ".xls", ".docx", ".tiff", ".tif", ".png", ".jpg"]
    CHUNK_SIZE = 1600  # characters (optimized for BGE-M3)
    CHUNK_OVERLAP = 200  # characters
    MIN_CHUNK_SIZE = 50  # skip tiny tail chunks
    
    def __init__(self, rag: AdvancedRAG, supabase_client: Optional[Any] = None):
        """
        Initialize DocumentManager.
        
        Args:
            rag: AdvancedRAG instance for embeddings and indexing
            supabase_client: Optional Supabase client for remote sync
        """
        self.rag = rag
        self.supabase_client = supabase_client
        self.documents: Dict[str, DocumentAsset] = {}
        self.supported_formats = self.SUPPORTED_FORMATS.copy()
    
    def ingest(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentAsset:
        """
        Ingest a document file with automatic parsing, chunking, and indexing.
        
        Steps:
        1. Validate file exists and format is supported
        2. Parse file according to format
        3. Chunk text with overlap
        4. Build enriched metadata for each chunk (language, timestamps, etc.)
        5. Add to RAG index and build FAISS index
        6. Sync to Supabase if available
        7. Store and return DocumentAsset
        
        Args:
            file_path: Path to document file
            metadata: Optional metadata dict with keys:
                - category: Document category (default: "General")
                - priority: Priority level (default: "Medium")
                - due_date: Due date string (default: None)
                - user_goal: User's goal for this document (default: "")
                - Any custom fields are passed through
        
        Returns:
            DocumentAsset containing doc_id, filename, chunk_count, etc.
        
        Raises:
            FileNotFoundError: If file doesn't exist
            UnsupportedFormatError: If file extension not supported
            DocumentIngestionError: If parsing fails
        """
        file_path_obj = Path(file_path)
        metadata = metadata or {}
        
        # Step 1: Validate file exists and extension supported
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = file_path_obj.suffix.lower()
        if extension not in self.supported_formats:
            raise UnsupportedFormatError(file_path, extension)
        
        # Step 2: Parse file according to format
        logger.info(f"Parsing {file_path_obj.name} (format: {extension})")
        if extension == ".pdf":
            text = _read_pdf(file_path_obj)
        elif extension in [".csv"]:
            text = _read_csv(file_path_obj)
        elif extension in [".xlsx", ".xls"]:
            text = _read_excel(file_path_obj)
        elif extension == ".docx":
            text = _read_docx(file_path_obj)
        elif extension in [".png", ".jpg", ".jpeg", ".tiff", ".tif"]:
            text = _read_image_ocr(file_path_obj)
        else:
            raise UnsupportedFormatError(file_path, extension)
        
        if not text or not text.strip():
            raise DocumentIngestionError(
                file_path, extension,
                ValueError("Document parsing produced empty text")
            )
        
        # Step 3: Chunk text with overlap
        chunks = _chunk_text(text, chunk_size=self.CHUNK_SIZE, overlap=self.CHUNK_OVERLAP)
        if not chunks:
            raise DocumentIngestionError(
                file_path, extension,
                ValueError("Text chunking produced no chunks")
            )
        
        logger.info(f"Created {len(chunks)} chunks from {file_path_obj.name}")
        
        # Step 4: Build enriched metadata for each chunk
        doc_id = str(uuid4())
        ingested_at = datetime.utcnow().isoformat()
        category = metadata.get("category", "General")
        
        rag_documents: List[Tuple[str, Dict[str, Any]]] = []
        
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_meta = {
                "doc_id": doc_id,
                "filename": file_path_obj.name,
                "source_path": str(file_path_obj),
                "chunk_index": chunk_idx,
                "total_chunks": len(chunks),
                "category": category,
                "priority": metadata.get("priority", "Medium"),
                "due_date": metadata.get("due_date", None),
                "user_goal": metadata.get("user_goal", ""),
                "language": detect_language(chunk_text),
                "ingested_at": ingested_at,
                # Pass through any custom metadata fields
                **{k: v for k, v in metadata.items()
                   if k not in ["category", "priority", "due_date", "user_goal"]},
            }
            rag_documents.append((chunk_text, chunk_meta))
        
        # Step 5: Add to RAG index
        logger.info(f"Adding {len(rag_documents)} chunk(s) to RAG index")
        self.rag.add_documents(rag_documents)
        
        # Step 6: Sync to Supabase if available
        supabase_synced = True
        if self.supabase_client is not None:
            try:
                logger.info(f"Syncing {len(rag_documents)} chunks to Supabase")
                # Prepare documents for Supabase with embeddings
                supabase_docs = []
                for chunk_text, chunk_meta in rag_documents:
                    embedding = self.rag.embeddings.embed_query(chunk_text)
                    supabase_docs.append({
                        "id": f"{doc_id}-{chunk_meta['chunk_index']}",
                        "content": chunk_text,
                        "metadata": chunk_meta,
                        "embedding": embedding,
                    })
                self.supabase_client.upsert_documents(supabase_docs)
            except Exception as e:
                supabase_synced = False
                doc_id_sample = f"{doc_id}-0"
                warning_msg = (
                    f"Supabase sync failed for {doc_id_sample} — "
                    f"local index is ahead of remote. Re-upload to sync."
                )
                logger.warning(f"{warning_msg} Details: {e}")
        
        # Step 7: Create and store DocumentAsset
        asset = DocumentAsset(
            doc_id=doc_id,
            filename=file_path_obj.name,
            category=category,
            chunk_count=len(chunks),
            ingested_at=ingested_at,
            metadata=metadata,
            _supabase_synced=supabase_synced,
        )
        self.documents[doc_id] = asset
        
        logger.info(f"Successfully ingested document {doc_id} with {len(chunks)} chunks")
        return asset
    
    def get_document(self, doc_id: str) -> Optional[DocumentAsset]:
        """
        Retrieve a document asset by ID.
        
        Args:
            doc_id: Document ID (UUID string)
        
        Returns:
            DocumentAsset if found, None otherwise
        """
        return self.documents.get(doc_id)
    
    def list_documents(self, category: Optional[str] = None) -> List[DocumentAsset]:
        """
        List all documents, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
        
        Returns:
            List of DocumentAsset objects
        """
        docs = list(self.documents.values())
        if category:
            docs = [d for d in docs if d.category == category]
        return docs
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from local storage and Supabase.
        
        Args:
            doc_id: Document ID to delete
        
        Returns:
            True if document was deleted, False if not found
        """
        if doc_id not in self.documents:
            return False
        
        asset = self.documents[doc_id]
        
        # Remove from local documents dict
        del self.documents[doc_id]
        logger.info(f"Deleted document {doc_id} from local storage")
        
        # Note: Supabase deletion would require implementing a delete method
        # on the SupabaseClient class. For now, local deletion is supported.
        # Document chunks remain in Supabase but are orphaned (consider cleanup strategy).
        
        return True
