"""
Integrated text cleaning pipeline for Maltese law documents.

This module provides a complete pipeline for:
1. Extracting text from PDFs using DocLing (layout-aware)
2. Separating marginal annotations from main content
3. Removing junk text (amendments, legal notices, etc.)
4. Extracting valuable metadata (cross-references, article structure)
5. Outputting clean text ready for embedding

Usage:
    from src.extraction.cleaning_pipeline import CleaningPipeline

    pipeline = CleaningPipeline()
    result = pipeline.process("path/to/law.pdf")
    print(result.clean_text)
    print(result.cross_references)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from enum import Enum

from .docling_extractor import DoclingExtractor, ExtractedDocument
from .text_cleaner import TextCleaner, CleanedDocument


class LegislationType(Enum):
    """Type of Maltese legislation."""
    MAIN_ACT = "main"           # Cap. XXX - Main legislation (Chapter)
    SUBSIDIARY = "subsidiary"   # S.L. XXX.XX - Subsidiary Legislation
    UNKNOWN = "unknown"


@dataclass
class ProcessedLaw:
    """Final result of the cleaning pipeline."""
    # Source info
    filename: str
    filepath: str
    legislation_type: LegislationType

    # Identifiers
    chapter_number: Optional[str] = None     # e.g., "653" for Cap. 653
    sl_number: Optional[str] = None          # e.g., "653.05" for S.L. 653.05
    title: Optional[str] = None              # e.g., "Nuclear Safety and Radiation Protection Regulations"

    # Clean content
    clean_text: str = ""                     # Main content without junk
    summary: str = ""                        # AI-generated summary (populated later)

    # Extracted metadata
    cross_references: set[str] = field(default_factory=set)  # Cap. XXX, S.L. XXX.XX
    legal_notices: set[str] = field(default_factory=set)     # L.N. XXX of YYYY
    act_references: set[str] = field(default_factory=set)    # Act XV of 2009

    # Statistics
    original_char_count: int = 0
    cleaned_char_count: int = 0
    junk_removed_pct: float = 0.0

    @property
    def identifier(self) -> str:
        """Get the primary identifier for this law."""
        if self.sl_number:
            return f"S.L. {self.sl_number}"
        elif self.chapter_number:
            return f"Cap. {self.chapter_number}"
        return self.filename

    @property
    def parent_chapter(self) -> Optional[str]:
        """Get parent chapter number for subsidiary legislation."""
        if self.sl_number and '.' in self.sl_number:
            return self.sl_number.split('.')[0]
        return None


class CleaningPipeline:
    """
    Complete pipeline for extracting and cleaning Maltese law PDFs.

    This pipeline:
    1. Uses DocLing for layout-aware PDF extraction
    2. Separates marginal annotations from main content
    3. Removes junk (amendment history, legal notice references)
    4. Extracts cross-references for graph building
    5. Identifies legislation type and identifiers
    """

    # Patterns for identifying legislation type
    CAP_PATTERN = re.compile(r'(?:CHAPTER|CAP\.?)\s*(\d+[A-Z]?)', re.IGNORECASE)
    SL_PATTERN = re.compile(r'(?:SUBSIDIARY\s+LEGISLATION|S\.L\.)\s*(\d+\.\d+)', re.IGNORECASE)

    # Patterns for page headers/footers to remove
    PAGE_HEADER_PATTERNS = [
        re.compile(r'^\s*\[\s*S\.L\.\s*\d+\.\d+\s*$', re.MULTILINE),
        re.compile(r'^\s*\[\s*CAP\.\s*\d+[A-Z]?\.\s*$', re.MULTILINE),
        re.compile(r'^\s*\d+\s*$', re.MULTILINE),  # Standalone page numbers
    ]

    def __init__(self):
        """Initialize the pipeline components."""
        self.extractor = DoclingExtractor()
        self.cleaner = TextCleaner()

    def process(self, pdf_path: str | Path) -> ProcessedLaw:
        """
        Process a PDF through the complete cleaning pipeline.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ProcessedLaw with clean text and metadata
        """
        pdf_path = Path(pdf_path)

        # Step 1: Extract with DocLing
        extracted = self.extractor.extract(pdf_path)

        # Step 2: Clean text
        cleaned = self.cleaner.clean(extracted)

        # Step 3: Post-process (remove remaining page headers/footers)
        final_text = self._remove_page_artifacts(cleaned.clean_text)

        # Step 4: Identify legislation type and extract identifiers
        leg_type, chapter_num, sl_num = self._identify_legislation(final_text, pdf_path.name)

        # Step 5: Extract title
        title = self._extract_title(final_text, leg_type)

        # Calculate stats
        junk_pct = (cleaned.junk_removed_count / cleaned.original_char_count * 100) if cleaned.original_char_count > 0 else 0

        return ProcessedLaw(
            filename=pdf_path.name,
            filepath=str(pdf_path),
            legislation_type=leg_type,
            chapter_number=chapter_num,
            sl_number=sl_num,
            title=title,
            clean_text=final_text,
            cross_references=cleaned.cross_references,
            legal_notices=cleaned.legal_notices,
            act_references=cleaned.act_references,
            original_char_count=cleaned.original_char_count,
            cleaned_char_count=len(final_text),
            junk_removed_pct=junk_pct
        )

    def _remove_page_artifacts(self, text: str) -> str:
        """Remove page headers, footers, and page numbers."""
        result = text

        for pattern in self.PAGE_HEADER_PATTERNS:
            result = pattern.sub('', result)

        # Clean up multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()

    def _identify_legislation(self, text: str, filename: str) -> tuple[LegislationType, Optional[str], Optional[str]]:
        """
        Identify the type of legislation and extract identifiers.

        Returns:
            (LegislationType, chapter_number, sl_number)
        """
        # Check filename first (most reliable)
        sl_match_file = re.search(r'S\.?L\.?\s*(\d+\.\d+)', filename, re.IGNORECASE)
        cap_match_file = re.search(r'Cap\.?\s*(\d+[A-Z]?)', filename, re.IGNORECASE)

        if sl_match_file:
            return (LegislationType.SUBSIDIARY, None, sl_match_file.group(1))

        if cap_match_file:
            # Could be main act or subsidiary - check content
            sl_match = self.SL_PATTERN.search(text[:2000])
            if sl_match:
                return (LegislationType.SUBSIDIARY, cap_match_file.group(1), sl_match.group(1))
            return (LegislationType.MAIN_ACT, cap_match_file.group(1), None)

        # Check content
        sl_match = self.SL_PATTERN.search(text[:2000])
        if sl_match:
            return (LegislationType.SUBSIDIARY, None, sl_match.group(1))

        cap_match = self.CAP_PATTERN.search(text[:2000])
        if cap_match:
            return (LegislationType.MAIN_ACT, cap_match.group(1), None)

        return (LegislationType.UNKNOWN, None, None)

    def _extract_title(self, text: str, leg_type: LegislationType) -> Optional[str]:
        """Extract the title of the legislation."""
        lines = text.split('\n')

        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            line = line.strip()
            if not line:
                continue

            # Skip metadata lines
            if any(skip in line.upper() for skip in ['SUBSIDIARY LEGISLATION', 'CHAPTER', 'S.L.', 'CAP.']):
                continue
            if re.match(r'^\d+$', line):  # Skip numbers
                continue
            if re.match(r'^[\d\s\-]+$', line):  # Skip date-like patterns
                continue

            # Look for title patterns
            if leg_type == LegislationType.SUBSIDIARY:
                # S.L. titles often end with "REGULATIONS" or "RULES"
                if any(word in line.upper() for word in ['REGULATIONS', 'RULES', 'ORDER', 'NOTICE']):
                    return line
            else:
                # Main act titles often end with "ACT" or "ORDINANCE"
                if any(word in line.upper() for word in ['ACT', 'ORDINANCE', 'CODE']):
                    return line

            # If we have a reasonable title-like line
            if len(line) > 10 and len(line) < 200 and line[0].isupper():
                return line

        return None

    def process_directory(self, dir_path: str | Path, pattern: str = "*.pdf") -> list[ProcessedLaw]:
        """
        Process all PDFs in a directory.

        Args:
            dir_path: Path to directory containing PDFs
            pattern: Glob pattern for PDF files

        Returns:
            List of ProcessedLaw objects
        """
        dir_path = Path(dir_path)
        results = []

        for pdf_path in sorted(dir_path.glob(pattern)):
            try:
                result = self.process(pdf_path)
                results.append(result)
                print(f"[OK] {pdf_path.name}: {result.identifier} ({result.junk_removed_pct:.1f}% cleaned)")
            except Exception as e:
                print(f"[ERROR] {pdf_path.name}: {e}")

        return results


def process_pdf(pdf_path: str | Path) -> ProcessedLaw:
    """Convenience function to process a single PDF."""
    pipeline = CleaningPipeline()
    return pipeline.process(pdf_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_dir():
            pipeline = CleaningPipeline()
            results = pipeline.process_directory(path)
            print(f"\nProcessed {len(results)} files")
        else:
            result = process_pdf(path)
            print(f"\nFile: {result.filename}")
            print(f"Type: {result.legislation_type.value}")
            print(f"Identifier: {result.identifier}")
            print(f"Title: {result.title}")
            print(f"Cleaned: {result.junk_removed_pct:.1f}%")
            print(f"Cross-refs: {result.cross_references}")
    else:
        # Test with samples
        samples_dir = Path(r"c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\Samples")
        pipeline = CleaningPipeline()
        results = pipeline.process_directory(samples_dir)

        print("\n" + "="*60)
        print("RESULTS SUMMARY")
        print("="*60)
        for r in results:
            print(f"\n{r.identifier}")
            print(f"  Type: {r.legislation_type.value}")
            print(f"  Title: {r.title}")
            print(f"  Parent: {r.parent_chapter}")
            print(f"  Cleaned: {r.junk_removed_pct:.1f}%")
            print(f"  Cross-refs: {len(r.cross_references)}")
