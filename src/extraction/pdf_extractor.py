"""
PDF text extraction using PyMuPDF.
Handles both native PDFs and provides OCR fallback detection.
"""

import pymupdf
from pathlib import Path
from dataclasses import dataclass
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractedPage:
    page_number: int
    text: str
    has_sufficient_text: bool

@dataclass
class ExtractedDocument:
    filename: str
    filepath: str
    pages: List[ExtractedPage]
    total_pages: int
    extraction_quality: str  # 'good', 'partial', 'needs_ocr'
    full_text: str

def extract_pdf(filepath: str) -> ExtractedDocument:
    """
    Extract text from PDF using PyMuPDF.
    Returns structured document with quality assessment.
    """
    path = Path(filepath)
    doc = pymupdf.open(filepath)
    pages = []
    low_text_pages = 0
    
    all_text_parts = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Extract with sort=True for proper reading order
        text = page.get_text(sort=True)
        
        # Check if page has meaningful text (more than 100 chars)
        has_sufficient = len(text.strip()) > 100
        if not has_sufficient:
            low_text_pages += 1
        
        pages.append(ExtractedPage(
            page_number=page_num + 1,
            text=text,
            has_sufficient_text=has_sufficient
        ))
        all_text_parts.append(text)
    
    doc.close()
    
    # Assess extraction quality
    if len(pages) == 0:
        quality = 'needs_ocr'
    elif low_text_pages / len(pages) > 0.5:
        quality = 'needs_ocr'
    elif low_text_pages / len(pages) > 0.1:
        quality = 'partial'
    else:
        quality = 'good'
    
    full_text = "\n\n".join(all_text_parts)
    
    logger.info(f"Extracted {path.name}: {len(pages)} pages, quality={quality}")
    
    return ExtractedDocument(
        filename=path.name,
        filepath=str(path),
        pages=pages,
        total_pages=len(pages),
        extraction_quality=quality,
        full_text=full_text
    )

def extract_all_pdfs(directory: str) -> List[ExtractedDocument]:
    """Extract all PDFs from a directory."""
    pdf_path = Path(directory)
    documents = []
    
    for pdf_file in pdf_path.glob("*.pdf"):
        try:
            doc = extract_pdf(str(pdf_file))
            documents.append(doc)
        except Exception as e:
            logger.error(f"Failed to extract {pdf_file.name}: {e}")
    
    return documents
