"""File extraction utilities for Slack Wrapped.

Extracts text content from various file formats (TXT, MD, PDF).
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileExtractionError(Exception):
    """Raised when file extraction fails."""
    pass


def extract_text_from_file(
    file_path: Optional[str] = None,
    file_content: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> str:
    """
    Extract text content from a file.
    
    Supports:
    - TXT files (plain text)
    - MD files (markdown, treated as plain text)
    - PDF files (text extraction)
    - LOG files (plain text)
    
    Args:
        file_path: Path to the file (if reading from disk)
        file_content: Raw file bytes (if uploaded)
        filename: Original filename (for format detection when using file_content)
        
    Returns:
        Extracted text content
        
    Raises:
        FileExtractionError: If extraction fails
    """
    # Determine file extension
    if file_path:
        path = Path(file_path)
        ext = path.suffix.lower()
        filename = path.name
    elif filename:
        ext = Path(filename).suffix.lower()
    else:
        ext = ".txt"  # Default to plain text
    
    # Read file content if path provided
    if file_path and not file_content:
        path = Path(file_path)
        if not path.exists():
            raise FileExtractionError(f"File not found: {file_path}")
        
        if ext == ".pdf":
            file_content = path.read_bytes()
        else:
            try:
                return path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                return path.read_text(encoding="latin-1")
    
    # Handle different formats
    if ext == ".pdf":
        return _extract_from_pdf(file_content, filename)
    elif ext in (".txt", ".md", ".log", ".text", ".markdown"):
        return _extract_from_text(file_content)
    else:
        # Try to treat as plain text
        logger.warning(f"Unknown file extension '{ext}', treating as plain text")
        return _extract_from_text(file_content)


def _extract_from_text(content: bytes) -> str:
    """Extract text from plain text file bytes."""
    if not content:
        return ""
    
    # Try UTF-8 first, then fallback encodings
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # Last resort - ignore errors
    return content.decode("utf-8", errors="ignore")


def _extract_from_pdf(content: bytes, filename: str = "file.pdf") -> str:
    """
    Extract text from PDF file bytes.
    
    Args:
        content: PDF file bytes
        filename: Original filename for error messages
        
    Returns:
        Extracted text content
        
    Raises:
        FileExtractionError: If PDF extraction fails
    """
    if not content:
        raise FileExtractionError("Empty PDF file")
    
    try:
        from pypdf import PdfReader
        import io
        
        # Create a file-like object from bytes
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        text_parts = []
        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
        
        if not text_parts:
            raise FileExtractionError(
                f"No text could be extracted from PDF '{filename}'. "
                "The PDF may be image-based or encrypted."
            )
        
        return "\n".join(text_parts)
        
    except ImportError:
        raise FileExtractionError(
            "PDF support requires pypdf. Install with: pip install pypdf"
        )
    except Exception as e:
        if "FileExtractionError" in type(e).__name__:
            raise
        raise FileExtractionError(f"Failed to extract text from PDF: {e}")


def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions."""
    return [".txt", ".md", ".log", ".text", ".markdown", ".pdf"]


def is_supported_file(filename: str) -> bool:
    """Check if a file type is supported."""
    ext = Path(filename).suffix.lower()
    return ext in get_supported_extensions()
