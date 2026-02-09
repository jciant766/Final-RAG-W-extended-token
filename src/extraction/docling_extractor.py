"""
DocLing-based PDF extractor for Maltese law documents.

This module uses IBM's DocLing library to extract text from PDFs with
layout-aware processing. It separates marginal annotations from main
content using bounding box positions.

Key features:
- Layout-aware extraction (handles two-column legal document format)
- Separates marginal notes from main article text
- Preserves document structure (parts, articles, definitions)
- Extracts metadata (cross-references, article titles)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum

from docling.document_converter import DocumentConverter


class TextBlockType(Enum):
    """Classification of text blocks based on position and content."""
    HEADER = "header"           # Document/section headers
    MAIN_CONTENT = "main"       # Primary article text
    MARGINAL_NOTE = "marginal"  # Side annotations (titles, amendments, refs)
    TABLE = "table"             # Table content
    FORMULA = "formula"         # Mathematical formulas
    FOOTER = "footer"           # Page footers


@dataclass
class TextBlock:
    """A text block with position and classification metadata."""
    text: str
    block_type: TextBlockType
    page_no: int
    left: float
    right: float
    top: float
    bottom: float
    label: str  # DocLing's label (text, section_header, list_item, etc.)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def is_marginal(self) -> bool:
        """Check if block is in the marginal column (left side of page)."""
        return self.left < 150  # Threshold based on analysis


@dataclass
class MarginalContent:
    """Parsed content from marginal annotations."""
    article_title: Optional[str] = None      # e.g., "Interpretation.", "Scope."
    amendments: list[str] = field(default_factory=list)  # e.g., ["L.N. 173 of 2004"]
    cross_references: list[str] = field(default_factory=list)  # e.g., ["Cap. 365"]
    schedule_refs: list[str] = field(default_factory=list)  # e.g., ["First Schedule"]
    raw_text: str = ""


@dataclass
class ExtractedDocument:
    """Result of DocLing extraction with classified content."""
    filename: str
    total_pages: int
    main_content_blocks: list[TextBlock] = field(default_factory=list)
    marginal_blocks: list[TextBlock] = field(default_factory=list)
    headers: list[TextBlock] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)

    # Parsed metadata from marginal content
    cross_references: set[str] = field(default_factory=set)
    article_titles: dict[int, str] = field(default_factory=dict)  # page_no -> title

    def get_clean_text(self) -> str:
        """Get reconstructed clean text without junk."""
        lines = []
        for block in sorted(self.main_content_blocks, key=lambda b: (b.page_no, -b.top)):
            lines.append(block.text)
        return "\n\n".join(lines)


class DoclingExtractor:
    """
    Extracts text from Maltese law PDFs using DocLing with layout awareness.

    The Maltese legislation PDFs have a two-column layout:
    - Left margin (x < 150): Article titles, amendment history, cross-references
    - Main content (x >= 150): Actual article text

    This extractor separates these columns and classifies content appropriately.
    """

    # Threshold for marginal vs main content (in PDF points)
    MARGINAL_THRESHOLD = 150

    def __init__(self):
        """Initialize the DocLing converter."""
        self.converter = DocumentConverter()

    def extract(self, pdf_path: Path) -> ExtractedDocument:
        """
        Extract and classify content from a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ExtractedDocument with classified text blocks
        """
        result = self.converter.convert(pdf_path)
        doc = result.document

        extracted = ExtractedDocument(
            filename=pdf_path.name,
            total_pages=len(doc.pages) if hasattr(doc, 'pages') else 0
        )

        # Process all text items
        if hasattr(doc, 'texts'):
            for text_item in doc.texts:
                block = self._process_text_item(text_item)
                if block:
                    self._classify_and_add_block(block, extracted)

        # Process tables
        if hasattr(doc, 'tables'):
            for table in doc.tables:
                extracted.tables.append(self._process_table(table))

        return extracted

    def _process_text_item(self, text_item) -> Optional[TextBlock]:
        """Convert a DocLing text item to a TextBlock."""
        # Get text content
        text = getattr(text_item, 'text', '') or getattr(text_item, 'orig', '')
        if not text or not text.strip():
            return None

        # Get provenance (position) info
        prov = getattr(text_item, 'prov', [])
        if not prov:
            return None

        # Use first provenance entry for position
        first_prov = prov[0]
        bbox = getattr(first_prov, 'bbox', None)
        if not bbox:
            return None

        page_no = getattr(first_prov, 'page_no', 1)
        label = getattr(text_item, 'label', 'text')

        # Determine block type based on position and label
        block_type = self._determine_block_type(bbox.l, label)

        return TextBlock(
            text=text.strip(),
            block_type=block_type,
            page_no=page_no,
            left=bbox.l,
            right=bbox.r,
            top=bbox.t,
            bottom=bbox.b,
            label=label
        )

    def _determine_block_type(self, left_pos: float, label: str) -> TextBlockType:
        """Determine the type of text block based on position and label."""
        if label == 'section_header':
            return TextBlockType.HEADER
        elif left_pos < self.MARGINAL_THRESHOLD:
            return TextBlockType.MARGINAL_NOTE
        else:
            return TextBlockType.MAIN_CONTENT

    def _classify_and_add_block(self, block: TextBlock, extracted: ExtractedDocument):
        """Add a block to the appropriate category in the extracted document."""
        if block.block_type == TextBlockType.HEADER:
            extracted.headers.append(block)
            # Headers are also part of main content for reconstruction
            extracted.main_content_blocks.append(block)
        elif block.block_type == TextBlockType.MARGINAL_NOTE:
            extracted.marginal_blocks.append(block)
            # Parse marginal content for metadata
            self._extract_marginal_metadata(block, extracted)
        else:
            extracted.main_content_blocks.append(block)

    def _extract_marginal_metadata(self, block: TextBlock, extracted: ExtractedDocument):
        """Extract useful metadata from marginal annotations."""
        text = block.text

        # Extract cross-references (Cap. XXX)
        cap_refs = re.findall(r'Cap\.\s*\d+[A-Z]?', text, re.IGNORECASE)
        for ref in cap_refs:
            extracted.cross_references.add(ref)

        # Extract article title if it's a simple title (ends with period, no amendment text)
        if self._is_article_title(text):
            extracted.article_titles[block.page_no] = text.rstrip('.')

    def _is_article_title(self, text: str) -> bool:
        """Check if text is likely an article title (not amendment metadata)."""
        # Article titles are short and don't contain amendment patterns
        if len(text) > 50:
            return False
        if any(pattern in text.lower() for pattern in ['amended by', 'substituted by', 'added by', 'l.n.']):
            return False
        # Should be title case or sentence case, ending with period
        if text.endswith('.') and text[0].isupper():
            return True
        return False

    def _process_table(self, table) -> dict:
        """Extract table content."""
        return {
            'data': table.export_to_dataframe().to_dict() if hasattr(table, 'export_to_dataframe') else {},
            'markdown': table.export_to_markdown() if hasattr(table, 'export_to_markdown') else str(table)
        }

    def extract_to_markdown(self, pdf_path: Path) -> str:
        """
        Simple extraction that returns DocLing's markdown output.

        This is a fallback for when full layout analysis isn't needed.
        """
        result = self.converter.convert(pdf_path)
        return result.document.export_to_markdown()


# Convenience function
def extract_pdf(pdf_path: str | Path) -> ExtractedDocument:
    """Extract content from a PDF file."""
    extractor = DoclingExtractor()
    return extractor.extract(Path(pdf_path))


if __name__ == "__main__":
    # Test extraction
    import sys

    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = Path(r"c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\Samples\Cap 653.5.pdf")

    print(f"Extracting: {pdf_path}")
    extractor = DoclingExtractor()
    doc = extractor.extract(pdf_path)

    print(f"\nDocument: {doc.filename}")
    print(f"Pages: {doc.total_pages}")
    print(f"Main content blocks: {len(doc.main_content_blocks)}")
    print(f"Marginal blocks: {len(doc.marginal_blocks)}")
    print(f"Headers: {len(doc.headers)}")
    print(f"Cross-references found: {doc.cross_references}")
    print(f"Article titles found: {len(doc.article_titles)}")

    print("\n--- First 5 marginal blocks ---")
    for block in doc.marginal_blocks[:5]:
        print(f"  [{block.page_no}] l={block.left:.1f}: {block.text[:60]}...")

    print("\n--- First 5 main content blocks ---")
    for block in doc.main_content_blocks[:5]:
        print(f"  [{block.page_no}] l={block.left:.1f}: {block.text[:60]}...")
