"""
Text cleaning module for Maltese law documents.

This module removes "junk" text from extracted law documents, specifically:
- Amendment metadata (Amended by: L.N. XXX of YYYY)
- Substitution notices (Substituted by: L.N. XXX of YYYY)
- Addition notices (Added by: L.N. XXX of YYYY)
- Act reference patterns in margins (XII.2025.12, XXXIII.2024)
- Legal notice references that appear inline with article titles

It preserves:
- Article titles (Citation., Scope., Interpretation.)
- Cross-references (Cap. XXX, S.L. XXX.XX)
- Actual article content
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from .docling_extractor import ExtractedDocument, TextBlock, TextBlockType


@dataclass
class CleanedDocument:
    """Result of text cleaning with separated content types."""
    filename: str
    clean_text: str = ""  # Main article content without junk
    article_structure: list[dict] = field(default_factory=list)  # Parsed articles

    # Preserved metadata (valuable for graph building)
    cross_references: set[str] = field(default_factory=set)  # Cap. XXX, S.L. XXX.XX
    legal_notices: set[str] = field(default_factory=set)  # L.N. XXX of YYYY (for metadata only)
    act_references: set[str] = field(default_factory=set)  # Act XV of 2009

    # Statistics
    original_char_count: int = 0
    cleaned_char_count: int = 0
    junk_removed_count: int = 0


class TextCleaner:
    """
    Cleans extracted Maltese law text by removing amendment metadata junk.

    The cleaning process:
    1. Identifies and removes amendment/substitution/addition notices
    2. Removes Act reference patterns (Roman numerals + year)
    3. Preserves cross-references for graph building (but removes from inline text)
    4. Cleans up spacing and formatting issues
    """

    # Patterns for junk text to remove
    JUNK_PATTERNS = [
        # Amendment notices: "Amended by: L.N. 173 of 2004; L.N. 425 of 2007."
        r'Amended\s+by:\s*(?:[^.]+\.)+',
        r'Amended\s+by:\s*[^.]+\.',

        # Substitution notices: "Substituted by: L.N. 423 of 2007."
        r'Substituted\s+by:\s*(?:[^.]+\.)+',
        r'Substituted\s+by:\s*[^.]+\.',

        # Addition notices: "Added by: L.N. 212 of 2025."
        r'Added\s+by:\s*(?:[^.]+\.)+',
        r'Added\s+by:\s*[^.]+\.',

        # Act amendment references: "XII.2025.12", "XXXIII.2024", "XV.2009"
        # Roman numerals followed by year and optional section
        r'\b[IVXLCDM]+\.\d{4}(?:\.\d+)?\.?(?:\s|$)',

        # Standalone Legal Notice references inline with article titles
        # e.g., "L.N. 173 of 2004;" appearing alone
        r'(?<=[.;])\s*L\.N\.\s*\d+\s+of\s+\d{4}[.;]?',

        # Schedule references when they're just labels (not part of content)
        # e.g., "First Schedule." appearing alone in margins
        r'^(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Schedule\.\s*$',
    ]

    # Patterns to extract and preserve (for metadata)
    CROSS_REF_PATTERN = r'Cap\.\s*\d+[A-Z]?'
    SL_REF_PATTERN = r'S\.L\.\s*\d+\.\d+'
    LN_PATTERN = r'L\.N\.\s*\d+\s+of\s+\d{4}'
    ACT_PATTERN = r'Act\s+[IVXLCDM]+\s+of\s+\d{4}'

    # Patterns for article titles (to preserve)
    ARTICLE_TITLE_PATTERN = r'^[A-Z][a-z]+(?:\s+[a-z]+)*\.\s*$'

    def __init__(self):
        """Compile regex patterns for efficiency."""
        self.junk_regexes = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.JUNK_PATTERNS]
        self.cross_ref_regex = re.compile(self.CROSS_REF_PATTERN, re.IGNORECASE)
        self.sl_ref_regex = re.compile(self.SL_REF_PATTERN, re.IGNORECASE)
        self.ln_regex = re.compile(self.LN_PATTERN, re.IGNORECASE)
        self.act_regex = re.compile(self.ACT_PATTERN, re.IGNORECASE)

    def clean(self, extracted_doc: ExtractedDocument) -> CleanedDocument:
        """
        Clean an extracted document by removing junk text.

        Args:
            extracted_doc: Document extracted by DoclingExtractor

        Returns:
            CleanedDocument with clean text and preserved metadata
        """
        result = CleanedDocument(filename=extracted_doc.filename)

        # Collect all cross-references from marginal blocks before cleaning
        for block in extracted_doc.marginal_blocks:
            self._extract_references(block.text, result)

        # Clean main content blocks
        cleaned_blocks = []
        for block in extracted_doc.main_content_blocks:
            cleaned_text = self._clean_text(block.text)
            if cleaned_text.strip():
                cleaned_blocks.append((block, cleaned_text))

            # Also extract references from main content
            self._extract_references(block.text, result)

        # Build clean text output
        # Sort by page and vertical position (top to bottom)
        cleaned_blocks.sort(key=lambda x: (x[0].page_no, -x[0].top))
        result.clean_text = "\n\n".join(text for _, text in cleaned_blocks)

        # Calculate statistics
        original_text = "\n".join(b.text for b in extracted_doc.main_content_blocks)
        original_text += "\n".join(b.text for b in extracted_doc.marginal_blocks)
        result.original_char_count = len(original_text)
        result.cleaned_char_count = len(result.clean_text)
        result.junk_removed_count = result.original_char_count - result.cleaned_char_count

        return result

    def _clean_text(self, text: str) -> str:
        """Apply all cleaning patterns to text."""
        cleaned = text

        # Apply all junk removal patterns
        for regex in self.junk_regexes:
            cleaned = regex.sub('', cleaned)

        # Clean up multiple spaces
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)

        # Clean up multiple newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(line for line in lines if line)

        return cleaned.strip()

    def _extract_references(self, text: str, result: CleanedDocument):
        """Extract and store references from text."""
        # Cross-references (Cap. XXX)
        for match in self.cross_ref_regex.finditer(text):
            result.cross_references.add(match.group())

        # Subsidiary legislation refs (S.L. XXX.XX)
        for match in self.sl_ref_regex.finditer(text):
            result.cross_references.add(match.group())

        # Legal notices (for metadata only)
        for match in self.ln_regex.finditer(text):
            result.legal_notices.add(match.group())

        # Act references
        for match in self.act_regex.finditer(text):
            result.act_references.add(match.group())

    def clean_text_string(self, text: str) -> str:
        """
        Clean a raw text string directly (without document structure).

        Useful for cleaning text that was extracted by other means (e.g., PyMuPDF).
        """
        return self._clean_text(text)

    def extract_references_from_text(self, text: str) -> dict:
        """
        Extract all references from a text string.

        Returns:
            Dict with 'cross_references', 'legal_notices', 'act_references'
        """
        result = CleanedDocument(filename="")
        self._extract_references(text, result)
        return {
            'cross_references': list(result.cross_references),
            'legal_notices': list(result.legal_notices),
            'act_references': list(result.act_references)
        }


class MarginalContentParser:
    """
    Parses marginal content blocks to separate article titles from junk.

    Marginal content in Maltese law PDFs contains:
    - Article titles (valuable): "Interpretation.", "Scope.", "Citation."
    - Cross-references (valuable): "Cap. 365.", "Cap. 537."
    - Amendment metadata (junk): "Amended by: L.N. 173 of 2004"
    - Act refs (junk): "XII.2025.12"
    """

    # Common article title patterns
    KNOWN_TITLES = {
        'citation', 'scope', 'interpretation', 'definitions', 'application',
        'commencement', 'establishment', 'powers', 'functions', 'duties',
        'composition', 'meetings', 'proceedings', 'offences', 'penalties',
        'regulations', 'amendment', 'repeal', 'savings', 'transitional',
        'short title', 'long title', 'purpose', 'objectives', 'general provisions'
    }

    def parse(self, text: str) -> dict:
        """
        Parse marginal content and separate useful from junk.

        Args:
            text: Raw marginal block text

        Returns:
            Dict with 'article_title', 'cross_refs', 'is_junk', 'junk_content'
        """
        result = {
            'article_title': None,
            'cross_refs': [],
            'is_junk': False,
            'junk_content': []
        }

        # Check for cross-references
        cap_refs = re.findall(r'Cap\.\s*\d+[A-Z]?\.?', text, re.IGNORECASE)
        sl_refs = re.findall(r'S\.L\.\s*\d+\.\d+\.?', text, re.IGNORECASE)
        result['cross_refs'] = cap_refs + sl_refs

        # Check if this is pure junk (amendment metadata)
        junk_indicators = ['amended by', 'substituted by', 'added by', 'l.n.']
        text_lower = text.lower()
        if any(ind in text_lower for ind in junk_indicators):
            result['is_junk'] = True
            result['junk_content'].append(text)

        # Check if this contains an article title
        # Article titles are typically at the start, before any amendment info
        parts = re.split(r'(?:Amended|Substituted|Added)\s+by:', text, flags=re.IGNORECASE)
        if parts:
            potential_title = parts[0].strip().rstrip('.')
            if potential_title.lower() in self.KNOWN_TITLES:
                result['article_title'] = potential_title.title()
            elif len(potential_title) < 40 and potential_title[0].isupper():
                # Might be a title we don't know about
                result['article_title'] = potential_title

        return result


# Convenience functions
def clean_extracted_document(extracted_doc: ExtractedDocument) -> CleanedDocument:
    """Clean an extracted document."""
    cleaner = TextCleaner()
    return cleaner.clean(extracted_doc)


def clean_text(text: str) -> str:
    """Clean a raw text string."""
    cleaner = TextCleaner()
    return cleaner.clean_text_string(text)


if __name__ == "__main__":
    # Test the cleaner
    from pathlib import Path
    from .docling_extractor import DoclingExtractor

    pdf_path = Path(r"c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\Samples\Cap 653.5.pdf")

    print(f"Testing cleaner on: {pdf_path.name}")
    print("=" * 60)

    # Extract
    extractor = DoclingExtractor()
    extracted = extractor.extract(pdf_path)

    # Clean
    cleaner = TextCleaner()
    cleaned = cleaner.clean(extracted)

    print(f"\nOriginal chars: {cleaned.original_char_count:,}")
    print(f"Cleaned chars: {cleaned.cleaned_char_count:,}")
    print(f"Junk removed: {cleaned.junk_removed_count:,} chars")
    print(f"Reduction: {(cleaned.junk_removed_count / cleaned.original_char_count * 100):.1f}%")

    print(f"\nCross-references found: {len(cleaned.cross_references)}")
    for ref in sorted(cleaned.cross_references)[:10]:
        print(f"  - {ref}")

    print(f"\nLegal notices found: {len(cleaned.legal_notices)}")
    for ln in sorted(cleaned.legal_notices)[:5]:
        print(f"  - {ln}")

    print(f"\nAct references found: {len(cleaned.act_references)}")
    for act in sorted(cleaned.act_references)[:5]:
        print(f"  - {act}")

    print("\n--- First 1000 chars of cleaned text ---")
    print(cleaned.clean_text[:1000])
