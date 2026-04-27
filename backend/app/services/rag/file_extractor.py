"""
File Content Extractor for AURA RAG Pipeline.

Extracts text content from uploaded files (PDF, Markdown, DOCX)
stored in the uploads/ folder.

Supported formats:
- .pdf  : Uses PyPDF2 (fallback: pdfplumber)
- .md   : Direct text read (Markdown)
- .txt  : Direct text read (Plain text)
- .doc/.docx : Uses python-docx
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Base uploads directory (relative to backend/)
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
UPLOADS_DIR = os.path.abspath(UPLOADS_DIR)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt", ".doc", ".docx"}


def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    Extract text content from a file in the uploads/ folder.

    Args:
        file_path: Absolute path or relative path (from uploads/) to the file.

    Returns:
        Extracted text content, or None if extraction fails.
    """
    # Resolve relative paths against uploads dir
    if not os.path.isabs(file_path):
        file_path = os.path.join(UPLOADS_DIR, file_path)

    if not os.path.exists(file_path):
        logger.error("File not found: %s", file_path)
        return None

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        logger.error("Unsupported file type: %s (supported: %s)", ext, SUPPORTED_EXTENSIONS)
        return None

    try:
        if ext == ".pdf":
            return _extract_pdf(file_path)
        elif ext in (".md", ".txt"):
            return _extract_text(file_path)
        elif ext in (".doc", ".docx"):
            return _extract_docx(file_path)
        else:
            return None
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", file_path, e)
        return None


def _extract_pdf(file_path: str) -> Optional[str]:
    """Extract text from a PDF file."""
    # Try PyPDF2 first
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())

        content = "\n\n".join(pages)
        if content.strip():
            logger.info("Extracted %d chars from PDF (%d pages): %s",
                        len(content), len(reader.pages), os.path.basename(file_path))
            return content
    except ImportError:
        logger.warning("PyPDF2 not installed, trying pdfplumber")
    except Exception as e:
        logger.warning("PyPDF2 failed for %s: %s, trying pdfplumber", file_path, e)

    # Fallback: pdfplumber
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())

        content = "\n\n".join(pages)
        if content.strip():
            logger.info("Extracted %d chars from PDF (pdfplumber): %s",
                        len(content), os.path.basename(file_path))
            return content
    except ImportError:
        logger.error("Neither PyPDF2 nor pdfplumber installed. Install: pip install PyPDF2")
    except Exception as e:
        logger.error("pdfplumber also failed for %s: %s", file_path, e)

    return None


def _extract_text(file_path: str) -> Optional[str]:
    """Extract text from a plain text or Markdown file."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            if content.strip():
                logger.info("Extracted %d chars from %s: %s",
                            len(content), os.path.splitext(file_path)[1],
                            os.path.basename(file_path))
                return content
        except (UnicodeDecodeError, UnicodeError):
            continue

    logger.error("Could not decode text file with any encoding: %s", file_path)
    return None


def _extract_docx(file_path: str) -> Optional[str]:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        content = "\n\n".join(paragraphs)

        if content.strip():
            logger.info("Extracted %d chars from DOCX (%d paragraphs): %s",
                        len(content), len(paragraphs), os.path.basename(file_path))
            return content
        return None

    except ImportError:
        logger.error("python-docx not installed. Install: pip install python-docx")
        return None
    except Exception as e:
        logger.error("Failed to extract DOCX %s: %s", file_path, e)
        return None


def get_supported_files_in_uploads() -> list:
    """
    List all supported files in the uploads/ directory (recursive).

    Returns:
        List of dicts with 'path', 'name', 'extension', 'size_bytes'.
    """
    files = []
    for root, dirs, filenames in os.walk(UPLOADS_DIR):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, UPLOADS_DIR)
                files.append({
                    "path": full_path,
                    "relative_path": rel_path,
                    "name": filename,
                    "extension": ext,
                    "size_bytes": os.path.getsize(full_path)
                })
    return files
