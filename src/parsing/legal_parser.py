"""
Legal document parser for Maltese legislation.

UPDATED: Patterns based on actual Maltese law samples (Constitution, Addolorata Cemetery Ordinance).

Maltese law structure:
- Chapter header: "CHAPTER 18" or "CHAPTER I" (Roman numerals for Constitution)
- CAP reference: "[CAP. 18." in header
- Articles: Number followed by period like "1." or "20A." at start of line
- Sub-articles: "(1)", "(2)" etc.
- Sub-sub-articles: "(a)", "(b)" etc.
- Deeper levels: "(i)", "(ii)" etc.
- Marginal notes appear in sidebars (e.g., "Short title.", "Religion.")
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StructureLevel(Enum):
    CHAPTER = "chapter"
    PART = "part"
    ARTICLE = "article"
    SUB_ARTICLE = "sub_article"
    PARAGRAPH = "paragraph"


@dataclass
class LegalUnit:
    """A parsed unit of legal text (article, sub-article, etc.)"""
    level: StructureLevel
    identifier: str  # e.g., "5", "5(1)", "5(1)(a)"
    title: Optional[str]
    text: str
    parent_identifier: Optional[str]
    cross_references: List[str] = field(default_factory=list)


@dataclass
class ParsedLaw:
    """A fully parsed law document"""
    chapter_number: str
    chapter_title: str
    source_file: str
    units: List[LegalUnit]
    full_text: str
    metadata: Dict[str, str] = field(default_factory=dict)


class MalteseLegalParser:
    """
    Parser for Maltese legislation structure.

    Based on actual samples: Constitution of Malta, Addolorata Cemetery Ordinance.
    """

    # PATTERNS BASED ON ACTUAL MALTESE LAW SAMPLES
    PATTERNS = {
        # Matches: "CHAPTER 18", "CHAPTER I", "CHAPTER 386"
        'chapter_header': re.compile(
            r'CHAPTER\s+(\d+[A-Z]?|[IVXLC]+)',
            re.IGNORECASE
        ),

        # Extract from CAP reference like "[CAP. 18." or "CAP. 18.]"
        'cap_reference': re.compile(
            r'\[?CAP\.\s*(\d+[A-Z]?)\.?\s*\]?',
            re.IGNORECASE
        ),

        # Matches: "PART 1" or "PART I" followed by title
        'part': re.compile(
            r'^PART\s+([IVXLC]+|\d+)\s*\n?\s*(.+?)(?:\n|$)',
            re.IGNORECASE | re.MULTILINE
        ),

        # Matches Maltese law articles: "1.", "2.", "20A.", "64A."
        # Must be at start of line (possibly with whitespace)
        # Followed by optional sub-article "(1)" on same line
        'article': re.compile(
            r'^\s*(\d+[A-Z]?)\.\s+(?:\((\d+)\))?\s*(.*)$',
            re.MULTILINE
        ),

        # Matches sub-articles: "(1)", "(2)", etc.
        'sub_article': re.compile(
            r'^\s*\((\d+)\)\s*(.+)',
            re.MULTILINE
        ),

        # Matches sub-sub-articles: "(a)", "(b)", etc.
        'sub_sub_article': re.compile(
            r'^\s*\(([a-z])\)\s*(.+)',
            re.MULTILINE
        ),

        # Matches deeper levels: "(i)", "(ii)", "(iii)", "(iv)", etc.
        'roman_sub': re.compile(
            r'^\s*\(([ivx]+)\)\s*(.+)',
            re.MULTILINE
        ),

        # Cross-references: "article 5", "article 5(1)", "article 5(1)(a)"
        'cross_reference': re.compile(
            r'(?:article|art\.?)\s*(\d+[A-Z]?(?:\s*\(\d+\))?(?:\s*\([a-z]\))?)',
            re.IGNORECASE
        ),

        # Chapter references in text: "Chapter 17", "Cap. 16"
        'chapter_reference': re.compile(
            r'(?:Chapter|Cap\.?)\s*(\d+[A-Z]?)',
            re.IGNORECASE
        ),

        # Amendment references: "Amended by:", "Substituted by:"
        'amendment': re.compile(
            r'(?:Amended|Substituted|Added)\s+by:\s*\n?([\w\.\s,;]+?)(?=\n\d+\.|\n\(\d+\)|\Z)',
            re.IGNORECASE
        ),

        # Title patterns - look for ALL CAPS title after chapter number
        'title_caps': re.compile(
            r'^([A-Z][A-Z\s]+(?:ORDINANCE|ACT|CODE|REGULATIONS?|ORDER|RULES?))\s*$',
            re.MULTILINE
        ),
    }

    def parse(self, text: str, source_file: str) -> ParsedLaw:
        """Parse full law text into structured units."""

        # Extract chapter info
        chapter_number, chapter_title = self._extract_chapter_info(text, source_file)

        logger.info(f"Parsing Chapter {chapter_number}: {chapter_title}")

        # Parse articles
        units = self._parse_articles(text)

        logger.info(f"Found {len(units)} articles in {source_file}")

        return ParsedLaw(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            source_file=source_file,
            units=units,
            full_text=text,
            metadata=self._extract_metadata(text)
        )

    def _extract_chapter_info(self, text: str, source_file: str) -> Tuple[str, str]:
        """Extract chapter number and title from text."""

        chapter_number = None
        chapter_title = None

        # Try CAP reference first (most reliable for numbered chapters)
        cap_match = self.PATTERNS['cap_reference'].search(text)
        if cap_match:
            chapter_number = cap_match.group(1)

        # Try CHAPTER header
        chapter_match = self.PATTERNS['chapter_header'].search(text)
        if chapter_match:
            found_num = chapter_match.group(1)
            # Prefer numeric CAP number over Roman numerals
            if not chapter_number or not chapter_number.isdigit():
                chapter_number = found_num

        # If still no chapter number, extract from filename
        if not chapter_number:
            chapter_number = self._extract_chapter_from_filename(source_file)

        # Extract title - look for ALL CAPS title
        title_match = self.PATTERNS['title_caps'].search(text[:2000])
        if title_match:
            chapter_title = title_match.group(1).strip()
        else:
            # Fallback: get text after CHAPTER line
            chapter_title = self._extract_title_fallback(text)

        return chapter_number, chapter_title

    def _extract_chapter_from_filename(self, filename: str) -> str:
        """Try to extract chapter number from filename."""
        match = re.search(r'(\d+)', filename)
        return match.group(1) if match else "UNKNOWN"

    def _extract_title_fallback(self, text: str) -> str:
        """Extract title from first substantial line."""
        lines = text.strip().split('\n')
        for line in lines[:15]:
            line = line.strip()
            # Skip short lines, chapter headers, and page markers
            if len(line) > 15 and not re.match(r'^CHAPTER\s', line, re.IGNORECASE):
                if not re.match(r'^\[?CAP\.', line, re.IGNORECASE):
                    if not re.match(r'^\d+\s*$', line):  # Skip page numbers
                        return line[:150]
        return "UNKNOWN"

    def _parse_articles(self, text: str) -> List[LegalUnit]:
        """Extract all articles and their sub-components."""
        units = []

        # Find all article matches
        article_matches = list(self.PATTERNS['article'].finditer(text))

        if not article_matches:
            logger.warning("No articles found - document may have different structure")
            # Try to create a single unit with all text
            units.append(LegalUnit(
                level=StructureLevel.ARTICLE,
                identifier="1",
                title=None,
                text=text[:5000],  # First 5000 chars as fallback
                parent_identifier=None,
                cross_references=[]
            ))
            return units

        for i, match in enumerate(article_matches):
            article_num = match.group(1)
            # Group 2 is optional sub-article number on same line
            inline_sub = match.group(2)
            article_first_line = match.group(3).strip() if match.group(3) else ""

            # Get text until next article or end
            start_pos = match.end()
            end_pos = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(text)
            article_body = text[start_pos:end_pos].strip()

            # Combine first line with body
            if article_first_line:
                full_text = article_first_line + "\n" + article_body
            else:
                full_text = article_body

            # Clean up amendment notes from the text for display
            # (but keep them in metadata)
            clean_text = self._clean_article_text(full_text)

            # Find cross-references
            cross_refs = self._find_cross_references(full_text)

            # Try to extract article title (marginal note)
            title = self._extract_article_title(text, match.start())

            # Create identifier including inline sub-article if present
            identifier = article_num
            if inline_sub:
                identifier = f"{article_num}({inline_sub})"

            unit = LegalUnit(
                level=StructureLevel.ARTICLE,
                identifier=identifier,
                title=title,
                text=clean_text,
                parent_identifier=None,
                cross_references=cross_refs
            )
            units.append(unit)

        return units

    def _extract_article_title(self, text: str, article_pos: int) -> Optional[str]:
        """
        Try to extract the marginal note (title) for an article.
        In Maltese laws, these appear before the article number.
        Examples: "Short title.", "Religion.", "National Flag."
        """
        # Look at text before the article position
        before_text = text[max(0, article_pos - 200):article_pos]
        lines = before_text.strip().split('\n')

        # Look for a capitalized short phrase ending with period
        for line in reversed(lines[-5:]):
            line = line.strip()
            # Match patterns like "Short title.", "Religion.", "National Flag."
            if re.match(r'^[A-Z][a-z].*\.$', line) and len(line) < 80:
                # Exclude amendment references
                if not re.match(r'^(?:Amended|Substituted|Added)\s+by', line, re.IGNORECASE):
                    return line.rstrip('.')
            # Also match multi-word titles like "Right of sepulture."
            if re.match(r'^[A-Z][a-z\s]+\.$', line) and len(line) < 80:
                if not re.match(r'^(?:Amended|Substituted|Added)\s+by', line, re.IGNORECASE):
                    return line.rstrip('.')

        return None

    def _clean_article_text(self, text: str) -> str:
        """Remove amendment references and clean up article text."""
        # Remove lines that are just amendment references
        lines = text.split('\n')
        clean_lines = []
        skip_next = False

        for line in lines:
            stripped = line.strip()
            # Skip amendment reference lines
            if re.match(r'^(?:Amended|Substituted|Added)\s+by:', stripped, re.IGNORECASE):
                skip_next = True
                continue
            # Skip continuation of amendment references (e.g., "XVII.2019.42.")
            if skip_next and re.match(r'^[IVXLC]+\.\d+\.\d+', stripped):
                continue
            skip_next = False
            clean_lines.append(line)

        return '\n'.join(clean_lines).strip()

    def _find_cross_references(self, text: str) -> List[str]:
        """Find references to other articles and chapters."""
        article_refs = self.PATTERNS['cross_reference'].findall(text)
        chapter_refs = self.PATTERNS['chapter_reference'].findall(text)

        # Combine and deduplicate
        all_refs = []
        for ref in article_refs:
            all_refs.append(f"Article {ref}")
        for ref in chapter_refs:
            all_refs.append(f"Chapter {ref}")

        return list(set(all_refs))

    def _extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract metadata like dates, amendments."""
        metadata = {}

        # Look for enactment date
        date_pattern = re.compile(
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December)[,\s]+(\d{4})',
            re.IGNORECASE
        )
        date_match = date_pattern.search(text[:1000])  # Usually in header
        if date_match:
            metadata['enactment_date'] = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}"

        # Look for amendment history in header
        amendment_pattern = re.compile(
            r'(?:as\s+)?amended\s+by\s+(?:Acts?|Ordinances?|L\.N\.)\s+([^;]+)',
            re.IGNORECASE
        )
        amendments = amendment_pattern.findall(text[:2000])
        if amendments:
            metadata['amendments'] = '; '.join(set(amendments))

        # Extract legal notice references
        ln_pattern = re.compile(r'L\.?N\.?\s+(\d+)\s+of\s+(\d{4})', re.IGNORECASE)
        legal_notices = ln_pattern.findall(text[:2000])
        if legal_notices:
            metadata['legal_notices'] = ', '.join([f"L.N. {num} of {year}" for num, year in legal_notices])

        return metadata
