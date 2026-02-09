"""
Comprehensive cross-reference extraction for Maltese legal documents.

Extracts:
- Chapter references (Cap. XXX)
- Subsidiary Legislation (S.L. XXX.XX)
- Articles (including nested: article X(Y)(Z))
- Internal article references
- Legal Notices (L.N. XXX of YYYY)
- Acts (Act XV of 2009)
- Parts, Schedules, Regulations

Uses hybrid approach: Regex (90%) + AI fallback (10%) for edge cases.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import logging
from openai import OpenAI
import os
import json

logger = logging.getLogger(__name__)


class ReferenceType(Enum):
    """Types of legal references."""
    CHAPTER = "chapter"  # Cap. 490
    SUBSIDIARY_LAW = "subsidiary_law"  # S.L. 653.05
    ARTICLE = "article"  # article 5 or article 5(1)(a)
    INTERNAL_ARTICLE = "internal_article"  # article 7 (within same chapter)
    LEGAL_NOTICE = "legal_notice"  # L.N. 44 of 2003
    ACT = "act"  # Act XV of 2009
    PART = "part"  # Part IV
    SCHEDULE = "schedule"  # First Schedule
    REGULATION = "regulation"  # regulation 17
    ANNEX = "annex"  # Annex I


@dataclass
class CrossReference:
    """A structured cross-reference."""
    ref_type: ReferenceType
    source_chapter: str
    source_article: Optional[str]

    # Target identifiers
    target_chapter: Optional[str] = None
    target_article: Optional[str] = None
    target_sl: Optional[str] = None  # S.L. number
    target_ln: Optional[str] = None  # Legal Notice
    target_act: Optional[str] = None  # Act identifier
    target_part: Optional[str] = None
    target_schedule: Optional[str] = None
    target_regulation: Optional[str] = None

    # Metadata
    act_name: Optional[str] = None
    context: str = ""
    confidence: float = 1.0  # 0.0-1.0
    extraction_method: str = "regex"  # "regex" or "llm"

    def __hash__(self):
        """Make hashable for deduplication."""
        return hash((
            self.ref_type,
            self.source_chapter,
            self.source_article,
            self.target_chapter,
            self.target_article,
            self.target_sl
        ))


class ComprehensiveCrossReferenceExtractor:
    """
    Extracts all types of cross-references from legal text.

    Uses comprehensive regex patterns + LLM fallback for edge cases.
    """

    # ========================================
    # COMPREHENSIVE REGEX PATTERNS
    # ========================================

    PATTERNS = {
        # 1. CHAPTER REFERENCES
        'cap_standard': re.compile(
            r'Cap\.?\s*(\d+[A-Z]?)',
            re.IGNORECASE
        ),
        'chapter_word': re.compile(
            r'Chapter\s+(\d+[A-Z]?)',
            re.IGNORECASE
        ),

        # 2. SUBSIDIARY LEGISLATION (S.L.)
        'sl_standard': re.compile(
            r'S\.L\.?\s*(\d+(?:\.\d+)?)',
            re.IGNORECASE
        ),
        'sl_in_parens': re.compile(
            r'\(S\.L\.?\s*(\d+\.\d+)\)',
            re.IGNORECASE
        ),

        # 3. LEGAL NOTICES (L.N.)
        'legal_notice_short': re.compile(
            r'L\.?N\.?\s*(\d+)\s+of\s+(\d{4})',
            re.IGNORECASE
        ),
        'legal_notice_full': re.compile(
            r'Legal\s+Notices?\s+((?:\d+(?:\s+and\s+\d+)?(?:,\s*)?)+)\s+of\s+(\d{4})',
            re.IGNORECASE
        ),
        # Multiple L.N. with individual years: "250 of 2024 and 212 of 2025"
        'legal_notice_individual': re.compile(
            r'(\d+)\s+of\s+(\d{4})',
            re.IGNORECASE
        ),

        # 4. ACT REFERENCES
        'act_roman': re.compile(
            r'Act\s+([IVXLC]+)\s+of\s+(\d{4})',
            re.IGNORECASE
        ),
        'act_number': re.compile(
            r'Act\s+No\.?\s*(\d+)\s+of\s+(\d{4})',
            re.IGNORECASE
        ),

        # 5. ARTICLE REFERENCES
        # Complex pattern: article 5(1)(a)(i)
        'article_complex': re.compile(
            r'article\s+(\d+[A-Z]?)(?:\s*\((\d+)\))?(?:\s*\(([a-z])\))?(?:\s*\(([ivx]+)\))?',
            re.IGNORECASE
        ),
        # Article with act name: "article 5(1) of the Administrative Justice Act"
        'article_of_act': re.compile(
            r'article\s+([\d\(\)a-z]+)\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Act|Ordinance|Code))',
            re.IGNORECASE
        ),
        # Sub-article references
        'sub_article': re.compile(
            r'sub-articles?\s*\((\d+)\)(?:\s*(?:and|,)\s*\(?([a-z])\)?)?',
            re.IGNORECASE
        ),
        # Articles range: "articles 7 or 12"
        'articles_multiple': re.compile(
            r'articles?\s+(\d+[A-Z]?)(?:\s+(?:or|and|,)\s+(\d+[A-Z]?))+',
            re.IGNORECASE
        ),

        # 6. PART REFERENCES
        'part_number': re.compile(
            r'Part\s+([IVXLC]+|\d+)',
            re.IGNORECASE
        ),
        'part_of_act': re.compile(
            r'Part\s+([IVXLC]+|\d+)\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s]+Act)',
            re.IGNORECASE
        ),

        # 7. SCHEDULE REFERENCES
        'schedule_ordinal': re.compile(
            r'(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Schedule',
            re.IGNORECASE
        ),
        'schedule_number': re.compile(
            r'Schedule\s+(\d+)',
            re.IGNORECASE
        ),

        # 8. REGULATION REFERENCES (for S.L.)
        'regulation_single': re.compile(
            r'regulations?\s+(\d+)',
            re.IGNORECASE
        ),
        'regulations_range': re.compile(
            r'regulations?\s+(\d+)\s*(?:-|to)\s*(\d+)',
            re.IGNORECASE
        ),

        # 9. ANNEX REFERENCES
        'annex': re.compile(
            r'Annex\s+([IVXLC]+|\d+)',
            re.IGNORECASE
        ),

        # 10. ACT NAME REFERENCES
        'act_name_standalone': re.compile(
            r'(?:the\s+)?([A-Z][A-Za-z\s]+(?:Act|Ordinance|Code|Regulations?))',
            re.IGNORECASE
        ),
        'act_in_meaning': re.compile(
            r'within\s+the\s+meaning\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Act|Ordinance))',
            re.IGNORECASE
        ),
        'act_in_accordance': re.compile(
            r'in\s+accordance\s+with\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Act|Ordinance))',
            re.IGNORECASE
        ),
        'provisions_of_act': re.compile(
            r'provisions?\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s]+(?:Act|Ordinance))',
            re.IGNORECASE
        ),
    }

    # Ordinal to number mapping
    ORDINAL_MAP = {
        'first': '1', 'second': '2', 'third': '3', 'fourth': '4',
        'fifth': '5', 'sixth': '6', 'seventh': '7', 'eighth': '8',
        'ninth': '9', 'tenth': '10'
    }

    def __init__(self, act_name_map: Optional[Dict[str, str]] = None, use_llm_fallback: bool = True):
        """
        Initialize extractor.

        Args:
            act_name_map: Mapping of act names (lowercase) to chapter numbers
            use_llm_fallback: Whether to use LLM for edge cases (recommended)
        """
        self.act_name_map = act_name_map or {}
        self.use_llm_fallback = use_llm_fallback

        # Initialize LLM client if needed
        if use_llm_fallback:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.llm_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key
                )
                # Use cheapest good model: Gemini 2.0 Flash Lite
                self.llm_model = "google/gemini-2.0-flash-lite"
                logger.info(f"LLM fallback enabled with model: {self.llm_model}")
            else:
                logger.warning("OPENROUTER_API_KEY not found, LLM fallback disabled")
                self.use_llm_fallback = False

    def extract_all(
        self,
        text: str,
        source_chapter: str,
        source_article: Optional[str] = None
    ) -> List[CrossReference]:
        """
        Extract ALL cross-references from text.

        Args:
            text: Legal text to analyze
            source_chapter: Current chapter number
            source_article: Current article (if within an article)

        Returns:
            List of CrossReference objects
        """
        references = []

        # 1. Extract chapter references
        references.extend(self._extract_chapter_refs(text, source_chapter, source_article))

        # 2. Extract S.L. references
        references.extend(self._extract_sl_refs(text, source_chapter, source_article))

        # 3. Extract article references
        references.extend(self._extract_article_refs(text, source_chapter, source_article))

        # 4. Extract Legal Notice references
        references.extend(self._extract_ln_refs(text, source_chapter, source_article))

        # 5. Extract Act references
        references.extend(self._extract_act_refs(text, source_chapter, source_article))

        # 6. Extract Part/Schedule/Regulation references
        references.extend(self._extract_structural_refs(text, source_chapter, source_article))

        # 7. Deduplicate
        unique_refs = list(set(references))

        # 8. LLM fallback for low-confidence extractions
        if self.use_llm_fallback and self._should_use_llm_fallback(text, unique_refs):
            llm_refs = self._llm_extract(text, source_chapter, source_article)
            unique_refs = self._merge_references(unique_refs, llm_refs)

        logger.debug(f"Extracted {len(unique_refs)} cross-references from text (method: regex + llm)")

        return unique_refs

    # ========================================
    # EXTRACTION METHODS
    # ========================================

    def _extract_chapter_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract Cap. XXX references."""
        refs = []

        # Find all Cap. references
        for match in self.PATTERNS['cap_standard'].finditer(text):
            cap_num = match.group(1)

            # Don't self-reference (unless it's a different article in same chapter)
            if cap_num == source_chapter and not source_article:
                continue

            context = self._extract_context(text, match.start(), match.end())

            # Check if there's an article number nearby
            article_num = self._find_nearby_article(text, match.end())

            ref = CrossReference(
                ref_type=ReferenceType.CHAPTER if not article_num else ReferenceType.ARTICLE,
                source_chapter=source_chapter,
                source_article=source_article,
                target_chapter=cap_num,
                target_article=article_num,
                context=context,
                extraction_method="regex"
            )
            refs.append(ref)

        # Also check "Chapter XXX" format
        for match in self.PATTERNS['chapter_word'].finditer(text):
            chapter_num = match.group(1)
            if chapter_num != source_chapter:
                context = self._extract_context(text, match.start(), match.end())
                ref = CrossReference(
                    ref_type=ReferenceType.CHAPTER,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_chapter=chapter_num,
                    context=context,
                    extraction_method="regex"
                )
                refs.append(ref)

        return refs

    def _extract_sl_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract S.L. references (Subsidiary Legislation)."""
        refs = []

        for pattern_name in ['sl_standard', 'sl_in_parens']:
            for match in self.PATTERNS[pattern_name].finditer(text):
                sl_num = match.group(1)
                context = self._extract_context(text, match.start(), match.end())

                ref = CrossReference(
                    ref_type=ReferenceType.SUBSIDIARY_LAW,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_sl=sl_num,
                    context=context,
                    extraction_method="regex"
                )
                refs.append(ref)

        return refs

    def _extract_article_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract article references."""
        refs = []

        # 1. Complex article references: article 5(1)(a)(i)
        for match in self.PATTERNS['article_complex'].finditer(text):
            article_num = match.group(1)
            sub1 = match.group(2)
            sub2 = match.group(3)
            sub3 = match.group(4)

            # Build full article identifier
            full_article = article_num
            if sub1:
                full_article += f"({sub1})"
            if sub2:
                full_article += f"({sub2})"
            if sub3:
                full_article += f"({sub3})"

            context = self._extract_context(text, match.start(), match.end())

            # Check if it references external act
            preceding_text = text[max(0, match.start() - 100):match.start()]
            cap_match = self.PATTERNS['cap_standard'].search(preceding_text)

            if cap_match:
                target_chapter = cap_match.group(1)
                ref_type = ReferenceType.ARTICLE
            else:
                # Internal reference
                target_chapter = source_chapter
                ref_type = ReferenceType.INTERNAL_ARTICLE

            # Don't add if it's self-reference
            if target_chapter == source_chapter and full_article == source_article:
                continue

            ref = CrossReference(
                ref_type=ref_type,
                source_chapter=source_chapter,
                source_article=source_article,
                target_chapter=target_chapter,
                target_article=full_article,
                context=context,
                extraction_method="regex"
            )
            refs.append(ref)

        # 2. Article with act name: "article 5(1) of the Administrative Justice Act"
        for match in self.PATTERNS['article_of_act'].finditer(text):
            article_id = match.group(1).strip()
            act_name = match.group(2).strip()

            # Map act name to chapter
            target_chapter = self._map_act_name_to_chapter(act_name)

            if target_chapter:
                ref = CrossReference(
                    ref_type=ReferenceType.ARTICLE,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_chapter=target_chapter,
                    target_article=article_id,
                    act_name=act_name,
                    context=match.group(0),
                    extraction_method="regex"
                )
                refs.append(ref)

        # 3. Sub-article references
        for match in self.PATTERNS['sub_article'].finditer(text):
            sub_num = match.group(1)
            sub_letter = match.group(2) if match.lastindex >= 2 else None

            # These are usually internal references
            if source_article:
                # Extract base article number
                base_article = source_article.split('(')[0]
                full_ref = f"{base_article}({sub_num})"
                if sub_letter:
                    full_ref += f"({sub_letter})"

                ref = CrossReference(
                    ref_type=ReferenceType.INTERNAL_ARTICLE,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_chapter=source_chapter,
                    target_article=full_ref,
                    context=match.group(0),
                    extraction_method="regex"
                )
                refs.append(ref)

        # 4. Multiple articles: "articles 7 or 12"
        for match in self.PATTERNS['articles_multiple'].finditer(text):
            # Extract all article numbers
            article_nums = re.findall(r'\d+[A-Z]?', match.group(0))
            for art_num in article_nums:
                if source_article and art_num == source_article:
                    continue  # Skip self-reference

                ref = CrossReference(
                    ref_type=ReferenceType.INTERNAL_ARTICLE,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_chapter=source_chapter,
                    target_article=art_num,
                    context=match.group(0),
                    extraction_method="regex"
                )
                refs.append(ref)

        return refs

    def _extract_ln_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract Legal Notice references (for amendment tracking)."""
        refs = []
        seen_lns = set()  # Track to avoid duplicates

        # Short form: L.N. 44 of 2003
        for match in self.PATTERNS['legal_notice_short'].finditer(text):
            ln_num = match.group(1)
            year = match.group(2)
            ln_id = f"L.N. {ln_num} of {year}"

            if ln_id not in seen_lns:
                seen_lns.add(ln_id)
                ref = CrossReference(
                    ref_type=ReferenceType.LEGAL_NOTICE,
                    source_chapter=source_chapter,
                    source_article=source_article,
                    target_ln=ln_id,
                    context=match.group(0),
                    extraction_method="regex"
                )
                refs.append(ref)

        # Find "Legal Notice(s)" and extract all N of YYYY patterns that follow
        # This handles: "Legal Notices 250 of 2024 and 212 of 2025"
        ln_header_pattern = re.compile(r'Legal\s+Notices?\s+', re.IGNORECASE)
        for header_match in ln_header_pattern.finditer(text):
            # Look at text after "Legal Notice(s)" (up to 150 chars or until period/newline)
            start_pos = header_match.end()
            end_pos = min(start_pos + 150, len(text))
            # Stop at sentence end or period
            subsequent = text[start_pos:end_pos]
            period_pos = subsequent.find('.')
            if period_pos > 0:
                subsequent = subsequent[:period_pos]

            # Find all "N of YYYY" patterns in this substring
            for num_match in self.PATTERNS['legal_notice_individual'].finditer(subsequent):
                ln_num = num_match.group(1)
                year = num_match.group(2)
                ln_id = f"Legal Notice {ln_num} of {year}"

                if ln_id not in seen_lns:
                    seen_lns.add(ln_id)
                    ref = CrossReference(
                        ref_type=ReferenceType.LEGAL_NOTICE,
                        source_chapter=source_chapter,
                        source_article=source_article,
                        target_ln=ln_id,
                        context=header_match.group(0) + subsequent.strip(),
                        extraction_method="regex"
                    )
                    refs.append(ref)

        return refs

    def _extract_act_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract Act references."""
        refs = []

        # Roman numeral acts: Act XV of 2009
        for match in self.PATTERNS['act_roman'].finditer(text):
            act_id = f"Act {match.group(1)} of {match.group(2)}"

            ref = CrossReference(
                ref_type=ReferenceType.ACT,
                source_chapter=source_chapter,
                source_article=source_article,
                target_act=act_id,
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        # Number acts: Act No. 5 of 2020
        for match in self.PATTERNS['act_number'].finditer(text):
            act_id = f"Act {match.group(1)} of {match.group(2)}"

            ref = CrossReference(
                ref_type=ReferenceType.ACT,
                source_chapter=source_chapter,
                source_article=source_article,
                target_act=act_id,
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        return refs

    def _extract_structural_refs(self, text: str, source_chapter: str, source_article: Optional[str]) -> List[CrossReference]:
        """Extract Part, Schedule, Regulation, Annex references."""
        refs = []

        # Parts
        for match in self.PATTERNS['part_number'].finditer(text):
            part_num = match.group(1)
            ref = CrossReference(
                ref_type=ReferenceType.PART,
                source_chapter=source_chapter,
                source_article=source_article,
                target_part=part_num,
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        # Schedules (ordinal)
        for match in self.PATTERNS['schedule_ordinal'].finditer(text):
            ordinal = match.group(1).lower()
            schedule_num = self.ORDINAL_MAP.get(ordinal, ordinal)
            ref = CrossReference(
                ref_type=ReferenceType.SCHEDULE,
                source_chapter=source_chapter,
                source_article=source_article,
                target_schedule=schedule_num,
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        # Regulations
        for match in self.PATTERNS['regulation_single'].finditer(text):
            reg_num = match.group(1)
            ref = CrossReference(
                ref_type=ReferenceType.REGULATION,
                source_chapter=source_chapter,
                source_article=source_article,
                target_regulation=reg_num,
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        # Annexes
        for match in self.PATTERNS['annex'].finditer(text):
            annex_num = match.group(1)
            ref = CrossReference(
                ref_type=ReferenceType.ANNEX,
                source_chapter=source_chapter,
                source_article=source_article,
                target_part=annex_num,  # Store in target_part field
                context=match.group(0),
                extraction_method="regex"
            )
            refs.append(ref)

        return refs

    # ========================================
    # HELPER METHODS
    # ========================================

    def _find_nearby_article(self, text: str, pos: int, window: int = 100) -> Optional[str]:
        """Find article number near a position."""
        nearby_text = text[pos:pos + window]
        match = re.search(r'article\s+(\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?)', nearby_text, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_context(self, text: str, start: int, end: int, window: int = 80) -> str:
        """Extract surrounding context."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()

    def _map_act_name_to_chapter(self, act_name: str) -> Optional[str]:
        """Map act name to chapter number."""
        act_name_lower = act_name.lower().strip()
        return self.act_name_map.get(act_name_lower)

    def _should_use_llm_fallback(self, text: str, regex_refs: List[CrossReference]) -> bool:
        """Decide if LLM fallback is needed."""
        # Heuristics for when to use LLM
        has_legal_language = any(keyword in text.lower() for keyword in ['cap.', 'article', 's.l.', 'act'])
        has_few_refs = len(regex_refs) < 2
        is_substantial = len(text) > 300
        has_complex_language = any(word in text.lower() for word in ['aforementioned', 'hereinafter', 'thereof'])

        return has_legal_language and (has_few_refs or has_complex_language) and is_substantial

    def _llm_extract(
        self,
        text: str,
        source_chapter: str,
        source_article: Optional[str]
    ) -> List[CrossReference]:
        """Use LLM to extract references (fallback for edge cases)."""

        if not self.use_llm_fallback or not hasattr(self, 'llm_client'):
            return []

        prompt = f"""Extract legal cross-references from this Maltese law text.

Find ALL references to:
1. Chapters (Cap. XXX or Chapter XXX)
2. Subsidiary Legislation (S.L. XXX.XX)
3. Articles (article X or article X(Y)(Z))
4. Legal Notices (L.N. XXX of YYYY)
5. Acts (Act XV of 2009)

Return ONLY valid JSON array:
[
  {{
    "type": "chapter|subsidiary_law|article|legal_notice|act",
    "target_chapter": "490" or null,
    "target_article": "5(1)" or null,
    "target_sl": "653.05" or null,
    "target_ln": "L.N. 44 of 2003" or null,
    "target_act": "Act XV of 2009" or null,
    "context": "brief quote"
  }}
]

Text:
{text[:1000]}

JSON:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)

            # Convert to CrossReference objects
            refs = []
            for item in data:
                ref_type_str = item.get('type', '').lower()
                ref_type = None

                # Map string to enum
                if ref_type_str == 'chapter':
                    ref_type = ReferenceType.CHAPTER
                elif ref_type_str == 'subsidiary_law':
                    ref_type = ReferenceType.SUBSIDIARY_LAW
                elif ref_type_str == 'article':
                    ref_type = ReferenceType.ARTICLE
                elif ref_type_str == 'legal_notice':
                    ref_type = ReferenceType.LEGAL_NOTICE
                elif ref_type_str == 'act':
                    ref_type = ReferenceType.ACT

                if ref_type:
                    ref = CrossReference(
                        ref_type=ref_type,
                        source_chapter=source_chapter,
                        source_article=source_article,
                        target_chapter=item.get('target_chapter'),
                        target_article=item.get('target_article'),
                        target_sl=item.get('target_sl'),
                        target_ln=item.get('target_ln'),
                        target_act=item.get('target_act'),
                        context=item.get('context', ''),
                        confidence=0.85,  # LLM confidence slightly lower
                        extraction_method="llm"
                    )
                    refs.append(ref)

            logger.info(f"LLM extracted {len(refs)} additional references")
            return refs

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []

    def _merge_references(
        self,
        regex_refs: List[CrossReference],
        llm_refs: List[CrossReference]
    ) -> List[CrossReference]:
        """Merge and deduplicate regex and LLM results."""
        all_refs = regex_refs + llm_refs

        # Deduplicate by converting to set (uses __hash__)
        unique_refs = list(set(all_refs))

        return unique_refs

    def update_act_name_map(self, act_name: str, chapter_number: str):
        """Add or update act name mapping."""
        self.act_name_map[act_name.lower().strip()] = chapter_number
        logger.debug(f"Added act mapping: {act_name} → {chapter_number}")
