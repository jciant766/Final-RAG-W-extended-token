"""
Article parser for Maltese law documents.

This module parses articles from DocLing's JSON structure using the 'marker'
and 'enumerated' fields to properly identify article boundaries.

Key insight: DocLing captures article numbers in the JSON structure:
- enumerated: true, marker: "1."  -> Article 1
- enumerated: true, marker: "2."  -> Article 2
- enumerated: false, marker: ""   -> Sub-item (i), (ii), etc.

We use this to reconstruct complete articles for chunking.
Each article = one chunk (no size limit, complete article must fit).
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterator

from docling.document_converter import DocumentConverter


@dataclass
class SubArticle:
    """A sub-article or sub-item within an article."""
    identifier: str  # e.g., "(1)", "(a)", "(i)"
    text: str
    level: int = 1   # Nesting level: 1=(1), 2=(a), 3=(i)


@dataclass
class Article:
    """A complete article from a Maltese law document."""
    number: str                      # e.g., "1", "2", "3A"
    title: Optional[str] = None      # Marginal note, e.g., "Interpretation"
    text: str = ""                   # Full article text
    sub_articles: list[SubArticle] = field(default_factory=list)

    # Source info
    page_start: int = 1
    page_end: int = 1

    @property
    def full_text(self) -> str:
        """Get complete article text including all sub-articles."""
        parts = [f"{self.number}. {self.text}"]
        for sub in self.sub_articles:
            parts.append(f"  {sub.identifier} {sub.text}")
        return "\n".join(parts)

    @property
    def citation(self) -> str:
        """Get a citation reference for this article."""
        return f"Article {self.number}"


@dataclass
class ParsedLaw:
    """A parsed Maltese law document with article structure."""
    filename: str
    legislation_id: str              # Cap. XXX or S.L. XXX.XX
    title: str = ""
    preamble: str = ""               # Text before Article 1
    articles: list[Article] = field(default_factory=list)
    schedules: list[dict] = field(default_factory=list)

    def get_article(self, number: str) -> Optional[Article]:
        """Get an article by number."""
        for article in self.articles:
            if article.number == number:
                return article
        return None

    def iter_chunks(self) -> Iterator[dict]:
        """Iterate over articles as chunks for embedding."""
        for article in self.articles:
            yield {
                'chunk_id': f"{self.legislation_id}_art_{article.number}",
                'legislation_id': self.legislation_id,
                'article_number': article.number,
                'article_title': article.title,
                'text': article.full_text,
                'citation': f"{self.legislation_id}, {article.citation}",
                'page_start': article.page_start,
                'page_end': article.page_end,
            }


class ArticleParser:
    """
    Parses articles from DocLing document structure.

    Uses the 'marker' and 'enumerated' fields from DocLing's JSON output
    to properly identify article boundaries and reconstruct complete articles.
    """

    # Pattern for article markers: "1.", "2.", "3A.", "l." (misread 1), etc.
    # Note: "l." (lowercase L) is often a misread of "1." in PDFs
    ARTICLE_MARKER_PATTERN = re.compile(r'^(\d+[A-Z]?|l)\.?$', re.IGNORECASE)

    # Pattern for detecting articles in text when marker is missing
    # Matches: "6A. Text...", "54A. Text...", "366F. Text..."
    TEXT_ARTICLE_PATTERN = re.compile(r'^(\d+[A-Z])\.\s+(.+)', re.IGNORECASE)

    # Pattern for sub-article markers: "(1)", "(2)", "(a)", "(b)", "(i)", "(ii)"
    SUB_ARTICLE_PATTERN = re.compile(r'^\((\d+|[a-z]|[ivxlc]+)\)$', re.IGNORECASE)

    # Patterns for legislation identifiers
    CAP_PATTERN = re.compile(r'(?:CHAPTER|CAP\.?)\s*(\d+[A-Z]?)', re.IGNORECASE)
    SL_PATTERN = re.compile(r'(?:S\.L\.)\s*(\d+\.\d+)', re.IGNORECASE)

    def __init__(self):
        """Initialize the converter."""
        self.converter = DocumentConverter()

    def parse(self, pdf_path: Path) -> ParsedLaw:
        """
        Parse a PDF into structured articles.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            ParsedLaw with articles extracted
        """
        result = self.converter.convert(pdf_path)
        doc = result.document

        # Extract legislation identifier
        leg_id = self._extract_legislation_id(doc, pdf_path.name)

        parsed = ParsedLaw(
            filename=pdf_path.name,
            legislation_id=leg_id
        )

        # Get all text items
        if not hasattr(doc, 'texts'):
            return parsed

        current_article = None
        preamble_parts = []
        in_preamble = True

        for text_item in doc.texts:
            text = getattr(text_item, 'text', '') or getattr(text_item, 'orig', '')
            if not text or not text.strip():
                continue

            marker = getattr(text_item, 'marker', '')
            enumerated = getattr(text_item, 'enumerated', False)
            label = getattr(text_item, 'label', 'text')

            # Get page number
            prov = getattr(text_item, 'prov', [])
            page_no = prov[0].page_no if prov else 1

            # Check if this is a new article (from marker field)
            if enumerated and marker:
                article_match = self.ARTICLE_MARKER_PATTERN.match(marker)
                if article_match:
                    # Save previous article
                    if current_article:
                        parsed.articles.append(current_article)

                    # Start new article
                    article_num = article_match.group(1)
                    # Fix common OCR error: lowercase "l" -> "1"
                    if article_num.lower() == 'l':
                        article_num = '1'
                    current_article = Article(
                        number=article_num,
                        text=text.strip(),
                        page_start=page_no,
                        page_end=page_no
                    )
                    in_preamble = False
                    continue

            # Fallback: Check for lettered articles in text itself (e.g., "6A. Text...")
            # This catches articles that DocLing doesn't recognize as enumerated
            if not marker or not enumerated:
                text_article_match = self.TEXT_ARTICLE_PATTERN.match(text.strip())
                if text_article_match:
                    # Save previous article
                    if current_article:
                        parsed.articles.append(current_article)

                    article_num = text_article_match.group(1).upper()
                    article_text = text_article_match.group(2)
                    current_article = Article(
                        number=article_num,
                        text=article_text.strip(),
                        page_start=page_no,
                        page_end=page_no
                    )
                    in_preamble = False
                    continue

            # Check for sub-article patterns in text
            sub_match = self.SUB_ARTICLE_PATTERN.match(text.strip()[:10])

            if current_article:
                # Update page end
                current_article.page_end = page_no

                # Check if this is a sub-article
                if text.strip().startswith('(') and ')' in text[:10]:
                    # Extract sub-article identifier
                    idx = text.find(')')
                    identifier = text[:idx+1].strip()
                    content = text[idx+1:].strip()
                    level = self._get_sub_article_level(identifier)
                    current_article.sub_articles.append(SubArticle(
                        identifier=identifier,
                        text=content,
                        level=level
                    ))
                else:
                    # Continuation of article text
                    if current_article.sub_articles:
                        # Add to last sub-article
                        current_article.sub_articles[-1].text += " " + text.strip()
                    else:
                        # Add to main article text
                        current_article.text += " " + text.strip()
            elif in_preamble:
                # Collect preamble text
                if label in ['text', 'section_header']:
                    preamble_parts.append(text.strip())

        # Save last article
        if current_article:
            parsed.articles.append(current_article)

        # Set preamble and title
        parsed.preamble = "\n".join(preamble_parts[:5])  # First few preamble lines
        if preamble_parts:
            # Title is usually the largest/boldest line in preamble
            for part in preamble_parts:
                if 'ACT' in part.upper() or 'REGULATIONS' in part.upper() or 'CODE' in part.upper():
                    parsed.title = part
                    break

        return parsed

    def _extract_legislation_id(self, doc, filename: str) -> str:
        """Extract the legislation identifier (Cap. XXX or S.L. XXX.XX)."""
        # Check filename first
        sl_match = re.search(r'S\.?L\.?\s*(\d+\.\d+)', filename, re.IGNORECASE)
        if sl_match:
            return f"S.L. {sl_match.group(1)}"

        cap_match = re.search(r'Cap\.?\s*(\d+[A-Z]?)', filename, re.IGNORECASE)
        if cap_match:
            return f"Cap. {cap_match.group(1)}"

        # Check document content
        if hasattr(doc, 'texts'):
            for text_item in doc.texts[:20]:  # Check first 20 items
                text = getattr(text_item, 'text', '') or getattr(text_item, 'orig', '')
                if not text:
                    continue

                sl_match = self.SL_PATTERN.search(text)
                if sl_match:
                    return f"S.L. {sl_match.group(1)}"

                cap_match = self.CAP_PATTERN.search(text)
                if cap_match:
                    return f"Cap. {cap_match.group(1)}"

        return filename

    def _get_sub_article_level(self, identifier: str) -> int:
        """Determine the nesting level of a sub-article identifier."""
        inner = identifier.strip('()')
        if inner.isdigit():
            return 1  # (1), (2), (3)
        elif inner.isalpha() and len(inner) == 1:
            return 2  # (a), (b), (c)
        else:
            return 3  # (i), (ii), (iii)


def parse_law(pdf_path: str | Path) -> ParsedLaw:
    """Convenience function to parse a law PDF."""
    parser = ArticleParser()
    return parser.parse(Path(pdf_path))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdf_path = Path(r"c:\Users\Jake\Downloads\maltese-law-rag\maltese-law-rag\Samples\Cap 653.5.pdf")

    print(f"Parsing: {pdf_path.name}")
    print("=" * 60)

    parser = ArticleParser()
    parsed = parser.parse(pdf_path)

    print(f"\nLegislation ID: {parsed.legislation_id}")
    print(f"Title: {parsed.title}")
    print(f"Number of articles: {len(parsed.articles)}")

    print("\n--- First 10 articles ---")
    for article in parsed.articles[:10]:
        print(f"\nArticle {article.number}:")
        print(f"  Text: {article.text[:100]}...")
        print(f"  Sub-articles: {len(article.sub_articles)}")
        print(f"  Pages: {article.page_start}-{article.page_end}")

    print("\n--- Sample chunks ---")
    for i, chunk in enumerate(parsed.iter_chunks()):
        if i >= 3:
            break
        print(f"\nChunk {chunk['chunk_id']}:")
        print(f"  Citation: {chunk['citation']}")
        # Encode safely for Windows console
        preview = chunk['text'][:200].encode('ascii', 'replace').decode('ascii')
        print(f"  Text preview: {preview}...")
