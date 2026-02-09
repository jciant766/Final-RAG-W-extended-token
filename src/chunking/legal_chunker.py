"""
Hierarchical chunking for legal documents.
Creates chunks that preserve legal structure and include rich metadata.

Note: Domain classification has been removed in favor of chapter-level
semantic routing. The legal_domains field is kept for backwards compatibility
but will be empty. Query routing is now done via chapter summaries.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import hashlib
import json
import re


@dataclass
class LegalChunk:
    """A chunk optimized for retrieval with full metadata."""
    chunk_id: str
    text: str  # The chunk content (with context)

    # Hierarchical identifiers for filtering
    chapter_number: str
    chapter_title: str
    article_number: Optional[str]
    sub_article_id: Optional[str]

    # Page metadata for PDF navigation
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    # Context for better retrieval
    context_summary: str = ""  # Brief summary of the chapter
    full_citation: str = ""  # e.g., "Chapter 386, Article 5(1)"

    # Metadata for filtering and routing
    cross_references: List[str] = field(default_factory=list)
    legal_domains: List[str] = field(default_factory=list)  # Deprecated - kept for compatibility, will be empty
    keywords: List[str] = field(default_factory=list)

    # Source tracking
    source_file: str = ""


class LegalChunker:
    """Creates retrieval-optimized chunks from parsed legal documents."""

    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
    
    def chunk_law(self, parsed_law) -> List[LegalChunk]:
        """Create chunks from a parsed law document."""
        chunks = []
        
        # Create chapter summary for context enrichment
        chapter_summary = self._create_chapter_summary(parsed_law)
        
        for unit in parsed_law.units:
            unit_chunks = self._chunk_unit(
                unit=unit,
                chapter_number=parsed_law.chapter_number,
                chapter_title=parsed_law.chapter_title,
                chapter_summary=chapter_summary,
                source_file=parsed_law.source_file
            )
            chunks.extend(unit_chunks)
        
        return chunks
    
    def _chunk_unit(
        self,
        unit,
        chapter_number: str,
        chapter_title: str,
        chapter_summary: str,
        source_file: str
    ) -> List[LegalChunk]:
        """Create chunk(s) from a legal unit."""
        chunks = []
        
        # Build citation
        full_citation = f"Chapter {chapter_number}, Article {unit.identifier}"
        
        # Build context-enriched text
        context_text = self._build_chunk_text(
            unit=unit,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary
        )
        
        # If text is too long, split into multiple chunks
        if len(context_text) > self.max_chunk_size:
            text_chunks = self._split_long_text(context_text, unit.identifier)
            for i, chunk_text in enumerate(text_chunks):
                chunk = self._create_chunk(
                    text=chunk_text,
                    chunk_id_suffix=f"-part{i+1}",
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    chapter_summary=chapter_summary,
                    unit=unit,
                    full_citation=full_citation,
                    source_file=source_file
                )
                chunks.append(chunk)
        else:
            chunk = self._create_chunk(
                text=context_text,
                chunk_id_suffix="",
                chapter_number=chapter_number,
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                unit=unit,
                full_citation=full_citation,
                source_file=source_file
            )
            chunks.append(chunk)
        
        return chunks
    
    def _build_chunk_text(self, unit, chapter_title: str, chapter_summary: str) -> str:
        """Build the text content for a chunk with context."""
        parts = [
            f"[{chapter_title}]",
            f"Context: {chapter_summary}",
            "",
            f"Article {unit.identifier}:",
        ]
        
        if unit.title:
            parts.append(f"Title: {unit.title}")
        
        parts.append("")
        parts.append(unit.text)
        
        return "\n".join(parts)
    
    def _create_chunk(
        self,
        text: str,
        chunk_id_suffix: str,
        chapter_number: str,
        chapter_title: str,
        chapter_summary: str,
        unit,
        full_citation: str,
        source_file: str
    ) -> LegalChunk:
        """Create a single LegalChunk."""

        # Generate unique ID
        chunk_id = self._generate_id(chapter_number, unit.identifier, text) + chunk_id_suffix

        # Extract keywords
        keywords = self._extract_keywords(unit.text)

        # Determine article and sub-article
        article_number = unit.identifier.split('(')[0] if '(' in unit.identifier else unit.identifier
        sub_article_id = unit.identifier if '(' in unit.identifier else None

        return LegalChunk(
            chunk_id=chunk_id,
            text=text,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            article_number=article_number,
            sub_article_id=sub_article_id,
            page_start=getattr(unit, 'page_start', None),
            page_end=getattr(unit, 'page_end', None),
            context_summary=chapter_summary,
            full_citation=full_citation,
            cross_references=unit.cross_references,
            legal_domains=[],  # Deprecated - routing now done via chapter summaries
            keywords=keywords,
            source_file=source_file
        )
    
    def _create_chapter_summary(self, parsed_law) -> str:
        """Create a brief summary of the chapter."""
        titles = []
        for unit in parsed_law.units[:5]:
            if unit.title:
                titles.append(f"Art. {unit.identifier}: {unit.title}")
            else:
                # Use first 50 chars of text
                preview = unit.text[:50].replace('\n', ' ').strip()
                titles.append(f"Art. {unit.identifier}: {preview}...")
        
        if titles:
            summary = f"{parsed_law.chapter_title}. Contains provisions on: {'; '.join(titles)}"
        else:
            summary = parsed_law.chapter_title
        
        return summary[:400]  # Limit length
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important legal keywords."""
        text_lower = text.lower()
        
        # Legal action words
        action_words = ['shall', 'must', 'may', 'may not', 'prohibited', 'required', 
                       'liable', 'entitled', 'obliged', 'permitted']
        
        # Legal concept words
        concept_words = ['obligation', 'right', 'duty', 'penalty', 'offence', 
                        'contract', 'agreement', 'property', 'transfer', 'registration',
                        'notification', 'application', 'approval', 'permit', 'licence',
                        'authority', 'minister', 'court', 'tribunal', 'appeal']
        
        found = []
        for word in action_words + concept_words:
            if word in text_lower:
                found.append(word)
        
        return list(set(found))
    
    def _split_long_text(self, text: str, identifier: str) -> List[str]:
        """Split long text at sentence boundaries."""
        chunks = []
        current_chunk = ""
        
        # Split by sentences (roughly)
        sentences = re.split(r'(?<=[.;])\s+', text)
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < self.max_chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _generate_id(self, chapter: str, identifier: str, text: str) -> str:
        """Generate unique chunk ID."""
        content = f"{chapter}:{identifier}:{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
